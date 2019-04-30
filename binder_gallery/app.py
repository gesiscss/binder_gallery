import requests
from flask import render_template, abort, make_response, request
from .utilities_db import get_all_projects, get_launched_repos
from . import app

BINDER_URL = app.config['BINDER_URL'].rstrip('/')


def get_binders(fetch_versions=True):
    binders = [
        {'name': 'GESIS', 'url': 'https://notebooks.gesis.org/binder', 'selected': 'false'},
        {'name': 'mybinder.org', 'url': 'https://mybinder.org', 'selected': 'false'},
        {'name': 'Pangeo', 'url': 'https://binder.pangeo.io', 'selected': 'false'},
    ]
    selected_binder = request.cookies.get('selected_binder') or BINDER_URL
    for binder in binders:
        if binder['name'] == selected_binder or binder['url'] == selected_binder:
            binder['selected'] = 'true'

    if fetch_versions is True:
        for binder in binders:
            versions = "No versions info is available"
            try:
                response = requests.get(binder['url'] + '/versions', timeout=0.5)
                if response.status_code == 200:
                    versions = response.json()
                    versions = f"BinderHub {versions['binderhub']} with {versions['builder']}"
            except Exception as e:
                app.logger.error(e)
            binder['versions'] = versions
    return binders


def get_default_template_context():
    staging = app.debug
    production = not app.debug
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
        'gallery_url': '/gallery/',  # TODO base url
        # 'help_url': 'https://www.gesis.org/en/help/',
        'binder_url': BINDER_URL,
    }
    return context


@app.route('/select_binder/', methods=['POST'])
def select_binder():
    selected_binder = request.json['name']
    resp = make_response(f"Selected Binder: {selected_binder}")
    resp.set_cookie("selected_binder", selected_binder)
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
                    'popular_repos': get_launched_repos(time_range)})
    return render_template('popular_repos.html', **context)


@app.errorhandler(404)
def not_found(error):
    context = get_default_template_context()
    context.update({'status_code': error.code,
                    'status_message': error.name,
                    'message': error.description,
                    'active': None})
    return render_template('error.html', **context), 404


def run_app():
    app.run(host='0.0.0.0')


main = run_app

if __name__ == '__main__':
    main()
