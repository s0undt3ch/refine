from django.core.management import BaseCommand
from django.core.management import BaseCommand as DjangoCommand
import django.core.management.BaseCommand as AnotherCommand


class MyCommand(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--user-id", help="The user ID")
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--company-id", help="The company ID")
        group.add_argument("--organization-id", help="The organization ID")


class AnotherDjangoCommand(DjangoCommand):
    def add_arguments(self, parser):
        parser.add_argument("--project-id", help="The project ID")
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--team-id", help="The team ID")
        group.add_argument("--department-id", help="The department ID")


class YetAnotherCommand(AnotherCommand):
    def add_arguments(self, parser):
        parser.add_argument("--task-id", help="The task ID")
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--sprint-id", help="The sprint ID")
        group.add_argument("--milestone-id", help="The milestone ID")
