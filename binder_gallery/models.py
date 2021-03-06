import jwt
import architect
from requests import get
from bs4 import BeautifulSoup
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import cached_property
from urllib.parse import unquote

from binder_gallery import db, app


PROVIDER_PREFIXES = {
    # name: prefix
    'Git': 'git',  # Bare bones git repo provider: full url + commit sha
    'Gist': 'gist',  # gist.github.com: username/gistId or full url + commit sha
    'GitHub': 'gh',  # github.com: repo name or full url + branch/tag/commit
    'GitLab': 'gl',  # gitlab.com: repo name or full url + branch/tag/commit
    'Zenodo': 'zenodo',  # Zenodo DOI
    'Figshare': 'figshare',
    'Hydroshare': 'hydroshare',
    'Dataverse': 'dataverse',
}


def _strip(type_, text, affixes):
    if type(affixes) == str:
        affixes = [affixes]

    for affix in affixes:
        if type_ == 'prefix':
            if text.startswith(affix):
                text = text[len(affix):]
        elif type_ == 'suffix':
            if text.endswith(affix):
                text = text[:-(len(affix))]
    return text


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
        return _strip('suffix',
                      _strip('prefix', self.repo_url, ['https://', 'http://']),
                      ['.git']).rsplit('/', 2)

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
        elif 'doi.org' in provider:
            if "zenodo" in repo_name.lower():
                provider = 'Zenodo'
            elif "figshare" in repo_name.lower():
                provider = 'Figshare'
            else:
                provider = 'Dataverse'
        elif "hydroshare.org" in provider:
            provider = 'Hydroshare'
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
            # user name to make tokens unique per user
            token = jwt.encode({'launch': True, 'name': self.name}, app.config['SECRET_KEY'], algorithm='HS256')
            token = token.decode()
            return token
        except Exception as e:
            app.logger.error(f"Error: token generation {e}")
            return e

    @staticmethod
    def validate_token(encoded_token, permission='launch'):
        try:
            payload = jwt.decode(encoded_token, app.config['SECRET_KEY'], algorithms='HS256')
        except Exception as e:
            from flask import request
            app.logger.error(f"Error: token validation: {request.remote_addr} requested {request.url}: {e}")
            return False
        return payload.get(permission, False)

    @classmethod
    def create_user(cls, name, password, email="", active=True):
        u = cls(name=name, email=email, password_hash=generate_password_hash(password), active=active)
        db.session.add(u)
        db.session.commit()
        return u


