import argparse
from argparse import ArgumentParser


def main() -> None:
    parser = ArgumentParser()
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


def main_2() -> None:
    parser = argparse.ArgumentParser()
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


if __name__ == "__main__":
    main()
