from .models import BinderLaunch
from datetime import datetime, timedelta
from sqlalchemy.orm import load_only


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


def get_popular_repos(time_range):
    """DOes sth

    :param time_range: (24h,7d,30d, all time) the interval to count launches
    :return: list {repo_id: [repo_name,org,provider,repo_url,binder_url,description,launches]}
    :rtype: list
    """
    if time_range.endswith('h'):
        p = {'hours': int(time_range.split('h')[0])}
    elif time_range.endswith('d'):
        p = {'days': int(time_range.split('d')[0])}
    else:
        raise ValueError('Time range must be in hours or days.')

    _to = datetime.utcnow()
    _from = _to - timedelta(**p)
    objects = BinderLaunch.query.\
        options(load_only('repo_id', 'provider', 'spec')).\
        filter(BinderLaunch.timestamp.between(_from, _to)).\
        all()

    popular_repos = {}  # {repo_id: [repo_name,org,provider,repo_url,binder_url,description,launches]}
    for o in objects:
        repo_id = o.repo_id
        if repo_id in popular_repos:
            popular_repos[repo_id][-1] += 1
        else:
            org, repo_name = o.spec_parts[:2]
            if org == '':
                # for Git provider
                repo_name = repo_name.replace('https://', '').rstrip('.git')
            launches = 1
            popular_repos[repo_id] = [repo_name, org, o.provider, o.repo_url,
                                      o.binder_url, o.repo_description, launches]

    popular_repos = list(popular_repos.values())
    popular_repos.sort(key=lambda x: x[-1], reverse=True)
    return popular_repos


