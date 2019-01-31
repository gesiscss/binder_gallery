import requests
from bs4 import BeautifulSoup

from .models import CreatedByGesis


def repo_url_parts(repo_url):
    return repo_url.replace('https://', '').rstrip('.git').rsplit('/', 2)


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


def get_repo_description(repo_link):
    page = requests.get(repo_link)
    soup = BeautifulSoup(page.content, 'html.parser')
    about = soup.find('span', itemprop='about')
    url = soup.find('span', itemprop='url')
    if about or url:
        text = about.text.strip() if about else ''
        url = ' ' + url.find('a').text.strip() if url else ''
        return text, url
    return '', ''
