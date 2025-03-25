from argparse import ArgumentParser

from django.core.management.base import BaseCommand


class Command(BaseCommand):

    help = "Anonymize customers for a company."

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument("--company_id", type=int, required=True)
        parser.add_argument(
            "--customer_ids",
            type=str,
            nargs="+",
            help="A space-separated list of customer IDs",
        )
        parser.add_argument(
            "--emails",
            type=str,
            nargs="+",
            help="A space-separated list of email addresses",
        )
