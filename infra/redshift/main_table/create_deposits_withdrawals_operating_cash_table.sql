CREATE TABLE IF NOT EXISTS fiscaldata.deposits_withdrawals_operating_cash (
    record_date              DATE           NOT NULL,
    account_type              VARCHAR(100),
    transaction_type          VARCHAR(100)   NOT NULL,
    transaction_catg          VARCHAR(200),
    transaction_catg_desc     VARCHAR(300),
    transaction_today_amt     BIGINT,
    transaction_mtd_amt       BIGINT,
    transaction_fytd_amt      BIGINT,
    table_nbr                 VARCHAR(10),
    table_nm                  VARCHAR(200),
    sub_table_name            VARCHAR(200),
    src_line_nbr              INTEGER        NOT NULL,
    record_fiscal_year        SMALLINT,
    record_fiscal_quarter     SMALLINT,
    record_calendar_year      SMALLINT,
    record_calendar_quarter   SMALLINT,
    record_calendar_month     SMALLINT,
    record_calendar_day       SMALLINT,
    deposits_withdrawals_operating_cash_key  VARCHAR(32),
    meta_datahash              VARCHAR(32),
    meta_etl_operation          VARCHAR(10),
    meta_updated_by              VARCHAR(200),
    meta_updated_date            TIMESTAMP,
    meta_from_source              VARCHAR(500),
    PRIMARY KEY (record_date, transaction_type, src_line_nbr)
)
DISTSTYLE KEY
DISTKEY (record_date)
SORTKEY (record_date, transaction_type, src_line_nbr);