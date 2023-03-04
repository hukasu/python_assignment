import os
import datetime
import logging

from pathlib import Path

import pandas as pd

import psycopg2

from alpha_vantage import timeseries

logging.basicConfig()
logger = logging.getLogger(Path(__file__).stem)
logger.setLevel(logging.DEBUG)

def get_envvar(name: str) -> str:
    envvar = os.environ.get(name)
    if envvar is None:
        logger.error("Enviroment variable `{}` is not set.".format(name))
        exit(1)
    return envvar

def start_database():
    logger.debug("Opening connection")
    with psycopg2.connect(
        host="postgres",
        dbname="postgres",
        user="postgres",
        password=get_envvar("POSTGRES_PASSWORD")
    ) as db:
        with db.cursor() as cur:
            logger.debug("Creating table")
            with open("schema.sql") as sql_file:
                sql_script = sql_file.read()
                cur.execute(sql_script)
        
        db.commit()
        return db

def retrieve_financial_data(db, symbol: str, api_key: str):
    logger.debug("Loading `{}` timeseries from API".format(symbol))
    (df, ts) = timeseries.TimeSeries(key=api_key, output_format="pandas").get_daily_adjusted(symbol)
    df: pd.DataFrame = df # just to have proper autocomplete

    # Cleaning columns names
    ncols = [c[3:] for c in df.columns]
    df.columns = ncols
    # Get a date from 2 weeks ago
    today = datetime.date.today()
    two_week_ago = today - datetime.timedelta(weeks=2)

    # Filtering two weeks of data
    two_week_view: pd.DataFrame = df[df.index.date >= two_week_ago]

    # Creating list of data to be inserted
    data = [(symbol.strip(), d.date(), sd["open"], sd["adjusted close"], sd["volume"]) for (d, sd) in two_week_view.iterrows()]
    # Inserting data into database
    logger.debug("Inserting `{}` lines into `financial_data` table.".format(len(data)))
    cur = db.cursor()
    cur.executemany("""
        INSERT INTO financial_data (symbol, date, open_price, close_price, volume)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (symbol, date)
        DO UPDATE
        SET open_price = EXCLUDED.open_price, close_price = EXCLUDED.close_price, volume = EXCLUDED.volume;
    """, data)
    db.commit()

if __name__ == "__main__":
    api_key = get_envvar("ALPHA_VANTAGE_API_KEY")

    db = start_database()

    retrieve_financial_data(db, "IBM", api_key)
    retrieve_financial_data(db, "AAPL", api_key)

    db.close()