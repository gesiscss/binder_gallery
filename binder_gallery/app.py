import os
from flask import Flask, render_template, abort
import flask_login as login
from flask_admin import Admin
from flask_debugtoolbar import DebugToolbarExtension
from .utilities_db import get_project_mixin
from .models import db, CreatedByGesis, User, Repo, BinderLaunch, FeaturedProject
from .admin import UserModelView, CreatedByGesisModelView, AdminIndexView, RepoModelView, BinderLaunchModelView, FeaturedProjectModelView


# Initialize flask-login
def init_login():
    login_manager = login.LoginManager()
    login_manager.init_app(app)

    # Create user loader function
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.query(User).get(user_id)


# app = Flask(__name__, template_folder='../templates/orc_site')
app = Flask(__name__)
# BG_DATABASE_URL = 'postgresql://%(user)s:%(pw)s@%(host)s:%(port)s/%(db)s'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['BG_DATABASE_URL']
app.config['SECRET_KEY'] = os.environ['BG_SECRET_KEY']
app.config['SESSION_COOKIE_NAME'] = 'bg_session'
app.config['SESSION_COOKIE_PATH'] = '/admin/'
# debug toolbar
toolbar = DebugToolbarExtension(app)
# SQLALCHEMY_TRACK_MODIFICATIONS
# If set to True (the default) Flask-SQLAlchemy will track modifications of objects and emit signals.
# This requires extra memory and can be disabled if not needed.
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
admin = Admin(app, name='Binder Gallery', index_view=AdminIndexView(),
              base_template='admin/master.html', template_mode='bootstrap3')
admin.add_view(UserModelView(User, db.session))
admin.add_view(CreatedByGesisModelView(CreatedByGesis, db.session))
admin.add_view(FeaturedProjectModelView(FeaturedProject, db.session))
admin.add_view(RepoModelView(Repo, db.session))
admin.add_view(BinderLaunchModelView(BinderLaunch, db.session))

# initialize db
db.init_app(app)
# Initialize flask-login
init_login()

# template context
staging = os.environ.get('DEPLOYMENT_ENV') == 'staging'
production = os.environ.get('DEPLOYMENT_ENV') == 'production'
site_url = 'https://notebooks{}.gesis.org'.format('-test' if staging else '')
context = {
    'staging': staging,
    'production': production,
    'version': 'beta',
    # 'shibboleth_entityID': f'{site_url}/shibboleth',

    'home_url': '/',
    'jhub_url': '/jupyter/',
    'gesis_login_url': f'{site_url}/Shibboleth.sso/Login?SAMLDS=1&'
                       f'target={site_url}/hub/login&'
                       f'entityID=https%3A%2F%2Fidp.gesis.org%2Fidp%2Fshibboleth',
    'bhub_url': '/binder/',
    'about_url': '/about/',
    'tou_url': '/terms_of_use/',
    'imprint_url': 'https://www.gesis.org/en/institute/imprint/',
    'data_protection_url': 'https://www.gesis.org/en/institute/data-protection/',
    'gesis_url': 'https://www.gesis.org/en/home/',
    'gallery_url': '/gallery/'
    # 'help_url': 'https://www.gesis.org/en/help/',
}


@app.route('/')
def gallery():
    # TODO get_popular_repos_all
    created_by_gesis = get_project_mixin(CreatedByGesis)
    featured_projcet = get_project_mixin(FeaturedProject)
    project_mixin = [('Created By Gesis', created_by_gesis), ('Featured Projects', featured_projcet)]
    context.update({'active': 'gallery',
                    # 'popular_repos_all': popular_repos_all,
                    'project_mixin': project_mixin,
                    })
    return render_template('gallery.html', **context)


@app.route('/popular_repos/<string:time_range>')
def popular_repos(time_range):
    titles = {'24h': 'Popular repositories in last 24 hours',
              '7d': 'Popular repositories in last week',
              '30d': 'Popular repositories in last 30 days',
              '60d': 'Popular repositories in last 60 days'}
    if time_range not in titles:
        abort(404)
    # TODO get_popular_repos(time_range)
    context.update({'active': 'gallery',
                    'title': titles[time_range],
                    'popular_repos': []})
    return render_template('popular_repos.html', **context)


@app.errorhandler(404)
def not_found(error):
    context.update({'status_code': error.code,
                    'status_message': error.name,
                    'message': error.description,
                    'active': None})
    return render_template('error.html', **context), 404


def run_app():
    app.run(debug=os.getenv('FLASK_DEBUG', False), host='0.0.0.0')


main = run_app

if __name__ == '__main__':
    main()
