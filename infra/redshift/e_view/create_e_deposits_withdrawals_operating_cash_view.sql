DROP VIEW IF EXISTS source_fiscaldata.e_deposits_withdrawals_operating_cash;

CREATE OR REPLACE VIEW source_fiscaldata.e_deposits_withdrawals_operating_cash as
select
    UPPER(MD5(
        coalesce(record_date::text, 'record_date') || '|' ||
        coalesce(transaction_type::text, 'transaction_type') || '|' ||
        coalesce(src_line_nbr::text, 'src_line_nbr')
    )) as deposits_withdrawals_operating_cash_key
    ,stg.*
    ,UPPER(MD5(
        coalesce(md5(account_type::text), ' ') ||
        coalesce(md5(transaction_catg::text), ' ') ||
        coalesce(md5(transaction_catg_desc::text), ' ') ||
        coalesce(md5(transaction_today_amt::text), ' ') ||
        coalesce(md5(transaction_mtd_amt::text), ' ') ||
        coalesce(md5(transaction_fytd_amt::text), ' ') ||
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
    ,stg.meta_loaded_at as meta_updated_date_extract
from
    source_fiscaldata.deposits_withdrawals_operating_cash_stg stg
with no schema binding;