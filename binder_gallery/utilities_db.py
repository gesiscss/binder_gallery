from .utilities import repo_url_parts
from .models import CreatedByGesis


def get_created_by_gesis():
    created_by_gesis = []
    # created_by_gesis = db.session.query(CreatedByGesis).filter_by(active=True).all()
    objects = CreatedByGesis.query.filter_by(active=True).order_by(CreatedByGesis.position).all()
    for o in objects:
        # repo_name, repo_url, org, provider, binder_url, description
        repo_url = o.repo_url
        binder_url = o.binder_url
        description = o.description
        provider, org, repo = repo_url_parts(repo_url)
        created_by_gesis.append([repo, repo_url, provider, org, binder_url, description])
    return created_by_gesis
