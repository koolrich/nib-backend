-- V2: Registration schema updates

-- -------------------------
-- invites: add member_id, expires_at, created_at, is_legacy
-- -------------------------
ALTER TABLE invites
    ADD COLUMN member_id UUID REFERENCES members(id),
    ADD COLUMN expires_at TIMESTAMP,
    ADD COLUMN created_at TIMESTAMP DEFAULT NOW(),
    ADD COLUMN is_legacy BOOLEAN NOT NULL DEFAULT FALSE;


-- -------------------------
-- members: add profile and status fields
-- birthday_day/birthday_month added as nullable due to existing admin row;
-- enforce as mandatory at the application level for new registrations
-- -------------------------
ALTER TABLE members
    ADD COLUMN state_of_origin TEXT,
    ADD COLUMN lga TEXT,
    ADD COLUMN birthday_day INT,
    ADD COLUMN birthday_month INT,
    ADD COLUMN relationship_status TEXT,
    ADD COLUMN emergency_contact_name TEXT,
    ADD COLUMN emergency_contact_phone TEXT,
    ADD COLUMN status TEXT NOT NULL DEFAULT 'active';


-- -------------------------
-- memberships: add primary_member_id and timestamps
-- -------------------------
ALTER TABLE memberships
    ADD COLUMN primary_member_id UUID REFERENCES members(id),
    ADD COLUMN created_at TIMESTAMP DEFAULT NOW(),
    ADD COLUMN updated_at TIMESTAMP DEFAULT NOW();


-- -------------------------
-- membership_periods: add timestamps
-- -------------------------
ALTER TABLE membership_periods
    ADD COLUMN created_at TIMESTAMP DEFAULT NOW(),
    ADD COLUMN updated_at TIMESTAMP DEFAULT NOW();


-- -------------------------
-- invoice number sequence
-- -------------------------
CREATE SEQUENCE invoice_number_seq START 1;


-- -------------------------
-- invoices (new table)
-- -------------------------
CREATE TABLE invoices (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    membership_period_id UUID NOT NULL REFERENCES membership_periods(id),
    invoice_number TEXT UNIQUE NOT NULL,
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    amount_due DECIMAL(10, 2) NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);


-- -------------------------
-- payments (new table)
-- -------------------------
CREATE TABLE payments (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    invoice_id UUID NOT NULL REFERENCES invoices(id),
    amount DECIMAL(10, 2) NOT NULL,
    method TEXT NOT NULL,
    reference TEXT,
    received_by UUID NOT NULL REFERENCES members(id),
    received_at TIMESTAMP NOT NULL,
    note TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);


-- -------------------------
-- reference data: new categories
-- -------------------------
INSERT INTO reference_data (category, code, label, sort_order, is_active)
VALUES
    -- member status
    ('member_status', 'active',   'Active',   1, TRUE),
    ('member_status', 'inactive', 'Inactive', 2, TRUE),

    -- relationship status
    ('relationship_status', 'single',   'Single',   1, TRUE),
    ('relationship_status', 'married',  'Married',  2, TRUE),
    ('relationship_status', 'divorced', 'Divorced', 3, TRUE),
    ('relationship_status', 'widowed',  'Widowed',  4, TRUE),

    -- invoice status
    ('invoice_status', 'unpaid',  'Unpaid',           1, TRUE),
    ('invoice_status', 'partial', 'Partially Paid',   2, TRUE),
    ('invoice_status', 'paid',    'Paid',             3, TRUE),

    -- payment method
    ('payment_method', 'bank_transfer', 'Bank Transfer', 1, TRUE),
    ('payment_method', 'cash',          'Cash',          2, TRUE),
    ('payment_method', 'cheque',        'Cheque',        3, TRUE),
    ('payment_method', 'other',         'Other',         4, TRUE),

    -- member role
    ('member_role', 'member',    'Member',    1, TRUE),
    ('member_role', 'executive', 'Executive', 2, TRUE),
    ('member_role', 'admin',     'Admin',     3, TRUE),

    -- membership period status
    ('membership_period_status', 'active',  'Active',  1, TRUE),
    ('membership_period_status', 'expired', 'Expired', 2, TRUE)

ON CONFLICT (category, code) DO UPDATE
SET label      = EXCLUDED.label,
    sort_order = EXCLUDED.sort_order,
    is_active  = EXCLUDED.is_active;


-- -------------------------
-- membership_fees (new table)
-- effective_from allows fee changes over time;
-- current fee = latest row where effective_from <= today
-- -------------------------
CREATE TABLE membership_fees (
    id               UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    membership_type  TEXT NOT NULL,
    annual_fee       DECIMAL(10, 2) NOT NULL,
    effective_from   DATE NOT NULL,
    created_at       TIMESTAMP DEFAULT NOW(),
    CONSTRAINT membership_fees_type_date_uniq UNIQUE (membership_type, effective_from)
);

INSERT INTO membership_fees (membership_type, annual_fee, effective_from)
VALUES
    ('individual', 60.00, '2025-01-01'),
    ('family',    120.00, '2025-01-01');


-- -------------------------
-- organisation (new table)
-- single-row table for org bank details and config;
-- populate manually after migration — do not store sensitive values in source code
-- -------------------------
CREATE TABLE organisation (
    id             UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    account_name   TEXT,
    account_number TEXT,
    sort_code      TEXT,
    bank_name      TEXT,
    created_at     TIMESTAMP DEFAULT NOW(),
    updated_at     TIMESTAMP DEFAULT NOW()
);
