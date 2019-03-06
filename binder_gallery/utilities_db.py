from .utilities import repo_url_parts
from .models import Repo, BinderLaunch, db
from datetime import datetime, timedelta
from .utilities import provider_spec_to_url


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
        with_entities(Repo.provider_spec, db.func.count(BinderLaunch.repo_id)).\
        filter(BinderLaunch.timestamp.between(end_time, datetime.utcnow())).\
        filter(BinderLaunch.repo_id == BinderLaunch.repo_id).group_by(Repo.provider_spec).all()

    for o in objects:
        repo_url = provider_spec_to_url(o[0])
        provider_org_repo = o[0].rsplit('/')
        provider, org, repo, ss = provider_org_repo
        if provider == 'gh':
            provider = 'GitHub'
        launches = o[1]
        repository = (repo, org, provider, launches, repo_url)
        popular_repos.append(repository)
    popular_repos.sort(key=lambda x: x[3], reverse=True)

    return popular_repos



