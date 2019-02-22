from .utilities import repo_url_parts


# for CreatedByGesis and FeaturePost
def get_project_mixin(table):
    results = []

    # created_by_gesis = db.session.query(CreatedByGesis).filter_by(active=True).all()
    objects = table.query.filter_by(active=True).order_by(table.position).all()

    for o in objects:
        # repo_name, repo_url, org, provider, binder_url, description
        repo_url = o.repo_url
        binder_url = o.binder_url
        description = o.description
        provider, org, repo = repo_url_parts(repo_url)
        results.append([repo, repo_url, provider, org, binder_url, description])

    return results

