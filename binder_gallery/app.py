import os
import requests
from flask import Flask, render_template, abort, make_response, request
import flask_login as login
from flask_admin import Admin
from flask_debugtoolbar import DebugToolbarExtension
from .utilities_db import get_projects, get_launched_repos
from .models import db, CreatedByGesis, User, Repo, BinderLaunch, FeaturedProject, BINDER_URL
from .admin import UserModelView, CreatedByGesisModelView, AdminIndexView, RepoModelView, \
    BinderLaunchModelView, FeaturedProjectModelView
from logging.config import dictConfig
from flask_restful import Resource, Api

app = Flask(__name__)


def get_binders(fetch_versions=True):
    binders = [
        {'name': 'GESIS', 'url': 'https://notebooks.gesis.org/binder', 'selected': 'false'},
        {'name': 'mybinder.org', 'url': 'https://mybinder.org', 'selected': 'false'},
        {'name': 'Pangeo', 'url': 'https://binder.pangeo.io', 'selected': 'false'},
    ]
    selected_binder = request.cookies.get('selected_binder')
    for binder in binders:
        if binder['name'] == selected_binder:
            binder['selected'] = 'true'

    if fetch_versions is True:
        for binder in binders:
            versions = "No versions info is available"
            try:
                response = requests.get(binder['url'] + '/versions', timeout=0.5)
                if response.status_code == 200:
                    versions = response.json()
                    versions = f"BinderHub {versions['binderhub']} with {versions['builder']}"
            except Exception as e:
                app.logger.error(e)
            binder['versions'] = versions
    return binders


def get_default_template_context():
    staging = app.debug
    production = not app.debug
    context = {
        'staging': staging,
        'production': production,
        'version': 'beta',
        'home_url': '/',
        'jhub_url': '/jupyter/',
        'bhub_url': '/binder/',
        'about_url': '/about/',
        'tou_url': '/terms_of_use/',
        'imprint_url': 'https://www.gesis.org/en/institute/imprint/',
        'data_protection_url': 'https://www.gesis.org/en/institute/data-protection/',
        'gesis_url': 'https://www.gesis.org/en/home/',
        'gallery_url': '/gallery/',
        # 'help_url': 'https://www.gesis.org/en/help/',
        'binder_url': BINDER_URL,
    }
    return context


@app.route('/select_binder', methods=['POST'])
def select_binder():
    selected_binder = request.json['name']
    resp = make_response(f"Selected Binder: {selected_binder}")
    resp.set_cookie("selected_binder", selected_binder)
    return resp


@app.route('/')
def gallery():
    _popular_repos_all = [
        ('24h', 'Last 24 hours', get_launched_repos('24h'), ),
        ('7d', 'Last week', get_launched_repos('7d'), ),
        ('30d', 'Last 30 days', get_launched_repos('30d'), ),
        ('60d', 'Last 60 days', get_launched_repos('60d'), ),
    ]
    popular_repos_all = []
    # don't show empty tabs (no launched happened)
    for pr in _popular_repos_all:
        if pr[-1]:
            popular_repos_all.append(pr)
    del _popular_repos_all

    projects = [('Created By Gesis', get_projects(CreatedByGesis)),
                ('Featured Projects', get_projects(FeaturedProject))]
    context = get_default_template_context()
    context.update({'active': 'gallery',
                    'popular_repos_all': popular_repos_all,
                    'projects': projects,
                    'binders': get_binders(),
                    })
    return render_template('gallery.html', **context)


@app.route('/<string:time_range>')
def popular_repos(time_range):
    titles = {'24h': 'Popular repositories in last 24 hours',
              '7d': 'Popular repositories in last week',
              '30d': 'Popular repositories in last 30 days',
              '60d': 'Popular repositories in last 60 days'}
    if time_range not in titles:
        abort(404)

    context = get_default_template_context()
    context.update({'active': 'gallery',
                    'title': titles[time_range],
                    'binders': get_binders(),
                    'popular_repos': get_launched_repos(time_range)})
    return render_template('popular_repos.html', **context)


class ReposLaunches(Resource):
    def get(self, time_range):
        repos = get_launched_repos(time_range)
        return repos


api = Api(app)
api.add_resource(ReposLaunches, '/gesisgallery/api/v1.0/repos/<string:time_range>')


@app.errorhandler(404)
def not_found(error):
    context = get_default_template_context()
    context.update({'status_code': error.code,
                    'status_message': error.name,
                    'message': error.description,
                    'active': None})
    return render_template('error.html', **context), 404


def init():
    # http://flask.pocoo.org/docs/1.0/logging/
    dictConfig({
        'version': 1,
        'formatters': {'default': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        }},
        'handlers': {'wsgi': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://flask.logging.wsgi_errors_stream',
            'formatter': 'default'
        }},
        'root': {
            'level': 'INFO',
            'handlers': ['wsgi']
        }
    })

    admin_url = "/admin"
    # BG_DATABASE_URL = 'postgresql://%(user)s:%(pw)s@%(host)s:%(port)s/%(db)s'
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['BG_DATABASE_URL']
    app.config['SECRET_KEY'] = os.environ['BG_SECRET_KEY']
    app.config['SESSION_COOKIE_NAME'] = 'bg_session'
    app.config['SESSION_COOKIE_PATH'] = admin_url
    if app.debug:
        # debug toolbar
        toolbar = DebugToolbarExtension(app)
    # SQLALCHEMY_TRACK_MODIFICATIONS
    # If set to True (the default) Flask-SQLAlchemy will track modifications of objects and emit signals.
    # This requires extra memory and can be disabled if not needed.
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    admin = Admin(app, name='Binder Gallery', index_view=AdminIndexView(url=admin_url),
                  base_template='admin/master.html', template_mode='bootstrap3')
    admin.add_view(UserModelView(User, db.session))
    admin.add_view(CreatedByGesisModelView(CreatedByGesis, db.session))
    admin.add_view(FeaturedProjectModelView(FeaturedProject, db.session))
    admin.add_view(RepoModelView(Repo, db.session))
    admin.add_view(BinderLaunchModelView(BinderLaunch, db.session))

    # initialize db
    db.init_app(app)

    # Initialize flask-login
    login_manager = login.LoginManager()
    login_manager.init_app(app)

    # Create user loader function
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.query(User).get(user_id)


def run_app():
    init()
    app.run(host='0.0.0.0')


main = run_app

if __name__ == '__main__':
    main()
