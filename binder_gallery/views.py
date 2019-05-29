import requests
import os
from flask import render_template, abort, make_response, request, Blueprint,  jsonify
from .utilities_db import get_all_projects, get_popular_repos_tr, get_popular_repos, get_first_launch_ts, get_launches_json
from . import app, cache
from flask_restplus import Api, Resource
from .models import BinderLaunch, User, Repo
from binder_gallery import db

# blueprint in order to change API url base otherwise it overwrites 127.0.0.1/gallery
# TODO where to put version of api ?? it always displays 1.0 in swagger
blueprint = Blueprint('api', __name__, url_prefix='/api/v1.0')
api = Api(blueprint)
app.register_blueprint(blueprint)


@cache.cached(timeout=300, key_prefix='binder_versions')
def get_binder_versions(binders):
    for binder in binders:
        # lasts ~0.3 seconds per binder
        try:
            response = requests.get(binder['url'] + '/versions', timeout=0.5)
            if response.status_code == 200:
                versions = response.json()
                versions = f"BinderHub {versions['binderhub']} with {versions['builder']}"
                binder['versions'] = versions
        except Exception as e:
            # if fail, last fetched version info (of this binder) is displayed
            app.logger.error(f"Error: fetching version of {binder['name']} failed: {e}")
    return binders


def get_binders(fetch_versions=True):
    binders = app.binders
    # first fetch versions, because it is cached and otherwise cached value overwrites the selected info
    if fetch_versions is True:
        binders = get_binder_versions(binders)
    # then set selected binder
    selected_binder = request.cookies.get('selected_binder') or app.default_binder_url
    for binder in binders:
        binder['selected'] = 'false'
        if binder['name'] == selected_binder or binder['url'] == selected_binder:
            binder['selected'] = 'true'
    return binders


def get_default_template_context():
    production = bool(os.getenv("PRODUCTION_SERVER", False))
    staging = not production
    context = {
        'staging': staging,
        'production': production,
        'version': 'beta',
        'home_url': '/',
        'jhub_url': '/jupyter/',
        'bhub_url': '/binder/',
        'about_url': '/about/',
        'tou_url': '/terms_of_use/',
        'imprint_url': 'https://www.gesis.org/en/institute/imprint/',
        'data_protection_url': 'https://www.gesis.org/en/institute/data-protection/',
        'gesis_url': 'https://www.gesis.org/en/home/',
        'gallery_url': app.base_url,
        # 'help_url': 'https://www.gesis.org/en/help/',
        'binder_url': app.default_binder_url,
    }
    return context


@app.route('/select_binder/', methods=['POST'])
def select_binder():
    selected_binder = request.json['name']
    resp = make_response(f"Selected Binder: {selected_binder}")

    if 'SELECT_BINDER_COOKIE_DOMAIN' in app.config:
        cookie_domain = app.config['SELECT_BINDER_COOKIE_DOMAIN']
    else:
        cookie_domain = app.config['SESSION_COOKIE_DOMAIN']
        cookie_domain = None if cookie_domain is False else cookie_domain
    resp.set_cookie("selected_binder", selected_binder,
                    path=app.base_url, httponly=True, samesite='Lax',
                    secure=app.config.get('SELECT_BINDER_COOKIE_SECURE', app.config['SESSION_COOKIE_SECURE']),
                    domain=cookie_domain)
    return resp


@app.route('/')
def gallery():
    time_range_list = [('24h', 'Last 24 hours'),
                       ('7d', 'Last week'),
                       ('30d', 'Last 30 days'),
                       ('60d', 'Last 60 days'),
                       ('all', 'All time')]
    launched_repos_all = []
    for time_rage, title in time_range_list:
        launched_repos = get_popular_repos_tr(time_rage)
        if launched_repos:
            total_launches = sum([l[-1] for l in launched_repos])
            launched_repos_all.append((time_rage, title, launched_repos, total_launches))

    context = get_default_template_context()
    context.update({'active': 'gallery',
                    'launched_repos_all': launched_repos_all,
                    'projects': get_all_projects(),
                    'binders': get_binders(),
                    'first_launch_ts': get_first_launch_ts(),
                    })
    return render_template('gallery.html', **context)


@app.route('/<string:time_range>/')
def view_all(time_range):
    titles = {'24h': 'Launches in last 24 hours',
              '7d': 'Launches in last week',
              '30d': 'Launches in last 30 days',
              '60d': 'Launches in last 60 days',
              'all': 'Launches in all time'}
    if time_range not in titles:
        abort(404)

    context = get_default_template_context()
    launched_repos = get_popular_repos_tr(time_range)
    total_launches = sum([l[-1] for l in launched_repos])
    context.update({'active': 'gallery',
                    'time_range': time_range,
                    'title': titles[time_range],
                    'binders': get_binders(),
                    'first_launch_ts': get_first_launch_ts(),
                    'total_launches': total_launches,
                    'launched_repos': launched_repos})
    return render_template('view_all.html', **context)


