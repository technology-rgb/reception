-- ============================================================
-- Returning Visitor Profile Lookup
-- Run in Supabase SQL Editor after 004_rls.sql
-- ============================================================

-- SECURITY DEFINER lets this function bypass RLS so it can
-- read historical records for a given phone number.
-- Only returns the three safe fields needed for auto-fill —
-- no visit dates, host names, or status are exposed.
CREATE OR REPLACE FUNCTION get_visitor_profile(p_phone TEXT)
RETURNS TABLE(v_name TEXT, v_email TEXT, v_org TEXT)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT name, email, organization
  FROM visitors
  WHERE phone = p_phone
  ORDER BY id DESC
  LIMIT 1;
$$;

-- Allow the anonymous (unauthenticated) role to call this function
GRANT EXECUTE ON FUNCTION get_visitor_profile(TEXT) TO anon;
