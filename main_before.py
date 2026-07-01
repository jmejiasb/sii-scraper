import os
import re
import argparse
import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv
from pymongo import MongoClient
from selenium.common.exceptions import TimeoutException

from sii_scraper.sii_scraper import SiiScraper

load_dotenv()

PROGRESS_FILE = "sii_progress.txt"

def main(month=None, year=None):

    atlas_uri = os.getenv("MONGODB_URI")
    client = MongoClient(atlas_uri)
    db = client.arrocera_erp_db
    inv_supplier = db.invoices_supplier
    print("Conectado a base de datos")

    completed_users = load_completed_users()

    creds = load_all_credentials()
    if not creds:
        raise RuntimeError("No SII_USER_N / SII_PASS_N found in environment.")

    all_dfs = []
    print("Obteniendo datos de facturas desde SII")
    for user, pw in creds.items():

        if user in completed_users:
            print(f"Skipping {user}, already completed")
            continue

        print(f"Scraping facturas para {user}…")
        try:
            scraper_kwargs = {"headless": True}

            if month is not None:
                scraper_kwargs["month"] = month
            if year is not None:
                scraper_kwargs["year"] = year

            scraper = SiiScraper(user, pw, **scraper_kwargs)
            df = scraper.scrape_all()
            df["sii_user"] = user

            df_cleaned = clean_and_normalize(df)
            print("Limpiando datos")

            total = len(df_cleaned)
            inserted = 0
            updated = 0
            for _, row in tqdm(df_cleaned.iterrows(), total=total,
                               desc="Sicronizando facturas", unit="inv"):

                # build your dedupe filter
                filt = {
                    "supplier_id": row["supplier_id"],
                    "number": row["number"],
                }

                data = row.to_dict()

                result = inv_supplier.update_one(
                    filt,
                    {"$set": {"status": data["status"]}}
                )

                if result.matched_count:
                    # an existing document was found and updated
                    updated += 1
                    mark_user_completed(user)
                else:
                    # no existing doc → insert it
                    inv_supplier.insert_one(data)
                    inserted += 1

            print(
                f"\nFinalizado: {inserted} nuevas facturas insertadas, {updated} facturas actualizadas")
        except TimeoutException:
            print(f"Timeout while scraping {user}, continuing with next user")
            continue
        except Exception as e:
            print(f"Error scraping {user}: {e}")
            continue
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)


def debug_scraper(month=None, year=None):

    atlas_uri = os.getenv("MONGODB_URI")
    client = MongoClient(atlas_uri)
    db = client.arrocera_erp_db
    inv_supplier = db.invoices_supplier
    print("Conectado a base de datos")

    creds = load_all_credentials()
    if not creds:
        raise RuntimeError("No SII_USER_N / SII_PASS_N found in environment.")

    all_dfs = []
    print("Obteniendo datos de facturas desde SII")

    scraper_kwargs = {
        # "use_certificate": True,
        "headless": False,
    }

    if month is not None:
        scraper_kwargs["month"] = month
    if year is not None:
        scraper_kwargs["year"] = year

    scraper = SiiScraper(
        user="",
        pwd="",
        **scraper_kwargs
    )

    df = scraper.scrape_all()
    df["sii_user"] = ""
    all_dfs.append(df)

    print(all_dfs)

    df = pd.concat(all_dfs, ignore_index=True)
    df.to_csv("compras_df.csv", sep=";")

    df_cleaned = clean_and_normalize(df)
    print("Limpiando datos")

    total = len(df_cleaned)
    inserted = 0
    updated = 0
    for _, row in tqdm(df_cleaned.iterrows(), total=total,
                       desc="Sicronizando facturas", unit="inv"):

        # build your dedupe filter
        filt = {
            "supplier_id": row["supplier_id"],
            "number":      row["number"],
        }

        data = row.to_dict()

        result = inv_supplier.update_one(
            filt,
            {"$set": {"status": data["status"]}}
        )

        if result.matched_count:
            # an existing document was found and updated
            updated += 1
        else:
            # no existing doc → insert it
            inv_supplier.insert_one(data)
            inserted += 1

    print(
        f"\nFinalizado: {inserted} nuevas facturas insertadas, {updated} facturas actualizadas")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Run the SII scraper")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="run the debug_scraper() instead of main()"
    )
    parser.add_argument(
        "--month",
        type=str,
        help="month to pass to SiiScraper"
    )

    parser.add_argument(
        "--year",
        type=str,
        help="year to pass to SiiScraper"
    )
    args = parser.parse_args()

    kwargs = {}
    if args.month is not None:
        kwargs["month"] = args.month
    if args.year is not None:
        kwargs["year"] = args.year

    if args.debug:
        debug_scraper(**kwargs)
    else:
        main(**kwargs)
