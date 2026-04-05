-- V4: Add date_joined to invites for legacy member onboarding

ALTER TABLE invites
    ADD COLUMN date_joined DATE;
