-- SQL schema reference: snapshot 2026-10-10 plus migrations 005-007 (2026-10-16).

-- Structure only: no account data, CV content or credentials.

-- Review reference; this file does not migrate existing tables.

SET NAMES utf8mb4;

USE `ai_cv_skillgap`;

-- Table: jobs

CREATE TABLE `jobs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `title` varchar(255) NOT NULL,
  `company` varchar(255) DEFAULT NULL,
  `location` varchar(255) DEFAULT NULL,
  `job_type` enum('full_time','part_time','internship','freelance') DEFAULT NULL,
  `level` enum('intern','fresher','junior','mid','senior','lead') DEFAULT NULL,
  `category` enum('backend','frontend','fullstack','data','ai_ml','devops','mobile','qa','other') DEFAULT NULL,
  `description` text,
  `salary_min` int DEFAULT NULL,
  `salary_max` int DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT NULL,
  `created_at` datetime DEFAULT (now()),
  `updated_at` datetime DEFAULT NULL,
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0',
  `deleted_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_jobs_id` (`id`),
  KEY `idx_jobs_is_deleted` (`is_deleted`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table: skills

CREATE TABLE `skills` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `normalized_name` varchar(255) NOT NULL,
  `category` enum('programming_language','framework','database','cloud','devops','ai_ml','soft_skill','tool','other') DEFAULT NULL,
  `description` text,
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0',
  `deleted_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_skills_name` (`name`),
  UNIQUE KEY `ix_skills_normalized_name` (`normalized_name`),
  KEY `ix_skills_id` (`id`),
  KEY `idx_skills_is_deleted` (`is_deleted`)
) ENGINE=InnoDB AUTO_INCREMENT=64 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table: users

CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `email` varchar(255) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `full_name` varchar(255) NOT NULL,
  `role` enum('user','admin','employer') NOT NULL DEFAULT 'user',
  `is_active` tinyint(1) DEFAULT NULL,
  `created_at` datetime DEFAULT (now()),
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_users_email` (`email`),
  KEY `ix_users_id` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table: cvs

CREATE TABLE `cvs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `filename` varchar(255) NOT NULL,
  `file_path` varchar(500) NOT NULL,
  `file_size` int DEFAULT NULL,
  `status` enum('uploaded','processing','analyzed','failed') NOT NULL,
  `raw_text` text,
  `ai_analysis` json DEFAULT NULL,
  `created_at` datetime DEFAULT (now()),
  `updated_at` datetime DEFAULT NULL,
  `file_hash` varchar(64) DEFAULT NULL,
  `analysis_run_id` varchar(32) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `ix_cvs_id` (`id`),
  KEY `idx_cvs_file_hash` (`file_hash`),
  CONSTRAINT `cvs_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=28 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table: job_skills

CREATE TABLE `job_skills` (
  `id` int NOT NULL AUTO_INCREMENT,
  `job_id` int NOT NULL,
  `skill_id` int NOT NULL,
  `is_required` tinyint(1) DEFAULT NULL,
  `importance` enum('high','medium','low') DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `job_id` (`job_id`),
  KEY `skill_id` (`skill_id`),
  KEY `ix_job_skills_id` (`id`),
  CONSTRAINT `job_skills_ibfk_1` FOREIGN KEY (`job_id`) REFERENCES `jobs` (`id`) ON DELETE CASCADE,
  CONSTRAINT `job_skills_ibfk_2` FOREIGN KEY (`skill_id`) REFERENCES `skills` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=39 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table: profiles

CREATE TABLE `profiles` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `phone` varchar(20) DEFAULT NULL,
  `location` varchar(255) DEFAULT NULL,
  `job_title` varchar(255) DEFAULT NULL,
  `bio` text,
  `avatar_url` varchar(500) DEFAULT NULL,
  `linkedin_url` varchar(500) DEFAULT NULL,
  `github_url` varchar(500) DEFAULT NULL,
  `created_at` datetime DEFAULT (now()),
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  KEY `ix_profiles_id` (`id`),
  CONSTRAINT `profiles_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table: cv_skills

CREATE TABLE `cv_skills` (
  `id` int NOT NULL AUTO_INCREMENT,
  `cv_id` int NOT NULL,
  `skill_id` int NOT NULL,
  `proficiency_level` enum('beginner','intermediate','advanced','expert') DEFAULT NULL,
  `years_experience` float DEFAULT NULL,
  `source` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `cv_id` (`cv_id`),
  KEY `skill_id` (`skill_id`),
  KEY `ix_cv_skills_id` (`id`),
  CONSTRAINT `cv_skills_ibfk_1` FOREIGN KEY (`cv_id`) REFERENCES `cvs` (`id`) ON DELETE CASCADE,
  CONSTRAINT `cv_skills_ibfk_2` FOREIGN KEY (`skill_id`) REFERENCES `skills` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=120 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table: skill_gaps

CREATE TABLE `skill_gaps` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `cv_id` int NOT NULL,
  `job_id` int NOT NULL,
  `match_score` float NOT NULL,
  `matched_skills` json DEFAULT NULL,
  `missing_skills` json DEFAULT NULL,
  `weak_skills` json DEFAULT NULL,
  `ai_recommendation` text,
  `job_snapshot` json DEFAULT NULL,
  `cv_input_hash` varchar(64) DEFAULT NULL,
  `matched_at` datetime(6) DEFAULT NULL,
  `created_at` datetime DEFAULT (now()),
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `cv_id` (`cv_id`),
  KEY `job_id` (`job_id`),
  KEY `ix_skill_gaps_id` (`id`),
  CONSTRAINT `skill_gaps_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `skill_gaps_ibfk_2` FOREIGN KEY (`cv_id`) REFERENCES `cvs` (`id`) ON DELETE CASCADE,
  CONSTRAINT `skill_gaps_ibfk_3` FOREIGN KEY (`job_id`) REFERENCES `jobs` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
