-- BLUEPRINT: PostgreSQL Index Audit
-- STRUCTURAL: Query structure and column selection are reusable across any schema.
-- ILLUSTRATIVE: Schema filter ('public') and LIMIT values are replaceable per environment.

-- Tables with high sequential scan rates (candidate for missing indexes or stale stats)
SELECT
    now() AS captured_at,
    schemaname,
    relname AS table_name,
    seq_scan,
    idx_scan,
    n_live_tup AS estimated_rows,
    ROUND(
        seq_scan::numeric / NULLIF(seq_scan + idx_scan, 0),
        4
    ) AS seq_scan_ratio
FROM pg_stat_user_tables
ORDER BY seq_scan DESC
LIMIT 50;

-- Unused or rarely used indexes (non-PK)
-- STRUCTURAL: pg_stat_user_indexes lacks indisprimary — must JOIN pg_index to filter PKs.
SELECT
    now() AS captured_at,
    psi.schemaname,
    psi.relname AS table_name,
    psi.indexrelname AS index_name,
    psi.idx_scan,
    psi.idx_tup_read,
    psi.idx_tup_fetch,
    pg_size_pretty(pg_relation_size(psi.indexrelid)) AS index_size
FROM pg_stat_user_indexes psi
JOIN pg_index pi ON pi.indexrelid = psi.indexrelid
WHERE psi.idx_scan = 0
  AND NOT pi.indisprimary
ORDER BY pg_relation_size(psi.indexrelid) DESC
LIMIT 50;

-- FK columns that may be missing indexes
-- STRUCTURAL: column membership checked via array equality, not substring — avoids false
--             negatives when a short column name appears inside a longer indexed column name
--             (e.g. "user_id" inside "external_user_id").
WITH fk_columns AS (
    SELECT
        tc.table_schema,
        tc.table_name,
        kcu.column_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
      ON tc.constraint_name = kcu.constraint_name
     AND tc.table_schema = kcu.table_schema
    WHERE tc.constraint_type = 'FOREIGN KEY'
      AND tc.table_schema = 'public'          -- ILLUSTRATIVE: adjust schema filter
),
indexed_columns AS (
    SELECT
        t.relname  AS table_name,
        i.relname  AS index_name,
        a.attname  AS column_name
    FROM pg_class t
    JOIN pg_index ix ON t.oid = ix.indrelid
    JOIN pg_class i  ON i.oid = ix.indexrelid
    JOIN pg_attribute a
      ON a.attrelid = t.oid
     AND a.attnum = ANY(ix.indkey)
    JOIN pg_namespace n ON n.oid = t.relnamespace
    WHERE n.nspname = 'public'                -- ILLUSTRATIVE: adjust schema filter
      AND NOT ix.indisprimary
)
SELECT
    fk.table_name,
    fk.column_name,
    COALESCE(ic.index_name, '<missing index>') AS index_name
FROM fk_columns fk
LEFT JOIN indexed_columns ic
  ON ic.table_name  = fk.table_name
 AND ic.column_name = fk.column_name
ORDER BY fk.table_name, fk.column_name;
