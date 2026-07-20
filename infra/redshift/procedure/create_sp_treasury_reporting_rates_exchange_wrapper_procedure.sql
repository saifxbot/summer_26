CREATE OR REPLACE PROCEDURE source_fiscaldata.sp_treasury_reporting_rates_exchange(
    skip_source_filters varchar(4000)
)
    LANGUAGE plpgsql
AS $$
BEGIN
    CALL control.sp_load_delete_insert(
        'load_treasury_reporting_rates_exchange',
        'fiscaldata',
        'treasury_reporting_rates_exchange',
        'record_date, country, currency, country_currency_desc, exchange_rate, effective_date, src_line_nbr, record_fiscal_year, record_fiscal_quarter, record_calendar_year, record_calendar_quarter, record_calendar_month, record_calendar_day',
        skip_source_filters,
        'record_date',
        'source_fiscaldata',
        'e_treasury_reporting_rates_exchange'
    );
EXCEPTION
    WHEN OTHERS THEN
        RAISE INFO 'ERROR in sp_treasury_reporting_rates_exchange';
END;
$$
;