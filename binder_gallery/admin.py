import base64
import flask_login as login
from flask import request, url_for, redirect, abort
from flask_admin import AdminIndexView as BaseAdminIndexView, expose, helpers
from flask_admin.contrib.sqla import ModelView
from flask_admin.helpers import is_safe_url
from wtforms import validators
from .forms import LoginForm
from .models import User
from .utilities import repo_url_parts


class UserModelView(ModelView):

    def is_accessible(self):
        # if request.path == '/admin/binderlaunches/new/' and request.method == "POST":
        #     # try to login using Bearer token
        #     token = request.headers.get('Authorization')
        #     if token:
        #         # token = token.replace('Basic ', '', 1)
        #         token = token.replace('Bearer ', '', 1)
        #         try:
        #             token = base64.b64decode(token)
        #         except TypeError:
        #             pass
        #         if User.query.filter_by(token=token).first():
        #             return True

        return login.current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return redirect(url_for('admin.login_view', next=request.url))


class CreatedByGesisModelView(UserModelView):
    def on_model_change(self, form, model, is_created):
        if form.repo_url.data:
            provider_org_repo = repo_url_parts(form.repo_url.data)
            if len(provider_org_repo) == 3:
                return super().on_model_change(form, model, is_created)
        raise validators.ValidationError('Invalid repo url! '
                                         'It must in form "https://<provider>/<org_or_user/<repo_name>"')

    @expose('/new/', methods=('GET', 'POST'))
    def create_view(self):

        return super(CreatedByGesisModelView, self).create_view()


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
