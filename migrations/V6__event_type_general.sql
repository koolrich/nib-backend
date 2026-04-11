-- V6: Add 'general' event type to reference data

INSERT INTO reference_data (category, code, label, sort_order, is_active)
VALUES ('event_type', 'general', 'General', 3, TRUE)
ON CONFLICT (category, code) DO UPDATE
SET label      = EXCLUDED.label,
    sort_order = EXCLUDED.sort_order,
    is_active  = EXCLUDED.is_active;
