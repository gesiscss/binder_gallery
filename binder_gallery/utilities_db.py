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


"""
def get_popular_repos(time_range):
    #FixME binder_url
    popular_repos = []  # [ (repo,org,provider,launches,repo_url)
    if time_range.endswith('h'):
        p = {'hours': int(time_range.split('h')[0])}
    elif time_range.endswith('d'):
        p = {'days': int(time_range.split('d')[0])}
    else:
        raise ValueError('Time range must be in hours or days.')
    time_delta = timedelta(**p)
    end_time = datetime.utcnow() - time_delta
    objects = BinderLaunch.query.join(Repo, BinderLaunch.repo_id == Repo.id).\
        with_entities(Repo.provider_spec, Repo.description, db.func.count(BinderLaunch.repo_id)).\
        filter(BinderLaunch.timestamp.between(end_time, datetime.utcnow())).\
        group_by(Repo.provider_spec, Repo.description).all()

    for o in objects:
        repo_url = provider_spec_to_url(o[0])
        provider_org_repo = o[0].rsplit('/')
        provider, org, repo, ss = provider_org_repo
        if provider == 'gh':
            provider = 'GitHub'
        description = o[1]
        launches = o[2]
        repository = (repo, org, provider, launches, repo_url, description, 'binder_url')
        popular_repos.append(repository)
    popular_repos.sort(key=lambda x: x[3], reverse=True)

    return popular_repos
"""
