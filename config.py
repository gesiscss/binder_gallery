import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "local.sqlite")

    # If set to True (the default) Flask-SQLAlchemy will track modifications of objects and emit signals.
    # This requires extra memory and can be disabled if not needed.
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    BG_ADMIN_URL = "/admin"

    SECRET_KEY = "development-secret"
    SESSION_COOKIE_NAME = "bg_session"
    SESSION_COOKIE_PATH = BG_ADMIN_URL

    # default binder url. default is GESIS binder
    BINDER_URL = "https://notebooks.gesis.org/binder"
