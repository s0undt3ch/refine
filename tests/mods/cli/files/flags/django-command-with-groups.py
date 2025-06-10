from django.core.management import BaseCommand
from django.core.management import BaseCommand as DjangoCommand
import django.core.management.BaseCommand as AnotherCommand


class MyCommand(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--user_id", help="The user ID")
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--company_id", help="The company ID")
        group.add_argument("--organization_id", help="The organization ID")


class AnotherDjangoCommand(DjangoCommand):
    def add_arguments(self, parser):
        parser.add_argument("--project_id", help="The project ID")
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--team_id", help="The team ID")
        group.add_argument("--department_id", help="The department ID")


class YetAnotherCommand(AnotherCommand):
    def add_arguments(self, parser):
        parser.add_argument("--task_id", help="The task ID")
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--sprint_id", help="The sprint ID")
        group.add_argument("--milestone_id", help="The milestone ID")
