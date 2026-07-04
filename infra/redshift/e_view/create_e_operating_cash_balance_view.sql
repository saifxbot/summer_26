DROP VIEW IF EXISTS source_fiscaldata.e_operating_cash_balance;

CREATE OR REPLACE VIEW source_fiscaldata.e_operating_cash_balance as
select
    UPPER(MD5(
        coalesce(record_date::text, 'record_date') || '|' ||
        coalesce(account_type::text, 'account_type') || '|' ||
        coalesce(src_line_nbr::text, 'src_line_nbr')
    )) as operating_cash_balance_key
    ,stg.*
    ,UPPER(MD5(
        coalesce(md5(close_today_bal::text), ' ') ||
        coalesce(md5(open_today_bal::text), ' ') ||
        coalesce(md5(open_month_bal::text), ' ') ||
        coalesce(md5(open_fiscal_year_bal::text), ' ') ||
        coalesce(md5(table_nbr::text), ' ') ||
        coalesce(md5(table_nm::text), ' ') ||
        coalesce(md5(sub_table_name::text), ' ') ||
        coalesce(md5(record_fiscal_year::text), ' ') ||
        coalesce(md5(record_fiscal_quarter::text), ' ') ||
        coalesce(md5(record_calendar_year::text), ' ') ||
        coalesce(md5(record_calendar_quarter::text), ' ') ||
        coalesce(md5(record_calendar_month::text), ' ') ||
        coalesce(md5(record_calendar_day::text), ' ')
    )) as meta_datahash
    ,'INS' as meta_etl_operation_extract
from
    source_fiscaldata.operating_cash_balance_stg stg
with no schema binding;