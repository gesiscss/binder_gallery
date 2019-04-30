import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
db = SQLAlchemy()


def init_app():
    app.config.from_object('config.Config')
    # to override default config
    custom_config = os.getenv('BG_APPLICATION_SETTINGS')
    if custom_config:
        app.config.from_object(custom_config)

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

    # debug toolbar
    if app.debug:
        from flask_debugtoolbar import DebugToolbarExtension
        toolbar = DebugToolbarExtension(app)

    # initialize db
    db.init_app(app)

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


init_app()
