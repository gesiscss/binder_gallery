from requests import get
from requests.exceptions import Timeout
from bs4 import BeautifulSoup


def repo_url_parts(repo_url):
    return repo_url.replace('https://', '').rstrip('.git').rsplit('/', 2)


def provider_spec_to_url(provider_spec):
    if provider_spec.startswith('gh/'):
        # for now only for GitHub repos
        provider_prefix, org, repo_name, ref = provider_spec.split('/', 3)
        return f'https://www.github.com/{org}/{repo_name}/tree/{ref}'
    return ''


def get_repo_description(repo_url):
    if 'github.com' not in repo_url:
        # only for GitHub repos
        return ''
    try:
        page = get(repo_url, timeout=1)
    except Timeout as e:
        return ''
    soup = BeautifulSoup(page.content, 'html.parser')
    about = soup.find('span', itemprop='about')
    url = soup.find('span', itemprop='url')
    if about or url:
        text = about.text.strip() if about else ''
        # url = ' ' + url.find('a').text.strip() if url else ''
        url = str(url.find('a')) if url else ''
        return f'{text} {url}'.strip()
    return ''
