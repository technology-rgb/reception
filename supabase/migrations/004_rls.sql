-- ============================================================
-- RLS — Visitor Management System
-- Run in Supabase SQL Editor (Dashboard → SQL Editor)
-- ============================================================

ALTER TABLE visitors ENABLE ROW LEVEL SECURITY;

-- ── Anon (mobile PWA, unauthenticated) ──────────────────────

-- Visitors can check themselves in.
-- Enforces: must be pending status, must have code + consent.
-- Prevents writing directly to inside/left or without consent.
CREATE POLICY "anon_insert_checkin" ON visitors
  FOR INSERT TO anon
  WITH CHECK (
    status = 'pending'
    AND confirmation_code IS NOT NULL
    AND consented_at IS NOT NULL
  );

-- Anon can read today's records only (needed for duplicate phone check).
-- Historical data (previous days) is not exposed to unauthenticated users.
CREATE POLICY "anon_read_today" ON visitors
  FOR SELECT TO anon
  USING (visit_date = CURRENT_DATE::text);

-- ── Authenticated admin (Supabase Auth JWT) ──────────────────

-- Admin has full access: read all records, confirm visitors,
-- check out, view logs across all dates.
CREATE POLICY "admin_full_access" ON visitors
  FOR ALL TO authenticated
  USING (true)
  WITH CHECK (true);

-- ── Verify policies are in place ─────────────────────────────
-- SELECT policyname, cmd, roles FROM pg_policies WHERE tablename = 'visitors';
