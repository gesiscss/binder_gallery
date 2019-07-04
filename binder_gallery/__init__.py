import os
from flask_caching import Cache
from flask_sqlalchemy import SQLAlchemy
from .flask_app import Flask
from apscheduler.schedulers.background import BackgroundScheduler


# set static_folder to None in order to prevent adding default static url rule
# it will be added manually later in __init__
app = Flask(__name__, static_folder=None)

if not app.debug:
    # configure flask.app logger
    import logging
    # sh = logging.StreamHandler()
    # formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
    # sh.setFormatter(formatter)
    # app.logger.handlers = [sh]
    app.logger.setLevel(logging.INFO)
    # reverse proxy fix
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app)

db = SQLAlchemy()
project_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
cache = Cache(config={'CACHE_TYPE': 'filesystem',
                      'CACHE_DIR': os.path.join(project_dir, 'bg_cache')})


def check_mybinder():
    from .mybinder_launches import mybinder_stream
    mybinder_stream()


scheduler = BackgroundScheduler()
job = scheduler.add_job(check_mybinder, 'interval', minutes=120)
scheduler.start()


def init_plugins():
    # add routes
    import binder_gallery.views
    import binder_gallery.api

    # debug toolbar
    if app.debug:
        from flask_debugtoolbar import DebugToolbarExtension
        toolbar = DebugToolbarExtension(app)

    # initialize db
    # TODO how to detect a new migration and apply it?
    db.init_app(app)

    cache.init_app(app)

    # initialize flask-login
    import flask_login as login
    from binder_gallery.models import User
    login_manager = login.LoginManager()
    login_manager.init_app(app)

    # create user loader function
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.query(User).get(user_id)

    # flask admin
    from binder_gallery import admin

    # flask commands
    import binder_gallery.commands


# init plugins after the app is initialized
init_plugins()
