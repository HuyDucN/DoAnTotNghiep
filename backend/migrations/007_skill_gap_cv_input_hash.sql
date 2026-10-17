-- Identify the CV inputs used for the latest successful match.
-- Keep legacy results NULL because their original CV inputs are unknown.
ALTER TABLE skill_gaps
    ADD COLUMN cv_input_hash VARCHAR(64) NULL DEFAULT NULL;
