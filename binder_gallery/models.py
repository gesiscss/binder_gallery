import os
import jwt
import architect
from requests import get
from requests.exceptions import Timeout
from bs4 import BeautifulSoup
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import cached_property
from urllib.parse import unquote

PROVIDER_PREFIXES = {
    # name: prefix
    'Git': 'git',  # Bare bones git repo provider: full url + commit sha
    'Gist': 'gist',  # gist.github.com: username/gistId or full url + commit sha
    'GitHub': 'gh',  # github.com: repo name or full url + branch/tag/commit
    'GitLab': 'gl',  # gitlab.com: repo name or full url + branch/tag/commit
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

    @cached_property
    def repo_url_parts(self):
        # provider, org, repo_name
        return self.repo_url.replace('https://', '').rstrip('.git').rsplit('/', 2)

    @property
    def provider(self):
        provider, org, repo_name = self.repo_url_parts
        provider = provider.lower()
        if 'github.com' in provider and 'gist.github.com' not in provider:
            provider = 'GitHub'
        elif 'gitlab.com' in provider:
            provider = 'GitLab'
        elif 'gist.github.com' in provider:
            provider = 'Gist'
        else:
            provider = 'Git'
        return provider

    @property
    def org(self):
        return self.repo_url_parts[1]

    @property
    def repo_name(self):
        return self.repo_url_parts[2]


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


class RepoMixin(object):

    @cached_property
    def spec_parts(self):
        if self.provider_prefix == 'git':
            repo_url, resolved_ref = self.spec.rsplit('/', 1)
            repo_url = unquote(repo_url)
            parts = ['', repo_url, resolved_ref]
        elif self.provider_prefix == 'gh':
            org, repo_name, unresolved_ref = self.spec.split('/', 2)
            parts = [org, repo_name, unresolved_ref]
        elif self.provider_prefix == 'gl':
            quoted_namespace, unresolved_ref = self.spec.split('/', 1)
            namespace = unquote(quoted_namespace)
            org, repo_name = namespace.split('/', 1)
            # unresolved_ref = unquote(unresolved_ref)
            parts = [org, repo_name, unresolved_ref]
        elif self.provider_prefix == 'gist':
            user_name, gist_id, *_unresolved_ref = self.spec.split('/', 2)
            unresolved_ref = _unresolved_ref[0] if _unresolved_ref else 'master'
            parts = [user_name, gist_id, unresolved_ref]
        return parts

    @cached_property
    def repo_url(self):
        if self.provider_prefix == 'git':
            repo_url = self.spec_parts[1]
        elif self.provider_prefix == 'gh':
            org, repo_name, unresolved_ref = self.spec_parts
            repo_url = f'https://www.github.com/{org}/{repo_name}'
        elif self.provider_prefix == 'gl':
            org, repo_name, unresolved_ref = self.spec_parts
            repo_url = f'https://www.gitlab.com/{org}/{repo_name}'
        elif self.provider_prefix == 'gist':
            user_name, gist_id, unresolved_ref = self.spec_parts
            repo_url = f'https://gist.github.com/{user_name}/{gist_id}'
        return repo_url

    @property
    def ref_url(self):
        if self.provider_prefix == 'git':
            # FIXME ref is missing
            ref_url = self.spec_parts[1]
        # FIXME we need resolved refs
        elif self.provider_prefix == 'gh':
            org, repo_name, unresolved_ref = self.spec_parts
            ref_url = f'https://www.github.com/{org}/{repo_name}/tree/{unresolved_ref}'
        elif self.provider_prefix == 'gl':
            org, repo_name, unresolved_ref = self.spec_parts
            ref_url = f'https://www.gitlab.com/{org}/{repo_name}/tree/{unresolved_ref}'
        elif self.provider_prefix == 'gist':
            user_name, gist_id, unresolved_ref = self.spec_parts
            ref_url = f'https://gist.github.com/{user_name}/{gist_id}/{unresolved_ref}'
        return ref_url

    @property
    def binder_url(self):
        return f'https://notebooks.gesis.org/binder/v2/{self.provider_spec}'

    @property
    def binder_ref_url(self):
        # TODO this should be v2/spec_with_resolved_ref
        return f'https://notebooks.gesis.org/binder/v2/{self.provider_spec}'

    def get_repo_description(self):
        repo_url = self.repo_url
        if 'github.com' not in repo_url or 'gist.github.com' in repo_url:
            # only for GitHub repos
            return ''
        try:
            page = get(repo_url, timeout=1)
        except Timeout as e:
            return ''
        soup = BeautifulSoup(page.content, 'html.parser')
        about = soup.find('span', itemprop='about')
        url = soup.find('span', itemprop='url')
        if about or url:
            text = about.text.strip() if about else ''
            # url = ' ' + url.find('a').text.strip() if url else ''
            url = str(url.find('a')) if url else ''
            return f'{text} {url}'.strip()
        return ''


class Repo(RepoMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # http://flask-sqlalchemy.pocoo.org/2.3/models/#one-to-many-relationships
    launches = db.relationship('BinderLaunch',
                               backref=db.backref('detail', lazy='joined'),
                               lazy='dynamic')
    provider_spec = db.Column(db.String, unique=True, index=True)  # provider_prefix/spec
    description = db.Column(db.Text)

    def __repr__(self):
        return f'{self.id}: {self.provider_spec}'

    @cached_property
    def provider_prefix(self):
        for prefix in PROVIDER_PREFIXES.values():
            if self.provider_spec.startswith(prefix+'/'):
                return prefix
        raise ValueError(f'{self.provider_spec} is not valid.')

    @property
    def spec(self):
        for prefix in PROVIDER_PREFIXES.values():
            if self.provider_spec.startswith(prefix+'/'):
                return self.provider_spec.lstrip(prefix+'/')
        raise ValueError(f'{self.provider_spec} is not valid.')


@architect.install('partition', type='range', subtype='date', constraint='year', column='timestamp', orm='sqlalchemy', db=os.environ['BG_DATABASE_URL'])
class BinderLaunch(RepoMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schema = db.Column(db.String, nullable=False)
    version = db.Column(db.String, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    provider = db.Column(db.String, nullable=False)  # provider_name
    spec = db.Column(db.String, nullable=False)
    repo_id = db.Column(db.Integer, db.ForeignKey('repo.id'), nullable=True, index=True)
    status = db.Column(db.String, nullable=False)

    def __repr__(self):
        return f'{self.id}'

    @cached_property
    def provider_prefix(self):
        return PROVIDER_PREFIXES[self.provider]

    @property
    def provider_spec(self):
        return f'{self.provider_prefix}/{self.spec}'

    @property
    def repo_description(self):
        return self.detail.description if self.detail else ''
