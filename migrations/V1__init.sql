CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS members (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  cognito_user_id TEXT UNIQUE NOT NULL,
  mobile TEXT NOT NULL UNIQUE,
  email TEXT,
  first_name NOT NULL TEXT,
  last_name NOT NULL TEXT,
  address_line1 TEXT,
  address_line2 TEXT,
  town TEXT,
  post_code TEXT,
  role NOT NULL TEXT CHECK (role IN ('admin', 'member')),
  membership_id UUID REFERENCES memberships(id),
  date_joined DATE,
  is_legacy BOOLEAN,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS invites (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  first_name NOT NULL TEXT,
  last_name NOT NULL TEXT,
  mobile TEXT NOT NULL
  activation_code TEXT NOT NULL UNIQUE,
  invited_by UUID NOT NULL REFERENCES members(id),
  relationship TEXT,
  status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memberships (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  membership_type NOT NULL TEXT
);

CREATE TABLE IF NOT EXISTS membership_periods (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  membership_id NOT NULL REFERENCES memberships(id),
  start_date NOT NULL DATE,
  end_date NOT NULL DATE,
  status NOT NULL TEXT
);

CREATE TABLE IF NOT EXISTS reference_data (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  category NOT NULL TEXT,
  code NOT NULL TEXT,
  label NOT NULL TEXT,
  sort_order INTEGER,
  is_active BOOLEAN
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