class RepoMixin(object):

    @cached_property
    def spec_parts(self):
        if self.provider_prefix in ['zenodo', 'figshare', 'dataverse']:
            # ref is always ''
            repo_url = f"https://doi.org/{self.spec}"
            parts = ['', self.spec, '', repo_url]
        elif self.provider_prefix == 'hydroshare':
            # ref is always ''
            resource_id = self.spec.split("/")[-1].split(".")[-1]
            repo_url = f"https://www.hydroshare.org/resource/{resource_id}"
            parts = ['', resource_id, '', repo_url]
        elif self.provider_prefix == 'git':
            repo_url, resolved_ref = self.spec.rsplit('/', 1)
            repo_url = unquote(repo_url)
            repo_name = _strip('suffix',
                               _strip('prefix', repo_url, ['https://', 'http://']),
                               ['.git'])
            parts = ['', repo_name, resolved_ref, repo_url]
        elif self.provider_prefix == 'gh':
            org, repo_name, unresolved_ref = self.spec.split('/', 2)
            repo_name = _strip('suffix', repo_name, ['.git'])
            parts = [org, repo_name, unresolved_ref]
        elif self.provider_prefix == 'gl':
            quoted_namespace, unresolved_ref = self.spec.split('/', 1)
            namespace = unquote(quoted_namespace)
            org, repo_name = namespace.split('/', 1)
            repo_name = _strip('suffix', repo_name, ['.git'])
            # unresolved_ref = unquote(unresolved_ref)
            parts = [org, repo_name, unresolved_ref]
        elif self.provider_prefix == 'gist':
            user_name, gist_id, *_unresolved_ref = self.spec.split('/', 2)
            unresolved_ref = _unresolved_ref[0] if _unresolved_ref else 'master'
            parts = [user_name, gist_id, unresolved_ref]
        return parts

    @cached_property
    def repo_namespace(self):
        org, repo_name = self.spec_parts[:2]
        return org, repo_name

    @cached_property
    def repo_url(self):
        if self.provider_prefix in ['git', 'zenodo', 'figshare', 'hydroshare', 'dataverse']:
            repo_url = self.spec_parts[3]
        elif self.provider_prefix == 'gh':
            org, repo_name = self.repo_namespace
            repo_url = f'https://www.github.com/{org}/{repo_name}'
        elif self.provider_prefix == 'gl':
            org, repo_name = self.repo_namespace
            repo_url = f'https://www.gitlab.com/{org}/{repo_name}'
        elif self.provider_prefix == 'gist':
            user_name, gist_id = self.repo_namespace
            repo_url = f'https://gist.github.com/{user_name}/{gist_id}'
        return repo_url

    # @property
    # def ref_url(self):
    #     if self.provider_prefix == 'git':
    #         # FIXME ref is missing
    #         ref_url = self.spec_parts[3]
    #     # FIXME we need resolved refs
    #     elif self.provider_prefix == 'gh':
    #         org, repo_name, *r = self.spec_parts
    #         ref_url = f'https://www.github.com/{org}/{repo_name}/tree/{r[0]}'
    #     elif self.provider_prefix == 'gl':
    #         org, repo_name, *r = self.spec_parts
    #         ref_url = f'https://www.gitlab.com/{org}/{repo_name}/tree/{r[0]}'
    #     elif self.provider_prefix == 'gist':
    #         user_name, gist_id, *r = self.spec_parts
    #         ref_url = f'https://gist.github.com/{user_name}/{gist_id}/{r[0]}'
    #     return ref_url

    @property
    def binder_url(self):
        return f'{app.default_binder_url}/v2/{self.provider_spec}'

    # @property
    # def binder_ref_url(self):
    #     # TODO this should be v2/spec_with_resolved_ref
    #     return f'{app.default_binder_url}/v2/{self.provider_spec}'

    def get_repo_description(self):
        repo_url = self.repo_url
        if 'github.com' not in repo_url or 'gist.github.com' in repo_url:
            # only for GitHub repos
            return ''
        try:
            page = get(repo_url, timeout=1)
        except Exception:
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
                               backref=db.backref('detail', lazy='select'),
                               lazy='dynamic')
    provider_namespace = db.Column(db.String, unique=True, index=True)  # provider_prefix/namespace
    description = db.Column(db.Text)
    last_ref = db.Column(db.String, default="master", server_default="master")  # last launched ref

    def __repr__(self):
        return f'{self.id}: {self.provider_namespace}'

    @cached_property
    def provider_prefix(self):
        for prefix in PROVIDER_PREFIXES.values():
            if self.provider_namespace.startswith(prefix+'/'):
                return prefix
        raise ValueError(f'{self.provider_namespace} is not valid.')

    @cached_property
    def provider(self):
        for provider_name, prefix in PROVIDER_PREFIXES.items():
            if self.provider_namespace.startswith(prefix+'/'):
                return provider_name
        raise ValueError(f'{self.provider_namespace} is not valid.')

    @property
    def provider_spec(self):
        if self.provider_prefix in ['zenodo', 'figshare', 'hydroshare', 'dataverse']:
            # zenodo and figshare have no ref info
            provider_spec = self.provider_namespace
        else:
            provider_spec = self.provider_namespace + "/" + self.last_ref
        return provider_spec

    @property
    def spec(self):
        return self.provider_spec[len(self.provider_prefix+'/'):]

    # def get_binder_url(self, spec):
    #     return f'{app.default_binder_url}/v2/{self.provider_prefix}/{spec}'


@architect.install('partition', type='range', subtype='date', constraint='year', column='timestamp', orm='sqlalchemy', db=app.config['SQLALCHEMY_DATABASE_URI'])
class BinderLaunch(RepoMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schema = db.Column(db.String, nullable=False)
    version = db.Column(db.String, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    origin = db.Column(db.String, nullable=True, index=True, default="", server_default="")
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

    @property
    def provider_namespace(self):
        if self.provider_prefix in ["zenodo", "figshare", "hydroshare", "dataverse"]:
            # zenodo and figshare have no ref info
            provider_namespace = self.provider_spec
        else:
            provider_spec_parts = self.provider_spec.split('/')
            # strip ref info from provider_spec_parts
            if self.provider_prefix in ['gh', 'gl']:
                # gh and gl branches can contain "/"
                provider_spec_parts = provider_spec_parts[:3]
            else:
                # git and gist have ref only as commit SHA
                provider_spec_parts = provider_spec_parts[:-1]
            provider_namespace = _strip('suffix',
                                        "/".join(provider_spec_parts),
                                        ['.git'])
        return provider_namespace
