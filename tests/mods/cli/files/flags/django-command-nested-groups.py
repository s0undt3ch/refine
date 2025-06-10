from django.core.management import BaseCommand


class MyCommand(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--user_id", help="The user ID")

        # First level group
        group1 = parser.add_mutually_exclusive_group(required=True)
        group1.add_argument("--company_id", help="The company ID")

        # Nested group
        nested_group = group1.add_mutually_exclusive_group()
        nested_group.add_argument("--team_id", help="The team ID")
        nested_group.add_argument("--department_id", help="The department ID")

        # Another first level group
        group2 = parser.add_mutually_exclusive_group()
        group2.add_argument("--project_id", help="The project ID")
        group2.add_argument("--organization_id", help="The organization ID")
