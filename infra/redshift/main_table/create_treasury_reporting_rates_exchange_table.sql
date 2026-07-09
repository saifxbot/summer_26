CREATE TABLE IF NOT EXISTS fiscaldata.treasury_reporting_rates_exchange (
    record_date               DATE           NOT NULL,
    country                    VARCHAR(100)   NOT NULL,
    currency                   VARCHAR(100)   NOT NULL,
    country_currency_desc      VARCHAR(300),
    exchange_rate               NUMERIC(18,6),
    effective_date              DATE,
    src_line_nbr                INTEGER        NOT NULL,
    record_fiscal_year          SMALLINT,
    record_fiscal_quarter       SMALLINT,
    record_calendar_year        SMALLINT,
    record_calendar_quarter     SMALLINT,
    record_calendar_month       SMALLINT,
    record_calendar_day         SMALLINT,
    treasury_reporting_rates_exchange_key  VARCHAR(32),
    meta_datahash                VARCHAR(32),
    meta_etl_operation             VARCHAR(10),
    meta_updated_by                 VARCHAR(200),
    meta_updated_date                TIMESTAMP,
    meta_from_source                  VARCHAR(500),
    PRIMARY KEY (record_date, country, currency, src_line_nbr)
)
DISTSTYLE KEY
DISTKEY (record_date)
SORTKEY (record_date, country, currency, src_line_nbr);