import requests
import os
from flask_restful import Resource, Api
from flask import render_template, abort, make_response, request
from .utilities_db import get_all_projects, get_launched_repos, get_launch_data
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
    _popular_repos_all = [
        ('24h', 'Last 24 hours', get_launched_repos('24h'), ),
        ('7d', 'Last week', get_launched_repos('7d'), ),
        ('30d', 'Last 30 days', get_launched_repos('30d'), ),
        ('60d', 'Last 60 days', get_launched_repos('60d'), ),
    ]
    popular_repos_all = []
    # don't show empty tabs (no launched happened)
    for pr in _popular_repos_all:
        if pr[-1]:
            popular_repos_all.append(pr)
    del _popular_repos_all

    context = get_default_template_context()
    context.update({'active': 'gallery',
                    'popular_repos_all': popular_repos_all,
                    'projects': get_all_projects(),
                    'binders': get_binders(),
                    'launch_data': get_launch_data(),
                    })
    return render_template('gallery.html', **context)


@app.route('/<string:time_range>/')
def popular_repos(time_range):
    titles = {'24h': 'Popular repositories in last 24 hours',
              '7d': 'Popular repositories in last week',
              '30d': 'Popular repositories in last 30 days',
              '60d': 'Popular repositories in last 60 days'}
    if time_range not in titles:
        abort(404)

    context = get_default_template_context()
    context.update({'active': 'gallery',
                    'title': titles[time_range],
                    'binders': get_binders(),
                    'launch_data': get_launch_data(),
                    'popular_repos': get_launched_repos(time_range)})
    return render_template('popular_repos.html', **context)


class ReposLaunches(Resource):
    def get(self, time_range):
        try:
            repos = get_launched_repos(time_range)
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
api.add_resource(ReposLaunches, '/api/v1.0/repos/<string:time_range>')
