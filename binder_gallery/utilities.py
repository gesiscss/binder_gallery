import csv
import os
import requests
from bs4 import BeautifulSoup


def get_created_by_gesis():
    csv_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'created_by_gesis.csv')
    with open(csv_file, 'r') as f:
        reader = csv.reader(f)
        created_by_gesis = list(reader)
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
