from flask_caching import Cache
from flask_sqlalchemy import SQLAlchemy
from .flask_app import Flask

# configure logging before creating the application object
# http://flask.pocoo.org/docs/1.0/logging/
from logging.config import dictConfig
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


# set static_folder to None in order to prevent adding default static url rule
# it will be added manually later in __init__
app = Flask(__name__, static_folder=None)
if not app.debug:
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app)
db = SQLAlchemy()
cache = Cache(config={'CACHE_TYPE': 'simple'})


def init_plugins():
    # add routes
    import binder_gallery.views

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
