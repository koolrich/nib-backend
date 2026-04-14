-- V7: Password reset tokens

CREATE TABLE password_reset_tokens (
    id         UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    member_id  UUID NOT NULL REFERENCES members(id),
    code_hash  TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used_at    TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
