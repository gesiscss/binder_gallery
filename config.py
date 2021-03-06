import os
from dirhash import dirhash
basedir = os.path.abspath(os.path.dirname(__file__))
static_sha1 = dirhash("binder_gallery/static", "sha1", ignore=["vendor/*"])
template_vars = {
    'static_version': static_sha1,
    'extra_header': None,
}


class Config(object):
    # Flask-SQLAlchemy config: https://flask-sqlalchemy.palletsprojects.com/en/2.x/config/#configuration-keys
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "local.sqlite")
    # If set to True (the default) Flask-SQLAlchemy will track modifications of objects and emit signals.
    # This requires extra memory and can be disabled if not needed.
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # binder gallery config
    BASE_URL = os.getenv("BG_BASE_URL", "/")
    # list of binders. default is GESIS binder.
    BINDERS = [
        {'name': 'GESIS', 'url': 'https://notebooks.gesis.org/binder', 'default': "true"},
        {'name': 'mybinder.org', 'url': 'https://mybinder.org', 'main': 'true'},
        {'name': 'Pangeo', 'url': 'https://binder.pangeo.io'},
    ]

    intervals = {
        '24h': {'title': 'Last 24 hours', 'show': True},
        '7d': {'title': 'Last week', 'show': True},
        '30d': {'title': 'Last 30 days', 'show': True},
        '60d': {'title': 'Last 60 days', 'show': True, "load_dynamic": True},
        'all': {'title': 'All time', 'show': True, "load_dynamic": True}
    }
    BINDER_ORIGINS = {
        'gesisbinder': {
            'show': True,
            'title': 'Popular Repositories of GESIS Binder',
            # origin '' is for those before version 3 (without origin)
            'origins': ('notebooks.gesis.org', ''),
            'intervals': intervals
        },
        'mybinder': {
            'show': True,
            'title': 'Popular Repositories of mybinder.org',
            # origin 'mybinder.org' is for mybinder.org events before version 3
            'origins': ('notebooks.gesis.org', '', 'gke.mybinder.org', 'ovh.mybinder.org', 'binder.mybinder.ovh', 'mybinder.org'),
            'intervals': intervals
        }
    }
    DETAIL_PAGES = {
        '24h': {'title': 'Launches in last 24 hours', 'show': True},
        '7d': {'title': 'Launches in last week', 'show': True},
        '30d': {'title': 'Launches in last 30 days', 'show': True},
        '60d': {'title': 'Launches in last 60 days', 'show': True},
        'all': {'title': 'Launches in all time', 'show': True}
    }

    TEMPLATE_VARS = template_vars

    # flask builtin config: http://flask.pocoo.org/docs/1.0/config/#builtin-configuration-values
    SECRET_KEY = "development-secret"
    APPLICATION_ROOT = BASE_URL
    SERVER_NAME = "127.0.0.1:5000"
    SESSION_COOKIE_DOMAIN = False
    SESSION_COOKIE_NAME = "bg_session"
    SESSION_COOKIE_PATH = f"{BASE_URL}admin"
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    SQLALCHEMY_ECHO = False
