-- ============================================================
-- Run in Supabase SQL Editor after 001_consent_retention.sql
-- ============================================================

-- Add confirmation code column (for pending check-in flow)
ALTER TABLE visitors ADD COLUMN IF NOT EXISTS confirmation_code TEXT;
