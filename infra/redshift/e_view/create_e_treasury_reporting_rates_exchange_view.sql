DROP VIEW IF EXISTS source_fiscaldata.e_treasury_reporting_rates_exchange;

CREATE OR REPLACE VIEW source_fiscaldata.e_treasury_reporting_rates_exchange as
select
    UPPER(MD5(
        coalesce(record_date::text, 'record_date') || '|' ||
        coalesce(country::text, 'country') || '|' ||
        coalesce(currency::text, 'currency') || '|' ||
        coalesce(src_line_nbr::text, 'src_line_nbr')
    )) as treasury_reporting_rates_exchange_key
    ,stg.*
    ,UPPER(MD5(
        coalesce(md5(country_currency_desc::text), ' ') ||
        coalesce(md5(exchange_rate::text), ' ') ||
        coalesce(md5(effective_date::text), ' ') ||
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
    source_fiscaldata.treasury_reporting_rates_exchange_stg stg
with no schema binding;