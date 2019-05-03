import click
from . import app
from .models import User


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
