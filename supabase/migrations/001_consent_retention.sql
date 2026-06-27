-- ============================================================
-- Run in Supabase SQL Editor: Dashboard → SQL Editor → New Query
-- ============================================================

-- 1. Add consent timestamp column
ALTER TABLE visitors ADD COLUMN IF NOT EXISTS consented_at TIMESTAMPTZ;

-- 2. Enable pg_cron extension first:
--    Dashboard → Database → Extensions → search "pg_cron" → Enable
--    Then run the line below.

-- 3. DPDP retention: auto-delete visitor records older than 30 days
--    Runs at 01:00 UTC every night.
SELECT cron.schedule(
  'delete-old-visitors',
  '0 1 * * *',
  $$
    DELETE FROM visitors
    WHERE visit_date < (CURRENT_DATE - INTERVAL '30 days');
  $$
);
