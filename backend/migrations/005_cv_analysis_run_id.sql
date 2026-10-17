-- Migration 005: Identify analysis attempts so obsolete tasks cannot publish results.
ALTER TABLE cvs ADD COLUMN analysis_run_id VARCHAR(32) NULL DEFAULT NULL;
