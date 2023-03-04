CREATE TABLE IF NOT EXISTS financial_data (
    symbol CHAR(8),
    date DATE,
    open_price FLOAT8,
    close_price FLOAT8,
    volume INT,
    UNIQUE(symbol, date)
);