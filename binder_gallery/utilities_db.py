from datetime import datetime, timedelta
from sqlalchemy.orm import load_only
from sqlalchemy import func
from . import db, cache, app
from .models import BinderLaunch, CreatedByGesis, FeaturedProject


def get_projects(table):
    """Gets all active objects of given table in order according to position

    :param table: CreatedByGesis or FeaturedProject
    :return: list of data of active projects,
    an item in list: [repo_name, org, provider, repo_url, binder_url, description]
    :rtype: list
    """
    # query = table.query.\
    #     with_entities(table.repo_url, table.binder_url, table.description). \
    #     filter_by(active=True).\
    #     order_by(table.position)

    objects = table.query.\
        options(load_only('repo_url', 'binder_url', 'description')).\
        filter_by(active=True).\
        order_by(table.position).\
        all()

    projects = []
    for o in objects:
        projects.append([o.repo_name, o.org, o.provider, o.repo_url, o.binder_url, o.description])
    return projects


@cache.cached(timeout=None, key_prefix='all_projects')
def get_all_projects():
    all_projects = []
    for title, model_ in [('Created by GESIS', CreatedByGesis),
                          ('Featured Projects', FeaturedProject)]:
        projects = get_projects(model_)
        if projects:
            all_projects.append((title, projects))
    return all_projects


def get_popular_repos(binder, from_dt, to_dt=None):
    """Gets launched repos from BinderLaunch table in a given time range
    and aggregates them over launch count in order according to launch count.
    :param binder: origin binder name
    :param from_dt: beginning of time range
    :param to_dt: end of time range
    :return: list of popular repos, ordered by launch count,
    an item in list: [repo_name,org,provider,repo_url,binder_url,description,launch_count]
    :rtype: list
    """
    if binder == 'gesisbinder':
        query = BinderLaunch.query.\
                filter(BinderLaunch.origin.in_(('notebooks.gesis.org', ''))).\
                options(load_only('repo_id', 'provider', 'spec'))  # Those before without origin
    elif binder == 'mybinder':
        query = BinderLaunch.query.\
                filter(BinderLaunch.origin.in_(('gke.mybinder.org', 'ovh.mybinder.org', "binder.mybinder.ovh", 'mybinder.org'))).\
                options(load_only('repo_id', 'provider', 'spec'))
    else:
        query = BinderLaunch.query.options(load_only('repo_id', 'provider', 'spec'))

    if from_dt is None and to_dt is None:
        # all time
        objects = query.all()
    else:
        from_dt = datetime.fromisoformat(from_dt)
        if to_dt is None:
            # until now
            to_dt = datetime.utcnow()
        else:
            to_dt = datetime.fromisoformat(to_dt)
        # get launch counts in given time range
        objects = query.filter(BinderLaunch.timestamp.between(from_dt, to_dt)).all()

    # aggregate over launch count
    repos = {}  # {repo_id: [repo_name,org,provider,repo_url,binder_url,description,launch_count]}
    for o in objects:
        repo_id = o.repo_id
        if repo_id in repos:
            repos[repo_id][-1] += 1
        else:
            org, repo_name = o.spec_parts[:2]
            launch_count = 1
            repos[repo_id] = [repo_name, org, o.provider, o.repo_url, o.binder_url, o.repo_description, launch_count]

    # order according to launch count
    repos = list(repos.values())
    repos.sort(key=lambda x: x[-1], reverse=True)

    return repos


def get_popular_repos_tr(binder, time_range):
    """Gets popular repos in given time range.

    :param binder: origin binder name
    :param time_range: the interval to get popular repos
    """
    if time_range == "all":
        to_dt = None
        from_dt = None
    else:
        if time_range.endswith('h'):
            p = {'hours': int(time_range.split('h')[0])}
        elif time_range.endswith('d'):
            p = {'days': int(time_range.split('d')[0])}
        elif time_range.endswith('m'):
            p = {'minutes': int(time_range.split('m')[0])}
        else:
            raise ValueError('Time range must be in minutes [m] or hours [h] or days [d].')

        to_dt = datetime.utcnow()
        from_dt = to_dt - timedelta(**p)
        to_dt = to_dt.isoformat()
        from_dt = from_dt.isoformat()

    return get_popular_repos(binder, from_dt, to_dt)


def get_launches_query(from_dt, to_dt=None):
    if to_dt is None:
        to_dt = datetime.utcnow()

    query = BinderLaunch.query. \
        filter(BinderLaunch.timestamp.between(from_dt, to_dt)). \
        order_by(BinderLaunch.timestamp)

    return query


def get_launches_paginated(from_dt, to_dt=None):
    """Get launches from BinderLaunch table in given time range ordered by timestamp.
    Returns a Pagination object: https://flask-sqlalchemy.palletsprojects.com/en/2.x/api/#flask_sqlalchemy.Pagination
    """
    query = get_launches_query(from_dt, to_dt)
    # https://flask-sqlalchemy.palletsprojects.com/en/2.x/api/#flask_sqlalchemy.BaseQuery
    # If page or per_page are None, they will be retrieved from the request query.
    # ex: ?page=5
    launches = query.paginate(per_page=app.config.get("PER_PAGE", 100))

    return launches


def get_launches(from_dt, to_dt=None):
    """Get launches from BinderLaunch table in given time range ordered by timestamp."""

    query = get_launches_query(from_dt, to_dt)
    launches = query.all()

    return launches


def get_launch_count():
    return db.session.execute(
        db.session.query(
            func.count(BinderLaunch.id)
        )
    ).scalar()


@cache.cached(timeout=None, key_prefix='first_launch_ts')
def get_first_launch_ts():
    first_launch = BinderLaunch.query.with_entities(BinderLaunch.timestamp).order_by(BinderLaunch.timestamp).first()
    return first_launch[0] if first_launch else None


def get_launch_data():
    return {
        "count": get_launch_count(),
        "first_ts": get_first_launch_ts()
    }
