from datetime import datetime
from flask import abort, make_response, request, Blueprint, jsonify, url_for
from flask_restplus import Api, Resource, fields, marshal, Namespace, reqparse, inputs
from .utilities_db import get_launches_paginated
from . import app, db
from .models import BinderLaunch, User, Repo
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(app, key_func=get_remote_address)


class GalleryApi(Api):
    @property
    def specs_url(self):
        """Fix for https"""
        return url_for(self.endpoint('specs'), _external=False)
        # scheme = 'http' if '5000' in self.base_url else 'https'
        # return url_for(self.endpoint('specs'), _external=True, _scheme=scheme)


# blueprint in order to change API url base otherwise it overwrites 127.0.0.1/gallery
version = '1.0'
blueprint = Blueprint('api', __name__, url_prefix='/api/v'+version)
app.config.SWAGGER_UI_DOC_EXPANSION = 'list'
authorizations = {
    'apikey': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization'
    }
}
api = GalleryApi(blueprint, version=version,
                 authorizations=authorizations,
                 title='Gallery API',
                 description='API for launch events on <a href="/binder">GESIS binder</a>',
                 )

launch_ns = Namespace('launches', description='Launch events related operations')
api.add_namespace(launch_ns, path='/launches')

app.register_blueprint(blueprint)

# https://flask-restplus.readthedocs.io/en/stable/marshalling.html
launch_model = api.model('Launch', {
    'timestamp': fields.DateTime(description="in UTC, timezone information is ignored"),
    'schema': fields.String(example='binderhub.jupyter.org/launch'),
    'version': fields.Integer(example=2),
    'provider': fields.String(example='GitHub'),
    'spec': fields.String(example='user/repo/branch'),
    'status': fields.String(example='success'),
    # TODO return optionally these values according to query params (?repourl=True&binderurl=True...)
    # 'repo_url': fields.String(),
    # 'binder_url': fields.String(),
    # 'repo_description': fields.String(),
})

# swagger documentation
dt_description = "Date and time in ISO 8601 format in UTC, e.g. 2019-05-31T16:17:56.946703"
page_description = "Default is 1 (first page) and each page contains max 100 items"


@launch_ns.route('/<string:from_datetime>/<string:to_datetime>', methods=['GET'])
class RepoLaunchesBase(Resource):
    # With class based approach to defining view function, the regular method of decorating a view function to apply a
    # per route rate limit will not work.So had to use this way.
    decorators = [limiter.limit("100/minute")]
    decorators = [limiter.limit("2/second")]

    @launch_ns.doc(params={'from_datetime': dt_description,
                           'to_datetime': dt_description},
                   responses={200: 'Success', 400: 'DateTime Value Error'})
    @launch_ns.param('page', page_description)
    def get(self, from_datetime, to_datetime=None):
        try:
            if from_datetime.endswith("Z"):
                from_datetime = from_datetime.rsplit('Z', 1)[0]
            from_datetime = datetime.fromisoformat(from_datetime)
            if to_datetime is not None:
                if to_datetime.endswith("Z"):
                    to_datetime = to_datetime.rsplit('Z', 1)[0]
                to_datetime = datetime.fromisoformat(to_datetime)
        except ValueError as e:
            return {"status": "error", "message": str(e)}, 400
        launches = get_launches_paginated(from_datetime, to_datetime)
        next_page = launches.next_num
        launches = launches.items
        return {"status": "success", "next_page": next_page,
                "launches": marshal(launches, launch_model)}, 200


# request parser for post requests
launch_parser = reqparse.RequestParser()
launch_parser.add_argument('timestamp', type=inputs.datetime_from_iso8601, required=True)
launch_parser.add_argument('schema', type=str, required=True)
launch_parser.add_argument('version', type=int, required=True)
launch_parser.add_argument('provider', type=str, required=True)
launch_parser.add_argument('spec', type=str, required=True)
launch_parser.add_argument('status', type=str, required=True)


@launch_ns.route('/<string:from_datetime>/', methods=['GET'])
@launch_ns.route('', methods=['POST'])
class RepoLaunches(RepoLaunchesBase):

    @launch_ns.doc(params={'from_datetime': {'description': dt_description}},
                   responses={200: 'Success', 400: 'DateTime Value Error'})
    @launch_ns.param('page', page_description)
    def get(self, from_datetime):
        return super().get(from_datetime)

    @launch_ns.doc(security='apikey',
                   body=launch_model,
                   responses={403: 'Not Authorized', 400: 'Launch Data Error', 201: 'Success'})
    def post(self):
        # require Bearer token authentication for creating new launch entry
        token = request.headers.get('Authorization')
        if token:
            token = token.replace('Bearer ', '', 1)
            if User.validate_token(token) is True:
                data = launch_parser.parse_args()
                # remove timezone information, we assume it is UTC
                # otherwise it is converted into local timezone and saved into database
                timestamp = data['timestamp'].replace(tzinfo=None)
                launch = BinderLaunch(schema=data['schema'],
                                      version=data['version'],
                                      timestamp=timestamp,
                                      provider=data['provider'],
                                      spec=data['spec'],
                                      status=data['status'])

                provider_spec = launch.provider_spec
                app.logger.info(f"New binder launch {provider_spec} on {launch.timestamp} - "
                                f"{launch.schema} {launch.version} {launch.status}")

                # NOTE: branch name can contain "/"
                provider_namespace = "/".join(provider_spec.split('/', 3)[:3])  # without ref
                repo = Repo.query.filter_by(provider_namespace=provider_namespace).first()
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
                abort(make_response(jsonify(status="error", message="Authorization token is not valid."), 403))
        else:
            abort(make_response(jsonify(status="error", message="Authorization token is required."), 403))

        return {"status": 'success'}, 201
