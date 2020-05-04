from datetime import datetime
from flask import abort, make_response, request, Blueprint, jsonify, url_for
from flask_restplus import Api, Resource, marshal, Namespace, reqparse, inputs
from flask_restplus.fields import String, Integer, DateTime
from .utilities_db import get_launches_paginated
from . import app, db
from .models import BinderLaunch, User, Repo
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import func

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
                 description=app.config.get("API_DESCRIPTION", "API for launch events"),
                 )

launch_ns = Namespace('launches', description='Launch events related operations')
api.add_namespace(launch_ns, path='/launches')

app.register_blueprint(blueprint)


# https://flask-restplus.readthedocs.io/en/stable/marshalling.html
launch_model = api.model('Launch', {
    'timestamp': DateTime(description="in UTC, timezone information is ignored"),
    'schema': String(example='binderhub.jupyter.org/launch'),
    'version': Integer(example=3),
    'origin': String(example='notebooks.gesis.org'),
    'provider': String(example='GitHub'),
    'spec': String(example='user/repo/branch'),
    'status': String(example='success'),
    # TODO return optionally these values according to query params (?repourl=True&binderurl=True...)
    # 'repo_url': String(example='https://github.com/user/repo'),
    # 'binder_url': String(),
    # 'repo_description': String(),
})

# swagger documentation
dt_description = "Date and time in ISO 8601 format in UTC, e.g. 2019-05-31T16:17:56.946703"
page_description = "Default is 1 (first page) and each page contains max 100 items"
origin_description = "Default is all origins"


@launch_ns.route('/<string:from_datetime>/<string:to_datetime>', methods=['GET'])
class RepoLaunchesBase(Resource):
    # With class based approach to defining view function, the regular method of decorating a view function to apply a
    # per route rate limit will not work.So had to use this way.
    # limit only get methods
    decorators = [limiter.limit("100/minute;2/second", methods=['GET'])]

    @launch_ns.doc(params={'from_datetime': dt_description,
                           'to_datetime': dt_description},
                   responses={200: 'Success', 400: 'DateTime Value Error', 429: 'Too Many Requests' })
    @launch_ns.param('origin', origin_description)
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
        origin = request.args.get("origin")
        if origin == " ":
            # origin "" is for launches of GESIS Binder before version 3 (without origin)
            origin = ""
        launches = get_launches_paginated(from_datetime, to_datetime, origin)
        next_page = launches.next_num
        launches = launches.items
        return {"status": "success", "next_page": next_page,
                "launches": marshal(launches, launch_model, skip_none=True)}, 200


# request parser for post requests
launch_parser = reqparse.RequestParser()
launch_parser.add_argument('timestamp', type=inputs.datetime_from_iso8601, required=True)
launch_parser.add_argument('schema', type=str, required=True)
launch_parser.add_argument('version', type=int, required=True)
launch_parser.add_argument('origin', type=str, required=True)
launch_parser.add_argument('provider', type=str, required=True)
launch_parser.add_argument('spec', type=str, required=True)
launch_parser.add_argument('status', type=str, required=True)


@launch_ns.route('/<string:from_datetime>/', methods=['GET'])
@launch_ns.route('', methods=['POST'])
class RepoLaunches(RepoLaunchesBase):

    @launch_ns.doc(params={'from_datetime': {'description': dt_description}},
                   responses={200: 'Success', 400: 'DateTime Value Error', 429: 'Too Many Requests'})
    @launch_ns.param('origin', origin_description)
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
                # Trim timestamp to minute resolution before saving
                # Should hopefully make it harder to de-anonymize users by observing timing
                # ref: https://github.com/jupyterhub/mybinder.org-deploy/blob/master/images/analytics-publisher/archiver.py
                timestamp = timestamp.replace(second=0, microsecond=0)
                launch = BinderLaunch(schema=data['schema'],
                                      version=data['version'],
                                      timestamp=timestamp,
                                      origin=data['origin'],
                                      provider=data['provider'],
                                      spec=data['spec'],
                                      status=data['status'])

                provider_spec = launch.provider_spec
                app.logger.info(f"New binder launch {provider_spec} at {launch.timestamp} on {launch.origin} - "
                                f"{launch.schema} {launch.version} {launch.status}")

                provider_namespace = launch.provider_namespace
                repo = Repo.query.filter_by(provider_namespace=provider_namespace).first()
                description = launch.get_repo_description()
                if launch.provider_prefix in ["zenodo", "figshare", "hydroshare", "dataverse"]:
                    last_ref = ""
                else:
                    last_ref = launch.spec.split('/')[-1]
                if repo:
                    repo.launches.append(launch)
                    repo.description = description
                    repo.last_ref = last_ref
                else:
                    repo = Repo(provider_namespace=provider_namespace, description=description,
                                launches=[launch], last_ref=last_ref)
                    db.session.add(repo)
                db.session.add(launch)
                db.session.commit()
            else:
                abort(make_response(jsonify(status="error", message="Authorization token is not valid."), 403))
        else:
            abort(make_response(jsonify(status="error", message="Authorization token is required."), 403))

        return {"status": 'success'}, 201


@launch_ns.route('/origins/', methods=['GET'])
class Origins(Resource):
    # With class based approach to defining view function, the regular method of decorating a view function to apply a
    # per route rate limit will not work.So had to use this way.
    # limit only get methods
    decorators = [limiter.limit("100/minute;2/second", methods=['GET'])]

    @launch_ns.doc(responses={200: 'Success', 429: 'Too Many Requests' })
    @launch_ns.param('count', "Default is False. Count of launches per origin")
    def get(self):
        origins = []
        count = request.args.get("count")
        if count and count in ['True', 'true', '1']:
            _origins = BinderLaunch.query.with_entities(BinderLaunch.origin, func.count(BinderLaunch.origin)).group_by(BinderLaunch.origin).all()
            for origin, count in _origins:
                origins.append({'origin': origin, 'count': count})
        else:
            _origins = BinderLaunch.query.with_entities(BinderLaunch.origin).distinct().all()
            for origin in _origins:
                origins.append({'origin': origin[0]})
        return {"status": "success", "origins": origins}, 200
