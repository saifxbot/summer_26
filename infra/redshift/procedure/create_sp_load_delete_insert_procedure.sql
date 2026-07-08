CREATE OR REPLACE PROCEDURE control.sp_load_delete_insert(
    procedure_name varchar(4000),
    target_schema_name varchar(4000),
    target_table_name varchar(4000),
    target_table_columns varchar(max),
    skip_source_filters varchar(4000),
    delete_partition varchar(4000),
    extract_schema_name varchar(4000),
    extract_view_name varchar(4000)
)
    LANGUAGE plpgsql
AS $$
DECLARE
  query varchar(max);
  insert_query varchar(max);
  update_query varchar(max);
  delete_trg_query varchar(max);
  insert_trg_query varchar(max);
  v_drop_temp_table_query varchar(max);
  v_filename  varchar(max);
  v_affected_records integer;
  v_target_table varchar(max);
  v_temp_table varchar(max);
  v_extract_view_name varchar(max);
  v_target_table_key_name varchar(max);
  v_source_fetched_from_meta_updated_date timestamp;
  v_load_control_key varchar(max);
  v_source_fetched_to_meta_updated_date_query varchar(max);
  v_skip_source_filters varchar(max);
  v_temp_table_records varchar(max);
  v_temp_table_unique_keys varchar(max);
  v_temp_table_delete_partitions varchar(max);
