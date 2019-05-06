import flask_login as login
from flask import request, url_for, redirect, abort, jsonify
from flask.helpers import get_debug_flag, make_response
from flask_admin import AdminIndexView as BaseAdminIndexView, expose, helpers, Admin, BaseView
from flask_admin.contrib.sqla import ModelView
from flask_admin.helpers import is_safe_url
from wtforms import validators
from .forms import LoginForm
from .models import User, Repo, CreatedByGesis, FeaturedProject, BinderLaunch
from . import app, db, cache

DEBUG_FLAG = get_debug_flag()


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
    column_list = ('provider_namespace', 'repo_url', 'description')
    column_searchable_list = ['provider_namespace']
    column_editable_list = ['description']


class BinderLaunchModelView(BaseModelView):
    can_delete = DEBUG_FLAG
    can_edit = DEBUG_FLAG
    column_default_sort = [('timestamp', True)]
    column_list = ('timestamp', 'provider', 'provider_spec', 'repo_id', 'repo_description')

    def is_accessible(self):
        # require Bearer token authentication for creating new launch entry
        if not DEBUG_FLAG and \
           request.path.endswith('/admin/binderlaunch/new/') and \
           request.method == "POST":
            token = request.headers.get('Authorization')
            if token:
                form = self.create_form()
                if self.validate_form(form):
                    token = token.replace('Bearer ', '', 1)
                    if User.validate_token(token) is True:
                        return True
                    abort(make_response(jsonify(error="Authorization token is not valid."), 400))
                abort(make_response(jsonify(**form.errors), 400))
            abort(make_response(jsonify(error="Authorization token is needed."), 403))
        return super(BinderLaunchModelView, self).is_accessible()

    def on_model_change(self, form, model, is_created):
        # https://docs.sqlalchemy.org/en/latest/orm/session_api.html
        if is_created is True:
            # model was added into session before checking if repo exist, thats why we remove it first
            self.session.expunge(model)
            provider_namespace = model.provider_spec.rsplit('/', 1)[0]  # without ref
            repo = Repo.query.filter_by(provider_namespace=provider_namespace).first()
            app.logger.info(f"New binder launch {model.provider_spec} on {model.timestamp} - "
                            f"{model.schema} {model.version} {model.status}")
            description = model.get_repo_description()
            if repo:
                repo.launches.append(model)
                repo.description = description
            else:
                repo = Repo(provider_namespace=provider_namespace, description=description, launches=[model])
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


class CacheView(BaseView):
    @expose('/')
    def index(self):
        with app.app_context():
            cache.clear()
        return redirect(url_for('admin.index'))


admin = Admin(app, name='Binder Gallery', index_view=AdminIndexView(),
              base_template='admin/master.html', template_mode='bootstrap3')

admin.add_view(UserModelView(User, db.session))
admin.add_view(RepoModelView(Repo, db.session))
admin.add_view(CreatedByGesisModelView(CreatedByGesis, db.session))
admin.add_view(FeaturedProjectModelView(FeaturedProject, db.session))
admin.add_view(BinderLaunchModelView(BinderLaunch, db.session))
admin.add_view(CacheView(name='Clear Cache', endpoint='clear_cache'))
