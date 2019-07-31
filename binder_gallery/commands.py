import click
from . import app
from .models import User
from .mybinder_launches import parse_mybinder_archives as _parse_mybinder_archives


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


@app.cli.command()
@click.argument('binder', required=False)
@click.option('--all-events', '-a', is_flag=True, help="Parse all events.")
def parse_mybinder_archives(binder='mybinder', all_events=False):
    _parse_mybinder_archives(binder, all_events)
