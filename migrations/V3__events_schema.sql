-- V3: Events, pledges and contributions schema

-- -------------------------
-- reference data
-- -------------------------
INSERT INTO reference_data (category, code, label, sort_order, is_active)
VALUES
    ('event_type',   'pledge',       'Pledge',       1, TRUE),
    ('event_type',   'contribution', 'Contribution', 2, TRUE),

    ('event_status', 'upcoming',  'Upcoming',  1, TRUE),
    ('event_status', 'completed', 'Completed', 2, TRUE),

    ('pledge_status', 'pledged',   'Pledged',   1, TRUE),
    ('pledge_status', 'cancelled', 'Cancelled', 2, TRUE)

ON CONFLICT (category, code) DO UPDATE
SET label      = EXCLUDED.label,
    sort_order = EXCLUDED.sort_order,
    is_active  = EXCLUDED.is_active;


-- -------------------------
-- events
-- -------------------------
CREATE TABLE events (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    title       TEXT NOT NULL,
    date        DATE NOT NULL,
    type        TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'upcoming',
    description TEXT,
    created_by  UUID NOT NULL REFERENCES members(id),
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW()
);


-- -------------------------
-- event_items (pledge events only)
-- -------------------------
CREATE TABLE event_items (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    event_id        UUID NOT NULL REFERENCES events(id),
    name            TEXT NOT NULL,
    quantity_needed DECIMAL NOT NULL,
    unit            TEXT NOT NULL,
    created_at      TIMESTAMP DEFAULT NOW()
);


-- -------------------------
-- pledges
-- -------------------------
CREATE TABLE pledges (
    id            UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    event_id      UUID NOT NULL REFERENCES events(id),
    member_id     UUID NOT NULL REFERENCES members(id),
    event_item_id UUID NOT NULL REFERENCES event_items(id),
    quantity      DECIMAL NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pledged',
    created_at    TIMESTAMP DEFAULT NOW(),
    updated_at    TIMESTAMP DEFAULT NOW(),
    CONSTRAINT pledges_member_item_uniq UNIQUE (member_id, event_item_id)
);


-- -------------------------
-- event_contributions
-- -------------------------
CREATE TABLE event_contributions (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    event_id    UUID NOT NULL REFERENCES events(id),
    member_id   UUID REFERENCES members(id),
    pledge_id   UUID REFERENCES pledges(id),
    amount      DECIMAL(10, 2) NOT NULL,
    recorded_by UUID NOT NULL REFERENCES members(id),
    received_at TIMESTAMP NOT NULL,
    note        TEXT,
    created_at  TIMESTAMP DEFAULT NOW()
);
