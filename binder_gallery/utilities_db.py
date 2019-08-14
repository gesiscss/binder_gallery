from datetime import datetime, timedelta
from sqlalchemy.orm import load_only
from sqlalchemy import desc, func
from . import cache, app
from .models import BinderLaunch, CreatedByGesis, FeaturedProject, Repo
from slugify import slugify


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
    for title, url_title, model_ in [('Created by GESIS', slugify('Created by GESIS'), CreatedByGesis),
                          ('Featured Projects', slugify('Featured Projects'), FeaturedProject)]:
        projects = get_projects(model_)
        if projects:
            all_projects.append((title, url_title, projects))
    return all_projects


def _get_popular_repos(binder, from_dt, to_dt=None):
    """Gets launched repos from BinderLaunch table in a given time range
    and aggregates them over launch count in order according to launch count.
    :param binder: origin binder name
    :param from_dt: beginning of time range
    :param to_dt: end of time range
    :return: list of popular repos, ordered by launch count,
    an item in list: [repo_name,org,provider,repo_url,binder_url,description,launch_count]
    :rtype: list
    """
    subquery = BinderLaunch.query.\
               with_entities(BinderLaunch.repo_id,
                             func.count(BinderLaunch.id).label('launch_count'),
                             # func.array_agg(BinderLaunch.spec.distinct()).label('specs')
                             ).\
               group_by(BinderLaunch.repo_id)
               # order_by(desc("launch_count"))

    if binder != "all":
        subquery = subquery.filter(BinderLaunch.origin.in_(app.binder_origins[binder]['origins']))

    if from_dt is not None or to_dt is not None:
        from_dt = datetime.fromisoformat(from_dt)
        if to_dt is None:
            # until now
            to_dt = datetime.utcnow()
        else:
            to_dt = datetime.fromisoformat(to_dt)
        # to get launch counts in given time range
        subquery = subquery.filter(BinderLaunch.timestamp.between(from_dt, to_dt))
    # subquery = subquery.limit(5).subquery()
    subquery = subquery.subquery()
    repos = Repo.query.filter(Repo.id == subquery.c.repo_id).add_columns(subquery.c.launch_count,
                                                                         # subquery.c.specs
                                                                         ).all()

    data = []
    for repo, launch_count in repos:
        org, repo_name = repo.repo_namespace
        data.append([repo_name, org, repo.provider, repo.repo_url, repo.binder_url, repo.description, launch_count])
        # data.append([repo_name, org, repo.provider, repo.repo_url, repo.get_binder_url(specs[-1]), repo.description, launch_count])
    data.sort(key=lambda x: x[-1], reverse=True)
    return data


def get_popular_repos(binder, time_range):
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

    return _get_popular_repos(binder, from_dt, to_dt)


def get_launches_query(from_dt, to_dt=None):
    if to_dt is None:
        to_dt = datetime.utcnow()

    query = BinderLaunch.query. \
        filter(BinderLaunch.timestamp.between(from_dt, to_dt)). \
        order_by(BinderLaunch.timestamp, BinderLaunch.id)

    return query


def get_launches_paginated(from_dt, to_dt=None):
    """Get launches from BinderLaunch table in given time range ordered by timestamp.
    Returns a Pagination object: https://flask-sqlalchemy.palletsprojects.com/en/2.x/api/#flask_sqlalchemy.Pagination
    """
    query = get_launches_query(from_dt, to_dt)
    # https://flask-sqlalchemy.palletsprojects.com/en/2.x/api/#flask_sqlalchemy.BaseQuery
    # If page or per_page are None, they will be retrieved from the request query.
    # ex: ?page=5
    # NOTE: it is very important to have both id and timestamp in order_by, if we had only timestamp,
    # it is possible to get some data double
    launches = query.paginate(per_page=app.config.get("PER_PAGE", 100))

    return launches


def get_launches(from_dt, to_dt=None):
    """Get launches from BinderLaunch table in given time range ordered by timestamp."""
    query = get_launches_query(from_dt, to_dt)
    launches = query.all()

    return launches


# def get_launch_count():
#     return db.session.execute(
#         db.session.query(
#             func.count(BinderLaunch.id)
#         )
#     ).scalar()


@cache.memoize(timeout=None)
def get_first_launch_ts(binder):
    query = BinderLaunch.query.\
            with_entities(BinderLaunch.timestamp).\
            order_by(BinderLaunch.timestamp)
    if binder != "all":
        query = query.filter(BinderLaunch.origin.in_(app.binder_origins[binder]['origins']))
    first_launch = query.first()
    return first_launch[0] if first_launch else None
