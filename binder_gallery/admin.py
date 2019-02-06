import flask_login as login
from flask import request, url_for, redirect, abort
from flask_admin import AdminIndexView as BaseAdminIndexView, expose, helpers
from flask_admin.contrib.sqla import ModelView
from flask_admin.helpers import is_safe_url
from wtforms import validators
from .forms import LoginForm
from .models import User, Repo
from .utilities import repo_url_parts, get_repo_description
from .app import db


class BaseModelView(ModelView):

    def is_accessible(self):
        return login.current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return redirect(url_for('admin.login_view', next=request.url))


class UserModelView(BaseModelView):
    column_list = ('name', 'email', 'encoded_token', 'active')


class CreatedByGesisModelView(BaseModelView):
    column_editable_list = ['position', 'repo_url', 'binder_url', 'description', 'active']
    column_default_sort = [('active', True), ('position', False)]

    def on_model_change(self, form, model, is_created):
        if form.repo_url and form.repo_url.data:
            provider_org_repo = repo_url_parts(form.repo_url.data)
            if len(provider_org_repo) == 3:
                return super().on_model_change(form, model, is_created)
            raise validators.ValidationError('Invalid repo url! '
                                             'It must in form "https://<provider>/<org_or_user/<repo_name>"')


class RepoModelView(BaseModelView):
    column_list = ('provider_spec', 'repo_url', 'description')
    column_searchable_list = ['provider_spec']
    column_editable_list = ['description']
    form_widget_args = {
        'launches': {
            'disabled': True
        }
    }


class BinderLaunchModelView(BaseModelView):
    can_delete = False
    can_edit = False
    column_default_sort = [('timestamp', True)]

    def is_accessible(self):
        # require Bearer token authentication for creating new launch entry
        if request.path == '/admin/binderlaunch/new/' and request.method == "POST":
            token = request.headers.get('Authorization')
            if token:
                if self.validate_form(self.create_form()):
                    token = token.replace('Bearer ', '', 1)
                    is_valid = User.validate_token(token)
                    if is_valid is True:
                        return True
                # TODO return the form error
                abort(400)
            abort(403)
        return super(BinderLaunchModelView, self).is_accessible()

    def after_model_change(self, form, model, is_created):

        target = model.provider + "/" + model.spec
        repo = Repo.query.filter_by(provider_spec=target).first()
        if not repo:
            provider_prefix, org, repo_name, ref = target.split('/')
            description=get_repo_description(f'https://www.github.com/{org}/{repo_name}/tree/{ref}')
            repo = Repo(provider_spec=target, description=description)
            db.session.add(repo)
            db.session.commit()


# Create customized index view class that handles login & registration
class AdminIndexView(BaseAdminIndexView):

    @expose('/')
    def index(self):
        if not login.current_user.is_authenticated:
            return redirect(url_for('.login_view'))
        return super(AdminIndexView, self).index()

    @expose('/login/', methods=('GET', 'POST'))
    def login_view(self):
        # handle user login
        form = LoginForm(request.form)

        if helpers.validate_form_on_submit(form):
            user = form.get_user()
            login.login_user(user)

        if login.current_user.is_authenticated:
            next_url = request.args.get("next")
            if next_url and not is_safe_url(next_url):
                return abort(400)
            return redirect(next_url or url_for('.index'))
        self._template_args['form'] = form
        return super(AdminIndexView, self).index()

    @expose('/logout/')
    def logout_view(self):
        login.logout_user()
        return redirect(url_for('.index'))
