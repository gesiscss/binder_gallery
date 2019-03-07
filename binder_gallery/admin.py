import os
import flask_login as login
from flask import request, url_for, redirect, abort
from flask_admin import AdminIndexView as BaseAdminIndexView, expose, helpers
from flask_admin.contrib.sqla import ModelView
from flask_admin.helpers import is_safe_url
from wtforms import validators
from .forms import LoginForm
from .models import User, Repo


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
            if len(model.repo_url_parts) == 3:
                return super().on_model_change(form, model, is_created)
            raise validators.ValidationError('Invalid repo url! '
                                             'It must in form "https://<provider>/<org_or_user/<repo_name>"')


class FeaturedProjectModelView(CreatedByGesisModelView):
    pass


class RepoModelView(BaseModelView):
    column_list = ('provider_spec', 'url', 'description')
    column_searchable_list = ['provider_spec']
    column_editable_list = ['description']
    form_widget_args = {
        'launches': {
            'disabled': True
        }
    }


class BinderLaunchModelView(BaseModelView):
    can_delete = True if os.environ.get('FLASK_DEBUG', False) in [1, '1', True] else False
    can_edit = True if os.environ.get('FLASK_DEBUG', False) in [1, '1', True] else False
    column_default_sort = [('timestamp', True)]
    column_list = ('schema', 'version', 'timestamp', 'provider', 'status', 'repo_id', 'repo_description')

    def is_accessible(self):
        # require Bearer token authentication for creating new launch entry
        if not os.environ.get('FLASK_DEBUG', False) and request.path == '/admin/binderlaunch/new/' and request.method == "POST":
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

    def on_model_change(self, form, model, is_created):
        # https://docs.sqlalchemy.org/en/latest/orm/session_api.html
        if is_created is True:
            # model was added into session before checking if repo exist, thats why we remove it first
            self.session.expunge(model)
            provider_spec = model.provider_spec
            repo = Repo.query.filter_by(provider_spec=provider_spec).first()
            description = model.get_repo_description()
            if repo:
                repo.launches.append(model)
                repo.description = description
            else:
                repo = Repo(provider_spec=provider_spec, description=description, launches=[model])
                self.session.add(repo)
            # Now the model should be added
            # into the Session after adding repo instance.
            self.session.add(model)


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
