-- Keep the validated job and UTC time of the latest successful match.
-- Legacy rows remain NULL; their original job data and match time are unknown.
ALTER TABLE skill_gaps
    ADD COLUMN job_snapshot JSON NULL DEFAULT NULL,
    ADD COLUMN matched_at DATETIME(6) NULL DEFAULT NULL;
