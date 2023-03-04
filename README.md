# Project Stack Example
This project is an example of how to setup a stack containing a database and an API.  
The stack is comprised [PostgreSQL](https://www.postgresql.org/) for the database, and a [Flask](https://flask.palletsprojects.com/en/2.2.x/) application being served by [Waitress](https://docs.pylonsproject.org/projects/waitress/en/latest/).  

## Setting Up and Running
When running locally, fill-in the `.env` file, the `POSTGRES_PASSWORD` is the password that Postgres will use, the `ALPHA_VANTAGE_API_KEY` is the key that will be used to make requests to the [AlphaVantage Stock API](https://www.alphavantage.co/), a free key can be requested [here](https://www.alphavantage.co/support/#api-key). An example of `.env` is available as `.env.example`.  

Example of how the `.env` should look like, this values are for example purposes only:
```
ALPHA_VANTAGE_API_KEY="aaaabbbbccccdddd"
POSTGRES_PASSWORD="password123"
```
Install [Docker](https://docs.docker.com/get-docker/) on your system.  With Docker installed, run the following command to build and run the stack:
```
docker compose up
```
After the stack is up and running, it should be possible to check the status of the containers using `docker ps -a`. The output should look something like:
```
$> docker ps -a
CONTAINER ID   IMAGE                   COMMAND                  CREATED              STATUS              PORTS                    NAMES
0fbefea99317   python_assignment-api   "waitress-serve --ca…"   About a minute ago   Up About a minute   0.0.0.0:8080->8080/tcp   python_assignment-api-1
5595c8ac7420   postgres:alpine         "docker-entrypoint.s…"   About an hour ago    Up About a minute   5432/tcp                 python_assignment-postgres-1
```
Initially the Postgres database is going to be empty, so the following command is needed to set up the database, tables, and collect the data from AlphaVantage. You will need the name of the Flask application seen on the step above.
```
docker exec python_assignment-api-1 python get_raw_data.py
```
With that it should be now possible to query the API.

## Queries
The API exposes 2 endpoints: `financial_data` and `statistics`.
### ✧ `financial_data`  
Recovers the `symbol` (name of the equity), `date`, `open_price`, `close_price` and `volume`.
#### Parameters
* `symbol`: (Optional) Name of equity to recover data from.
* `start_date`: (Optional) Filters dates that are earlier than this.
* `end_date`: (Optional) Filters dates that are later than this.
* `limit`: (Optional, Default=5) Limit the number of items in the response.
* `page`: (Optional, Default=1) Get the page of number `page` for results that go over the limit.
#### Example
[http://localhost:8080/api/financial_data?start_date=2023-02-01&end_date=2023-02-28&symbol=IBM&limit=5&page=1](http://localhost:8080/api/financial_data?start_date=2023-02-01&end_date=2023-02-28&symbol=IBM&limit=5&page=1)  
**Note**: An empty response might mean that the dates are too old for when you are  

### ✧ `statistics`  
Recovers the `symbol` (name of the equity), `start_date`, `end_date`, `average_daily_open_price`, `average_daily_close_price` and `average_daily_volume`.
#### Parameters
* `symbol`: Name of equity to recover data from.
* `start_date`: Filters dates that are earlier than this.
* `end_date`: Filters dates that are later than this.
#### Example
[http://localhost:8080/api/statistics?start_date=2023-02-01&end_date=2023-03-02&symbol=IBM](http://localhost:8080/api/statistics?start_date=2023-02-01&end_date=2023-02-28&symbol=IBM)  
**Note**: An empty response might mean that the dates are too old for when you are  

## Security
For local development, the use of `.env` to set the enviroment variables of the docker compose is enough, but including it in the deployment of the production version is a security risk. Each provider has a proper way of setting enviroment variables securely, refer to the documentation of your server provider for the proper way of setting environment variables.