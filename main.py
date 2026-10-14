import argparse
import logging

from pymongo import MongoClient
from datetime import datetime, timedelta

from sii_scraper.settings import settings
from sii_scraper.credentials import Credentials
from sii_scraper.progress_store import ProgressStore
from sii_scraper.invoice_transformer import InvoiceTransformer
from sii_scraper.invoice_repository import InvoiceRepository
from sii_scraper.runner import SiiScraperRunner



def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the SII scraper")

    parser.add_argument(
        "--month",
        type=str,
        help="month to pass to SiiScraper",
    )

    parser.add_argument(
        "--year",
        type=str,
        help="year to pass to SiiScraper",
    )

    return parser.parse_args()


def main() -> None:
    configure_logging()

    args = parse_args()

    mongo_client = MongoClient(settings.mongo_uri)

    try:
        db = mongo_client[settings.db_name]

        credentials = Credentials()
        progress_store = ProgressStore(settings.progress_file)
        transformer = InvoiceTransformer()
        repository = InvoiceRepository(db)

        runner = SiiScraperRunner(
            credentials=credentials,
            progress_store=progress_store,
            transformer=transformer,
            repository=repository,
            headless=settings.headless,
            use_certificate=settings.use_certificate,
        )

        today = datetime.now()

        if today.day <= 5:
            current_month = today.replace(day=1)
            previous_month = current_month - timedelta(days=1)

            runner.run(
                month=f"{previous_month.month:02d}",
                year=str(previous_month.year),
            )

            runner.run(
                month=f"{current_month.month:02d}",
                year=str(current_month.year),
            )

        else:
            runner.run(
                month=args.month,
                year=args.year,
            )

    finally:
        mongo_client.close()


if __name__ == "__main__":
    main()