@app.errorhandler(404)
def not_found(error):
    context = get_default_template_context()
    context.update({'status_code': error.code,
                    'status_message': error.name,
                    'message': error.description,
                    'active': None})
    return render_template('error.html', **context), 404


@api.route('/launches/<string:from_datetime>/', methods=['GET'])
class RepoLaunches(Resource):

    # @api.marshal_with(Repos, envelope='resource')
    @api.doc(params={'from_datetime': 'DateTime format utc0 from when you want to see repo_launches'})
    def get(self, from_datetime):
        try:
            launches = get_launches_json(from_datetime)
        except ValueError as e:
            return {"status": "error", "message": str(e)}, 400
        except Exception as e:
            # TODO
            return {"status": "error", "message": str(e)}, 400
        return {"status": "success", "launches": launches}


@api.route('/launches/<string:from_datetime>/<string:to_datetime>', methods=['GET'])
class RepoLaunchesGet(Resource):

    # @api.marshal_with(Repos, envelope='resource')
    @api.doc(params={'from_datetime': 'DateTime format utc0 from when you want to see repo_launches',
                     'to_datetime': 'until what time'})
    def get(self, from_datetime, to_datetime):
        try:
            launches = get_launches_json(from_datetime, to_datetime)
        except ValueError as e:
            return {"status": "error", "message": str(e)}, 400
        except Exception as e:
            # TODO
            return {"status": "error", "message": str(e)}, 400
        return {"status": "success", "launches": launches}


@api.route('/launches', methods=['POST'])
class RepoLaunchesCreate(Resource):
    # @api.doc(parser=parser)
    # TODO add all responses: 400, 201
    @api.doc(responses={403: 'Not Authorized'})
    def post(self):
        token = request.headers.get('Authorization')
        if token:
            token = token.replace('Bearer ', '', 1)
            if User.validate_token(token) is True:

                # data = dict(request.form)
                data = request.form
                # json_data = request.get_json(force=True)
                if not data:
                    return {"status": "error", 'message': 'No input data provided'}, 400
                else:
                    # FIXME
                    fields = ["timestamp", "schema", "version", "provider", "spec", "status"]
                    for field in fields:
                        if field in data and data[field]:
                            print(field, data[field])
                            pass
                        else:
                            return {"status": "error", 'message': 'Data is incomplete.'}, 400
                #launch = BinderLaunch(**data)
                launch = BinderLaunch(schema=data['schema'],
                                      version=data['version'],
                                      timestamp=data['timestamp'],
                                      provider=data['provider'],
                                      spec=data['spec'],
                                      status=data['status'])

                provider_namespace = launch.provider_spec.rsplit('/', 1)[0]  # without ref
                repo = Repo.query.filter_by(provider_namespace=provider_namespace).first()
                app.logger.info(f"New binder launch {launch.provider_spec} on {launch.timestamp} - "
                                f"{launch.schema} {launch.version} {launch.status}")
                description = launch.get_repo_description()
                if repo:
                    repo.launches.append(launch)
                    repo.description = description
                else:
                    repo = Repo(provider_namespace=provider_namespace, description=description, launches=[launch])
                    db.session.add(repo)

                db.session.add(launch)
                db.session.commit()
            else:
                abort(make_response(jsonify(status="error", message="Authorization token is not valid."), 400))
        else:
            abort(make_response(jsonify(status="error", message="Authorization token is required."), 400))

        return {"status": 'success'}, 201


@api.route('/popular_repos/<string:time_range>', methods=['GET'])
# @api.doc(params={'from_date': 'DateTime format utc0 from when you want to see repo_launches'})
class PopularReposTr(Resource):
    # @api.marshal_with(Repos, envelope='resource')
    @api.doc(params={'time_range': 'TODO'})
    def get(self, time_range):
        try:
            # TODO should we output popular repos in different format with different data?
            # right now we output what is needed/specific for gallery
            popular_repos = get_popular_repos_tr(time_range)
        except ValueError as e:
            return {"status": "error", "message": str(e)}, 400
        return {"status": "success", "popular_repos": popular_repos}


@api.route('/popular_repos/<string:from_datetime>/', defaults={'to_datetime': None})
@api.route('/popular_repos/<string:from_datetime>/<string:to_datetime>', methods=['GET'])
# @api.doc(params={'from_date': 'DateTime format utc0 from when you want to see repo_launches'})
class PopularRepos(Resource):
    # @api.marshal_with(Repos, envelope='resource')
    @api.doc(params={'from_datetime': 'TODO', 'to_datetime': 'TODO'})
    def get(self, from_datetime, to_datetime):
        try:
            # TODO should we output popular repos in different format with different data?
            # right now we output what is needed/specific for gallery
            popular_repos = get_popular_repos(from_datetime, to_datetime)
        except ValueError as e:
            return {"status": "error", "message": str(e)}, 400
        return {"status": "success", "popular_repos": popular_repos}
