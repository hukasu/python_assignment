import os
import datetime
from typing import List, Any

from flask import Flask, Blueprint, Response
from flask import request, current_app, g, jsonify

import psycopg2

def get_envvar(name: str) -> str:
    envvar = os.environ.get(name)
    if envvar is None:
        current_app.logger.error("Enviroment variable `{}` is not set.".format(name))
        exit(1)
    return envvar

def get_database():
    if g.get("db") is None:
        g.db = psycopg2.connect(
            host="postgres",
            dbname="postgres",
            user="postgres",
            password=get_envvar("POSTGRES_PASSWORD")
        )

    return g.db

def close_database(exception):
    logger = current_app.logger

    db = g.pop("db", None)
    if db is not None:
        logger.debug("Closing database connection")
        db.close()

def convert_dates(start_date, end_date, required, logger):
    if start_date is None:
        if required:
            return make_statistics_response(
                error="Argument `start_date` is required for `statistics` request.",
                status_code=400
            )
    else:
        try:
            start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            logger.exception("`start_date` has invalid format.")
            return make_statistics_response(
                error="Argument `start_date` has invalid format. Passed argument `{}`.".format(start_date),
                status_code=400
            )
        
    if end_date is None:
        if required:
            return make_statistics_response(
                error="Argument `end_date` is required for `statistics` request.",
                status_code=400
            )
    else:
        try:
            end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            logger.exception("`end_date` has invalid format.")
            return make_statistics_response(
                error="Argument `end_date` has invalid format. Passed argument `{}`.".format(end_date),
                status_code=400
            )
        
    if start_date is not None and end_date is not None and start_date > end_date:
        logger.error("`start_date` is a later date than `end_date`.")
        return make_statistics_response(
            error="Argument `start_date` must be a earlier date than `end_date`. Passed arguments `{}` <=> `{}`.".format(start_date, end_date),
            status_code=400
        )
    else:
        return (start_date, end_date)

def make_financial_data_response(
        data: List[Any] = None,
        count: int = 0,
        page: int = 0,
        limit: int = 0,
        error: str = "",
        status_code: int = 200
) -> Response:
    # Build response data
    if data is not None:
        rows = [
            {
                "symbol": d[0].strip(),
                "date": d[1].strftime("%Y-%m-%d"),
                "open_price": d[2],
                "close_price": d[3],
                "volume": d[4],
            } for d in data
        ]
    else:
        rows = []

    # Build response
    resp = jsonify(
        {
            "data": rows,
            "pagination": {
                "count": count,
                "page": page,
                "limit": limit,
                "pages": 0 if count == 0 or limit == 0 else (count // limit) + 1
            },
            "info": {
                "error": error
            }
        }
    )
    resp.status_code = status_code
    return resp

def financial_data():
    logger = current_app.logger
    db = get_database()
    args = request.args

    # Get request arguments
    symbol = args.get("symbol")
    
    date_conversion = convert_dates(args.get("start_date"), args.get("end_date"), False, logger)
    if type(date_conversion) is Response:
        return date_conversion
    else:
        start_date, end_date = date_conversion

    # Cast limit to integer or get default value
    limit = args.get("limit")
    if limit is not None:
        try:
            limit = int(limit)
        except ValueError as e:
            logger.exception(e)
            return make_financial_data_response(
                error="Argument `limit` is not an integer. Passed argument was `{}`".format(limit),
                status_code=400
            )
    else:
        limit = 5

    # Cast page to integer or get default value
    page = args.get("page")
    if page is not None:
        try:
            page = int(page)
            if page <= 0:
                return make_financial_data_response(
                    error="Page must be a positive number bigger than zero. Passed argument was `{}`.".format(page),
                    status_code=400
                )
        except ValueError as e:
            logger.exception(e)
            return make_financial_data_response(
                error="Argument `page` is not an integer. Passed argument was `{}`".format(page),
                status_code=400
            )
    else:
        page = 1

    # Calculate offset
    # Internally, page is zero-indexed
    offset = (page - 1) * limit

    # Build where clause
    wheres = []
    if symbol is not None:
        wheres.append("symbol = '{}'".format(symbol))
    if start_date is not None:
        wheres.append("date >= '{}'".format(start_date))
    if end_date is not None:
        wheres.append("date <= '{}'".format(end_date))

    if len(wheres) == 0:
        wheres = ""
    else:
        wheres = " AND ".join(wheres)

    # Build query
    query = "SELECT * FROM financial_data {where} ORDER BY date DESC;".format(
        where="WHERE {}".format(wheres) if wheres else "",
    )
    with db.cursor() as cur:
        try:
            # Execute query
            cur.execute(query)
            rows = cur.fetchall()
        except psycopg2.errors.UndefinedTable:
            logger.exception("Database is uninitialized.")
            return make_financial_data_response(
                error="The application is still being initialized.",
                status_code=500
            )
    # Get count
    count = len(rows)
    # Filter response
    rows = rows[offset:(offset + limit)]

    return make_financial_data_response(
        rows,
        count,
        page,
        limit,
        status_code=200,
    )

def make_statistics_response(
        symbol: str = None,
        start_date: datetime.date = None,
        end_date: datetime.date = None,
        avg_open: float = None,
        avg_close: float = None,
        avg_volume: float = None,
        error: str = "",
        status_code: int = 200
) -> Response:
    logger = current_app.logger
    # Build response data
    if avg_open is None:
        assert(avg_close is None)
        assert(avg_volume is None)
        logger.debug("Empty response")
        data = None
        error = "The query had no results. Try another date range and verify symbol is correct."
    if not error:
        data = {}
        data["symbol"] = symbol
        data["start_date"] = start_date.isoformat()
        data["end_date"] = end_date.isoformat()
        data["average_daily_open_price"] = avg_open
        data["average_daily_close_price"] = avg_close
        data["average_daily_volume"] = avg_volume
        
    info = {"error": error}

    # Build response
    resp = jsonify(
        data=data,
        info=info
    )
    resp.status_code = status_code
    return resp

def statistics():
    logger = current_app.logger
    db = get_database()
    args = request.args

    # Get request arguments
    symbol = args.get("symbol")
    if symbol is None:
        return make_statistics_response(
            error="Argument `symbol` is required for `statistics` request.",
            status_code=400
        )
    
    date_conversion = convert_dates(args.get("start_date"), args.get("end_date"), True, logger)
    if type(date_conversion) is Response:
        return date_conversion
    else:
        start_date, end_date = date_conversion
    
    query = """SELECT AVG(fd.open_price), AVG(fd.close_price), AVG(CAST(fd.volume as FLOAT8))
                FROM financial_data as fd
                WHERE fd.symbol = %s AND (fd.date BETWEEN %s AND %s);"""
    with db.cursor() as cur:
        try:
            # Execute query
            cur.execute(query, (symbol, start_date, end_date))
            rows = cur.fetchone()
        except psycopg2.errors.UndefinedTable:
            logger.exception("Database is uninitialized.")
            return make_financial_data_response(
                error="The application is still being initialized.",
                status_code=500
            )

    return make_statistics_response(
        symbol,
        start_date,
        end_date,
        rows[0],
        rows[1],
        rows[2],
        status_code=200
    )

def create_app(config=None):
    app = Flask(__name__)

    bp = Blueprint("api", __name__)
    bp.add_url_rule("/financial_data", view_func=financial_data)
    bp.add_url_rule("/statistics", view_func=statistics)

    app.register_blueprint(bp, url_prefix="/api")
    app.teardown_appcontext(close_database)
    return app