CREATE TABLE IF NOT EXISTS fiscaldata.operating_cash_balance (
    record_date              DATE           NOT NULL,
    account_type             VARCHAR(100)   NOT NULL,
    close_today_bal          DECIMAL(18,2),
    open_today_bal           DECIMAL(18,2),
    open_month_bal           DECIMAL(18,2),
    open_fiscal_year_bal     DECIMAL(18,2),
    table_nbr                VARCHAR(10),
    table_nm                 VARCHAR(200),
    sub_table_name           VARCHAR(200),
    src_line_nbr             SMALLINT       NOT NULL,
    record_fiscal_year       SMALLINT,
    record_fiscal_quarter    SMALLINT,
    record_calendar_year     SMALLINT,
    record_calendar_quarter  SMALLINT,
    record_calendar_month    SMALLINT,
    record_calendar_day      SMALLINT,
    PRIMARY KEY (record_date, account_type, src_line_nbr)
)
DISTSTYLE KEY
DISTKEY (record_date)
SORTKEY (record_date, account_type, src_line_nbr);