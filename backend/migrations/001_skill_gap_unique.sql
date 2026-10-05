SELECT user_id, cv_id, job_id, COUNT(*) AS duplicate_count
FROM skill_gaps
GROUP BY user_id, cv_id, job_id
HAVING COUNT(*) > 1;

ALTER TABLE skill_gaps
ADD CONSTRAINT uq_skill_gap_user_cv_job UNIQUE (user_id, cv_id, job_id);