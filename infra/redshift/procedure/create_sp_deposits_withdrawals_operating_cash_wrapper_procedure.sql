CREATE OR REPLACE PROCEDURE source_fiscaldata.sp_deposits_withdrawals_operating_cash(
    skip_source_filters varchar(4000)
)
    LANGUAGE plpgsql
AS $$
BEGIN
    CALL control.sp_load_delete_insert(
        'load_deposits_withdrawals_operating_cash',
        'fiscaldata',
        'deposits_withdrawals_operating_cash',
        'record_date, account_type, transaction_type, transaction_catg, transaction_catg_desc, transaction_today_amt, transaction_mtd_amt, transaction_fytd_amt, table_nbr, table_nm, sub_table_name, src_line_nbr, record_fiscal_year, record_fiscal_quarter, record_calendar_year, record_calendar_quarter, record_calendar_month, record_calendar_day',
        skip_source_filters,
        'record_date',
        'source_fiscaldata',
        'e_deposits_withdrawals_operating_cash'
    );
EXCEPTION
    WHEN OTHERS THEN
        RAISE INFO 'ERROR in sp_deposits_withdrawals_operating_cash';
END;
$$
;