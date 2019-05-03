import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    # Flask-SQLAlchemy config: https://flask-sqlalchemy.palletsprojects.com/en/2.x/config/#configuration-keys
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "local.sqlite")
    # If set to True (the default) Flask-SQLAlchemy will track modifications of objects and emit signals.
    # This requires extra memory and can be disabled if not needed.
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # binder gallery config
    BASE_URL = os.getenv("BG_BASE_URL", "/")
    # default binder url. default is GESIS binder
    BINDER_URL = "https://notebooks.gesis.org/binder"

    # flask builtin config: http://flask.pocoo.org/docs/1.0/config/#builtin-configuration-values
    SECRET_KEY = "development-secret"
    APPLICATION_ROOT = BASE_URL
    SERVER_NAME = "127.0.0.1:5000"
    SESSION_COOKIE_DOMAIN = "127.0.0.1"
    SESSION_COOKIE_NAME = "bg_session"
    SESSION_COOKIE_PATH = f"{BASE_URL}admin"
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