BEGIN
  IF skip_source_filters IS NULL or (skip_source_filters != 'skip_datahash'
                                  and skip_source_filters != 'skip_updated_date'
                                  and skip_source_filters != 'skip_all'
                                  and skip_source_filters != 'skip_none'
                                )
  THEN v_skip_source_filters := 'skip_none';
  ELSE v_skip_source_filters := skip_source_filters;
  END IF;
  RAISE INFO 'target_schema_name %', target_schema_name;
  RAISE INFO 'target_table_name %', target_table_name;
  v_target_table := '' || target_schema_name || '.' || target_table_name || '' ;
  v_extract_view_name := '' || extract_schema_name || '.' || extract_view_name || '' ;
  v_target_table_key_name := target_table_name || '_key';
  RAISE INFO 'v_target_table % ;', v_target_table;
  RAISE INFO 'v_extract_view_name % ;', v_extract_view_name;
  RAISE INFO 'insert into LOAD_CONTROL query SUCCEEDED;';
  select
    coalesce(max(source_fetched_to_meta_updated_date),date'1900-01-01') as date_until
    from control.LOAD_CONTROL
    where meta_updated_by = procedure_name AND STATUS = 'SUCCEEDED' into v_source_fetched_from_meta_updated_date;
  RAISE INFO 'v_source_fetched_from_meta_updated_date % ;', v_source_fetched_from_meta_updated_date;
  v_load_control_key := upper(md5(
      md5(procedure_name ::text) ||
      md5(floor(extract(epoch from sysdate))::text)
  )) ;
  RAISE INFO 'v_load_control_key % ;', v_load_control_key;
  SELECT target_table_name ||  '_temp_' || round(1000*extract(epoch from now())) into v_temp_table;
  RAISE INFO 'v_temp_table % ;', v_temp_table;
  select target_schema_name || target_table_name || round(1000*extract(epoch from now())) into v_temp_table_delete_partitions;
  RAISE INFO 'v_temp_table_processed_filenames %', v_temp_table_delete_partitions;
  query := 'CREATE TEMPORARY TABLE ' || v_temp_table_delete_partitions || ' as (
            select
              distinct ' || delete_partition  || ' delete_partitions_list
            from ' || v_extract_view_name || ' e_view
            where   1=1
              and e_view.meta_updated_date_extract > to_timestamp(''' || v_source_fetched_from_meta_updated_date || ''',
                ''YYYY-MM-DD HH24:MI:SS.US'')::TIMESTAMP)';
  RAISE INFO 'query ; %', query;
  EXECUTE query;
  RAISE INFO 'Creating temp table for to be prosessed delete partitions SUCCEEDED';
  -- Inserting changed and new records to TEMP table.
  -- A candidate row (matching the changed partition) is kept only if it is
  -- either brand new (no matching key in target yet) or its meta_datahash
  -- differs from what is currently stored in target - i.e. content actually
  -- changed, not just "touched" (e.g. re-loaded with the same values).
  insert_query := 'create temp table ' || v_temp_table || ' as
    (
    select
      upd.*
      ,case when upd.meta_etl_operation_extract = ''DEL'' then ''DEL'' else ''INS'' end AS meta_etl_operation
      ,''' || procedure_name || ''' AS meta_updated_by
      ,sysdate AS meta_updated_date
    from
        ' || v_extract_view_name || ' upd
    left join ' || v_target_table || ' t
      on t.' || v_target_table_key_name || ' = upd.' || v_target_table_key_name || '
    where 1=1
    AND (
      (
        upd.' || delete_partition || ' in (select delete_partitions_list from ' || v_temp_table_delete_partitions || ')
        AND (
          t.' || v_target_table_key_name || ' is null
          or t.meta_datahash <> upd.meta_datahash
        )
      )
        or (''' || v_skip_source_filters || ''' <> ''skip_none'' and ''' || v_skip_source_filters || ''' <> ''skip_datahash'')
        --false: skip datahash, true: filter by updated_date
      )
    )';
  RAISE INFO 'insert_query; % ;', insert_query;
  EXECUTE  insert_query;
  -- Delete any rows from TARGET that exist in TEMP, because they are updates
  RAISE INFO 'insert_query SUCCEEDED ;';
  --Ensure uniqueness of records
  execute 'select count( distinct ' || v_target_table_key_name || ' ) from ' ||  v_temp_table  || ';' into   v_temp_table_unique_keys ;
  execute 'select count( ' || v_target_table_key_name || ' ) from ' ||   v_temp_table  ||  ';'   into  v_temp_table_records ;
  RAISE INFO 'v_temp_table_unique_keys; % ;', v_temp_table_unique_keys;
  RAISE INFO 'v_temp_table_records; % ;', v_temp_table_records;
  IF v_temp_table_records != v_temp_table_unique_keys
  THEN
    RAISE EXCEPTION 'Source records are not unique. Please check possible duplicates with insert; % ; and update ; % ; queries;', insert_query, update_query;
  END IF;
  delete_trg_query := 'delete from ' || v_target_table || '
  where ' || v_target_table_key_name || ' in (
      select
        distinct ' || v_target_table_key_name || '
      from ' || v_temp_table || '
    )';
  RAISE INFO 'delete_trg_query; % ;', delete_trg_query;
  EXECUTE delete_trg_query;
  RAISE INFO 'delete_trg_query SUCCEEDED ;';
  insert_trg_query := 'insert into ' || v_target_table || '
    (
      ' || v_target_table_key_name ||
      ' ,meta_datahash ,meta_etl_operation ,meta_updated_by ,meta_updated_date ,meta_from_source,
      ' || target_table_columns ||  '
    )
  select
      ' || v_target_table_key_name ||
      ' ,meta_datahash ,meta_etl_operation ,meta_updated_by ,meta_updated_date ,meta_from_source,
      ' || target_table_columns ||  '
  from ' || v_temp_table ||'
  where ' || v_target_table_key_name || ' is not null';
  RAISE INFO 'insert_trg_query; % ;', insert_trg_query;
  -- Insert all the rows from the TEMP table into the TARGET table
  EXECUTE insert_trg_query;
  GET DIAGNOSTICS v_affected_records := ROW_COUNT;
  RAISE INFO 'insert_trg_query SUCCEEDED ;';
  RAISE INFO 'v_affected_records % ;', v_affected_records;
  COMMIT;
  insert into control.LOAD_CONTROL (
      load_control_key
      ,meta_updated_by
      ,meta_updated_date
      ,source_fetched_from_meta_updated_date
      ,affected_records
      ,target_table
      ,status
    )
  values
    (
      v_load_control_key
      ,procedure_name
      ,sysdate
      ,to_timestamp( v_source_fetched_from_meta_updated_date , 'YYYY-MM-DD HH24:MI:SS' )::TIMESTAMP
      ,v_affected_records
      ,v_target_table
      ,'SUCCEEDED'
    )
  ;
  RAISE INFO 'INSERT INTO LOAD_CONTROL query SUCCEEDED';
  --update source_fetched_to_meta_updated_date into control table
  v_source_fetched_to_meta_updated_date_query :=
  'UPDATE control.LOAD_CONTROL
  set source_fetched_to_meta_updated_date =
  nvl((SELECT MAX(meta_updated_date_extract) FROM ' || v_temp_table || '), source_fetched_from_meta_updated_date)
  WHERE load_control_key = ''' || v_load_control_key || ''' and 1=1 ';
  RAISE INFO 'v_source_fetched_to_meta_updated_date_query; % ;', v_source_fetched_to_meta_updated_date_query;
  EXECUTE v_source_fetched_to_meta_updated_date_query;
  RAISE INFO 'UPDATE source_fetched_to_meta_updated_date query SUCCEEDED';
  v_drop_temp_table_query := 'drop table ' || v_temp_table;
  RAISE INFO 'v_drop_temp_table_query; % ;', v_drop_temp_table_query;
  -- Drop the TEMP table
  EXECUTE v_drop_temp_table_query;
  RETURN;
EXCEPTION
  WHEN OTHERS THEN
    RAISE INFO 'ERROR. Procedure % Failed', procedure_name;
END;
$$
;