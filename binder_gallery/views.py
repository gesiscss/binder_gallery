import requests
import os
from flask_restful import Resource, Api
from flask import render_template, abort, make_response, request
from .utilities_db import get_all_projects, get_launched_repos, get_first_launch_ts, get_launches
from . import app, cache


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
        launched_repos = get_launched_repos(time_rage)
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
    launched_repos = get_launched_repos(time_range)
    total_launches = sum([l[-1] for l in launched_repos])
    context.update({'active': 'gallery',
                    'time_range': time_range,
                    'title': titles[time_range],
                    'binders': get_binders(),
                    'first_launch_ts': get_first_launch_ts(),
                    'total_launches': total_launches,
                    'launched_repos': launched_repos})
    return render_template('view_all.html', **context)


class PopularRepos(Resource):
    def get(self, time_range):
        try:
            repos = get_launched_repos(time_range)
        except ValueError as e:
            return {"error": str(e)}, 400
        return repos


class RepoLaunches(Resource):
    def get(self, from_datetime, to_datetime):
        try:
            repos = get_launches(from_datetime, to_datetime)
        except ValueError as e:
            return {"error": str(e)}, 400
        return repos


@app.errorhandler(404)
def not_found(error):
    context = get_default_template_context()
    context.update({'status_code': error.code,
                    'status_message': error.name,
                    'message': error.description,
                    'active': None})
    return render_template('error.html', **context), 404


api = Api(app)
api.add_resource(PopularRepos, '/api/v1.0/popular_repos/<string:time_range>')

api.add_resource(RepoLaunches, '/api/v1.0/launches/<string:from_datetime>/<string:to_datetime>')
