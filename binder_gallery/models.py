from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


db = SQLAlchemy()


class CreatedByGesis(db.Model):
    __tablename__ = 'created_by_gesis'

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


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120))
    password_hash = db.Column(db.String(128))
    token = db.Column(db.BINARY(64))
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

    # @classmethod
    # def create_user(cls, name, password):
    #     u = cls(name, "", generate_password_hash(password), True)
    #     db.session.add(u)
    #     db.session.commit()
