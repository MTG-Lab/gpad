import click
from flask.cli import with_appcontext


@click.group()
def cli():
    """Main entry point"""


@cli.command("init")
@with_appcontext
def init():
    """Create a new admin user"""
    # from api.extensions import db
    # from api.models import User

    # click.echo("create user")
    # user = User(username="admin", email="admin@mail.com", password="admin", active=True)
    # db.session.add(user)
    # db.session.commit()
    # click.echo("created user admin")
    pass

if __name__ == "__main__":
    cli()
