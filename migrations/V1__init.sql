CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS memberships (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  membership_type TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS members (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  cognito_user_id TEXT UNIQUE NOT NULL,
  mobile TEXT UNIQUE NOT NULL,
  email TEXT UNIQUE NOT NULL,
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  address_line1 TEXT,
  address_line2 TEXT,
  town TEXT,
  post_code TEXT,
  member_role TEXT NOT NULL,
  membership_id UUID REFERENCES memberships(id),
  date_joined DATE NOT NULL,
  is_legacy BOOLEAN,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS invites (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  mobile TEXT NOT NULL,
  activation_code TEXT UNIQUE NOT NULL,
  invited_by UUID REFERENCES members(id),
  relationship TEXT NOT NULL,
  status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS membership_periods (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  membership_id UUID REFERENCES memberships(id),
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reference_data (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  category TEXT NOT NULL,
  code TEXT NOT NULL,
  label TEXT NOT NULL,
  sort_order INTEGER,
  is_active BOOLEAN,
  CONSTRAINT reference_data_category_code_uniq UNIQUE (category, code)
);

INSERT INTO reference_data (category, code, label, sort_order, is_active)
VALUES
    ('relationship', 'spouse', 'Spouse', 1, TRUE),
    ('relationship', 'other', 'Other', 2, TRUE),
    ('membership_type', 'individual', 'Individual', 1, TRUE),
    ('membership_type', 'family', 'Family', 2, TRUE),
    ('invite_status', 'pending', 'Invite Pending', 1, TRUE),
    ('invite_status', 'sent', 'Invite Sent', 2, TRUE),
    ('invite_status', 'used', 'Invite Used', 3, TRUE),
    ('invite_status', 'expired', 'Expired', 4, TRUE),
    ('invite_status', 'cancelled', 'Cancelled', 5, TRUE)
ON CONFLICT (category, code) DO UPDATE
SET label = EXCLUDED.label,
    sort_order = EXCLUDED.sort_order,
    is_active = EXCLUDED.is_active;
