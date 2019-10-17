import click
from . import app
from .models import User
from .mybinder_archives import parse_mybinder_archives as _parse_mybinder_archives


# http://flask.pocoo.org/docs/1.0/cli/#custom-commands
# http://click.palletsprojects.com/en/7.x/arguments/
@app.cli.command()
@click.argument('name')
@click.argument('password')
@click.argument('email', required=False)
@click.argument('active', required=False)
def create_user(name, password, email="", active=True):
    u = User.create_user(name, password, email, active)
    print(f"User {u.name} is created!")


# flask parse-mybinder-archives --all-events mybinder
@app.cli.command()
@click.argument('binder', required=False, default='mybinder')
@click.option('--all-events', '-a', is_flag=True, help="Parse all events.")
@click.option('--with-description', '-d', is_flag=True, help="Fetch description of repos.")
@click.option('--excluded-origins', '-e', help="List of origins to exclude (comma-separated).")
def parse_mybinder_archives(binder='mybinder', all_events=False, with_description=False, excluded_origins=None):
    if excluded_origins is not None:
        excluded_origins = excluded_origins.split(',')
    _parse_mybinder_archives(binder, all_events, with_description, excluded_origins)
