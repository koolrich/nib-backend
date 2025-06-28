CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY,
  cognito_sub TEXT UNIQUE NOT NULL,
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
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id),
  activation_code TEXT NOT NULL UNIQUE,
  invited_by UUID NOT NULL REFERENCES users(id),
  status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memberships (
  id UUID PRIMARY KEY,
  type TEXT CHECK (type IN ('family', 'single', 'student')),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);