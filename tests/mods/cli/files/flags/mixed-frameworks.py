import argparse
import click
from flask import Flask

app = Flask(__name__)

# argparse
parser = argparse.ArgumentParser()
parser.add_argument("--user_id", help="The user ID")
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--company_id", help="The company ID")
group.add_argument("--organization_id", help="The organization ID")

# click
@click.command()
@click.option("--project_id", help="The project ID")
@click.option("--team_id", help="The team ID")
def click_command(project_id, team_id):
    pass

# flask
@app.cli.command("--task_id")
def flask_command(task_id):
    pass
