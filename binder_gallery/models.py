import os
import jwt
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .utilities import provider_spec_to_url

PROVIDER_PREFIXES = {
    'Git': 'git',
    'GitHub': 'gh',
    'GitLab': 'gl',
    # 'gist.github.com': 'gist',
}

db = SQLAlchemy()


class ProjectMixin(object):
    id = db.Column(db.Integer, primary_key=True)
    position = db.Column(db.Integer, unique=True)
    repo_url = db.Column(db.String(), nullable=False)
    binder_url = db.Column(db.String(), nullable=False)
    description = db.Column(db.Text())
    active = db.Column(db.Boolean(), default=True)
    # def __init__(self, position, repo_url, binder_url, description, active):
    #     self.position = position
    #     self.repo_url = repo_url
    #     self.binder_url = binder_url
    #     self.description = description
    #     self.active = active

    def __repr__(self):
        return f'{self.id}: {self.repo_url}'

    def serialize(self):
        return {
            'id': self.id,
            'position': self.position,
            'repo_url': self.repo_url,
            'binder_url': self.binder_url,
            'description': self.description,
            'active': self.active
        }


class FeaturedProject(ProjectMixin, db.Model):
    __tablename__ = 'featured_project'


class CreatedByGesis(ProjectMixin, db.Model):
    __tablename__ = 'created_by_gesis'


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120))
    password_hash = db.Column(db.String(128))
    active = db.Column(db.Boolean(), default=True)

    # def __init__(self, name, email, password_hash, active):
    #     self.name = name
    #     self.email = email
    #     self.password_hash = password_hash
    #     # self.token = token
    #     self.active = active

    def __repr__(self):
        return f'{self.id}: {self.name}'

    # Required for administrative interface
    def __unicode__(self):
        return self.name

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    @property
    def encoded_token(self):
        try:
            token = jwt.encode({'id': self.id}, os.environ['BG_SECRET_KEY'], algorithm='HS256')
            token = token.decode()
            return token
        except Exception as e:
            return e

    @staticmethod
    def validate_token(encoded_token):
        try:
            payload = jwt.decode(encoded_token, os.environ['BG_SECRET_KEY'], algorithms='HS256')
        except Exception as e:
            return e
        return 'id' in payload

    # @classmethod
    # def create_user(cls, name, password):
    #     u = cls(name, "", generate_password_hash(password), True)
    #     db.session.add(u)
    #     db.session.commit()


class Repo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # http://flask-sqlalchemy.pocoo.org/2.3/models/#one-to-many-relationships
    launches = db.relationship('BinderLaunch',
                               backref=db.backref('detail', lazy='joined'),
                               lazy='dynamic')
    provider_spec = db.Column(db.String, unique=True, index=True)
    description = db.Column(db.Text)

    def __repr__(self):
        return f'{self.id}: {self.provider_spec}'

    @property
    def url(self):
        return provider_spec_to_url(self.provider_spec)


class BinderLaunch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schema = db.Column(db.String, nullable=False)
    version = db.Column(db.String, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    provider = db.Column(db.String, nullable=False)  # provider_name
    spec = db.Column(db.String, nullable=False)
    # may be useful to index in the future
    repo_id = db.Column(db.Integer, db.ForeignKey('repo.id'), nullable=True)
    status = db.Column(db.String, nullable=False)

    def __repr__(self):
        return f'{self.id}'

    @property
    def provider_spec(self):
        return f'{PROVIDER_PREFIXES[self.provider]}/{self.spec}'

    @property
    def repo_url(self):
        return provider_spec_to_url(self.provider_spec)

    @property
    def repo_description(self):
        return self.detail.description if self.detail else ''
