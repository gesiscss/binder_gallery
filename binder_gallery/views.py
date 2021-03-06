import requests
from flask import render_template, abort, make_response, request
from .utilities_db import get_all_projects, get_popular_repos, get_first_launch_ts
from . import app, cache


@cache.cached(timeout=300, key_prefix='binder_versions')
def get_binder_versions(binders):
    main_versions = None
    for binder in binders:
        # lasts ~0.3 seconds per binder
        try:
            response = requests.get(binder['url'] + '/versions', timeout=0.5)
            if response.status_code == 200:
                versions = response.json()
                versions = f"BinderHub {versions['binderhub']} with {versions['builder']}"
                binder['versions'] = versions
                if binder.get('main', 'false') == 'true':
                    # get versions of main binder. other binders will be checked against this to decide if up-to-date
                    main_versions = versions
        except Exception as e:
            # if fail, last fetched version info (of this binder) is displayed
            app.logger.error(f"Error: fetching version of {binder['name']} failed: {e}")
    # check if up-to-date
    for binder in binders:
        binder['versions'] = binder['versions'].rstrip('.')
        if main_versions is not None and binder.get('main', 'false') != 'true' and binder['versions'] == main_versions:
            binder['versions'] = binder['versions'] + '.'
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
    context = {
        'version': 'beta',
        'home_url': '/',
        'gesishub_url': '/hub/',
        'gesisbinder_url': '/binder/',
        'about_url': '/about/',
        'tou_url': '/terms_of_use/',
        'imprint_url': 'https://www.gesis.org/en/institute/imprint/',
        'data_protection_url': 'https://www.gesis.org/en/institute/data-protection/',
        'gesis_url': 'https://www.gesis.org/en/home/',
        'gallery_url': app.base_url,
        'faq_url': '/faq/',
        # 'help_url': 'https://www.gesis.org/en/help/',
        'binder_url': app.default_binder_url,
    }
    context.update(app.config.get('TEMPLATE_VARS', {}))
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
    popular_repos_all_binders = {}
    for b_name, b_data in app.binder_origins.items():
        popular_repos_all = []
        if not b_data["show"]:
            continue
        for time_range, i_data in b_data["intervals"].items():
            if not i_data["show"]:
                continue
            if i_data.get("load_dynamic", False):
                popular_repos_all.append((time_range, i_data["title"], [], 0, True))
            else:
                popular_repos = get_popular_repos(b_name, time_range)
                if popular_repos:
                    total_launches = sum([l[-1] for l in popular_repos])
                    popular_repos_all.append((time_range, i_data["title"], popular_repos, total_launches, False))
        if popular_repos_all:
            popular_repos_all_binders[b_name] = [b_data['title'],
                                                 popular_repos_all,
                                                 get_first_launch_ts(b_name)]

    context = get_default_template_context()
    context.update({'active': 'gallery',
                    'popular_repos_all_binders': popular_repos_all_binders,
                    'projects': get_all_projects(),
                    'binders': get_binders(),
                    })
    return render_template('gallery.html', **context)


@app.route('/<string:binder>/<string:time_range>/')
def view_all(binder, time_range):
    if (binder not in app.binder_origins and binder != 'all') \
       or time_range not in app.detail_pages\
       or not app.detail_pages[time_range]['show']:
        abort(404)
    if binder == 'all':
        title = app.detail_pages[time_range]['title']
    else:
        title = app.binder_origins[binder]["intervals"][time_range].get("detail_title",
                                                                        app.detail_pages[time_range]['title'])

    context = get_default_template_context()
    popular_repos = get_popular_repos(binder, time_range)
    total_launches = sum([l[-1] for l in popular_repos])
    context.update({'active': 'gallery',
                    'time_range': time_range,
                    'title': title,
                    'binders': get_binders(),
                    'first_launch_ts': get_first_launch_ts(binder),
                    'total_launches': total_launches,
                    'popular_repos': popular_repos})
    return render_template('view_all.html', **context)


@app.route('/table/<string:binder>/<string:time_range>/')
def table(binder, time_range):
    if binder not in app.binder_origins \
       or time_range not in app.binder_origins[binder]["intervals"] \
       or not app.binder_origins[binder]["intervals"][time_range]['show']:
        abort(404)

    popular_repos = get_popular_repos(binder, time_range)
    total_launches = sum([l[-1] for l in popular_repos])

    context = get_default_template_context()
    context.update({'active': 'gallery',
                    'binder': binder,
                    'time_range': time_range,
                    'table_id': '-'.join([binder, time_range]),
                    'title': app.binder_origins[binder]["intervals"][time_range]["title"],
                    'launch': True,
                    'first_launch_ts': get_first_launch_ts(binder),
                    'total_launches': total_launches,
                    'repos': popular_repos[:5],
                    'repos_length': len(popular_repos),
                    })
    return render_template('table.html', **context)


@app.errorhandler(404)
def not_found(error):
    context = get_default_template_context()
    context.update({'status_code': error.code,
                    'status_message': error.name,
                    'message': error.description,
                    'active': None})
    return render_template('error.html', **context), 404
