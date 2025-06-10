import argparse
import click
from flask import Flask

app = Flask(__name__)

# argparse
parser = argparse.ArgumentParser()
parser.add_argument("--user-id", help="The user ID")
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--company-id", help="The company ID")
group.add_argument("--organization-id", help="The organization ID")

# click
@click.command()
@click.option("--project-id", help="The project ID")
@click.option("--team-id", help="The team ID")
def click_command(project_id, team_id):
    pass

# flask
@app.cli.command("--task-id")
def flask_command(task_id):
    pass
