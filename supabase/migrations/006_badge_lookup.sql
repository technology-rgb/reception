-- ============================================================
-- Visitor Badge Lookup (SECURITY DEFINER — bypasses RLS)
-- Run in Supabase SQL Editor after 005_returning_visitor_rpc.sql
-- ============================================================

-- Badge is valid from check-in until the visitor is checked out.
-- No date restriction — only verifies id + code + not yet checked out.
CREATE OR REPLACE FUNCTION get_visitor_pass(p_id BIGINT, p_code TEXT)
RETURNS TABLE(
  v_name       TEXT,
  v_host       TEXT,
  v_department TEXT,
  v_purpose    TEXT,
  v_check_in   TEXT
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT name, host, department, purpose, check_in
  FROM visitors
  WHERE id = p_id
    AND confirmation_code = p_code
    AND status != 'left';
$$;

GRANT EXECUTE ON FUNCTION get_visitor_pass(BIGINT, TEXT) TO anon;
