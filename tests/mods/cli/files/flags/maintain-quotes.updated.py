from argparse import ArgumentParser


def main() -> None:
    parser: ArgumentParser = ArgumentParser()
    parser.add_argument('--company-id', type=int, required=True)
    parser.add_argument('''--company-id-1''', type=int, required=True)
    parser.add_argument("""--company-id-2""", type=int, required=True)
    parser.add_argument(
        '--customer-ids',
        type=str,
        nargs='+',
        help='A space-separated list of customer IDs',
    )
    parser.add_argument(
        "--emails",
        type=str,
        nargs="+",
        help="A space-separated list of email addresses",
    )
    # If not handled carefully(skipped), assignment expansion will trow an exception in the codemod.
    a, b = 1, 2


if __name__ == '__main__':
    main()
