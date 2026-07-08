CREATE OR REPLACE PROCEDURE source_fiscaldata.sp_operating_cash_balance(
    skip_source_filters varchar(4000)
)
    LANGUAGE plpgsql
AS $$
BEGIN
    CALL control.sp_load_delete_insert(
        'load_operating_cash_balance',
        'fiscaldata',
        'operating_cash_balance',
        'record_date, account_type, close_today_bal, open_today_bal, open_month_bal, open_fiscal_year_bal, table_nbr, table_nm, sub_table_name, src_line_nbr, record_fiscal_year, record_fiscal_quarter, record_calendar_year, record_calendar_quarter, record_calendar_month, record_calendar_day',
        skip_source_filters,
        'record_date',
        'source_fiscaldata',
        'e_operating_cash_balance'
    );
EXCEPTION
    WHEN OTHERS THEN
        RAISE INFO 'ERROR in sp_operating_cash_balance';
END;
$$
;