from .utilities import repo_url_parts
from .models import Repo, BinderLaunch, db
from datetime import datetime, timedelta
from .utilities import provider_spec_to_url
from sqlalchemy.orm import load_only, Load


def get_projects(table):
    # for CreatedByGesis and FeaturedProject

    query = table.query.\
        with_entities(table.repo_url, table.binder_url, table.description). \
        filter_by(active=True).\
        order_by(table.position)

    results = []
    for r in query.all():
        provider, org, repo = repo_url_parts(r[0])
        # repo_name, repo_url, org, provider, binder_url, description
        results.append([repo, r[0], provider, org, r[1], r[2]])

    return results


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


def get_popular_repos_2(time_range):
    #FixME binder_url
    if time_range.endswith('h'):
        p = {'hours': int(time_range.split('h')[0])}
    elif time_range.endswith('d'):
        p = {'days': int(time_range.split('d')[0])}
    else:
        raise ValueError('Time range must be in hours or days.')

    time_delta = timedelta(**p)
    end_time = datetime.utcnow() - time_delta
    objects = BinderLaunch.query.options(load_only('repo_id', 'provider', 'spec')).\
        filter(BinderLaunch.timestamp.between(end_time, datetime.utcnow())).\
        all()

    popular_repos = {}  # {repo_id: [repo,org,provider,launches,repo_url]}
    for o in objects:
        repo_id = o.repo_id
        if repo_id in popular_repos:
            popular_repos[repo_id][3] += 1
        else:
            launches = 1
            popular_repos[repo_id] = ['test repo name', 'test org', o.provider, launches,
                                      o.repo_url, o.repo_description, '']

    popular_repos = list(popular_repos.values())
    popular_repos.sort(key=lambda x: x[3], reverse=True)
    return popular_repos
