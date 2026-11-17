-- MySQL dump 10.13  Distrib 8.0.45, for Linux (x86_64)
--
-- Host: host.docker.internal    Database: ai_cv_skillgap
-- ------------------------------------------------------
-- Server version	8.0.43

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `alembic_version`
--

DROP TABLE IF EXISTS `alembic_version`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `alembic_version` (
  `version_num` varchar(32) NOT NULL,
  PRIMARY KEY (`version_num`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `alembic_version`
--

LOCK TABLES `alembic_version` WRITE;
/*!40000 ALTER TABLE `alembic_version` DISABLE KEYS */;
INSERT INTO `alembic_version` VALUES ('000000000005');
/*!40000 ALTER TABLE `alembic_version` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `audit_logs`
--

DROP TABLE IF EXISTS `audit_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `actor_id` int DEFAULT NULL,
  `action` varchar(64) NOT NULL,
  `target_type` varchar(32) DEFAULT NULL,
  `target_id` int DEFAULT NULL,
  `detail` json DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_audit_logs_action` (`action`),
  KEY `ix_audit_logs_actor_id` (`actor_id`),
  KEY `ix_audit_logs_id` (`id`),
  CONSTRAINT `audit_logs_ibfk_1` FOREIGN KEY (`actor_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `audit_logs`
--

LOCK TABLES `audit_logs` WRITE;
/*!40000 ALTER TABLE `audit_logs` DISABLE KEYS */;
INSERT INTO `audit_logs` VALUES (1,1,'recruiter.verify','user',5,'{\"is_verified\": true}','2026-10-20 11:14:07'),(2,1,'applicant.review','skill_gap',16,'{\"job_id\": 4, \"review_status\": \"viewed\"}','2026-10-20 11:18:53'),(3,1,'applicant.review','skill_gap',16,'{\"job_id\": 4, \"review_status\": \"new\"}','2026-10-20 11:18:55'),(4,5,'job.create','job',9,'{\"title\": \"fdgf\"}','2026-10-20 11:20:06'),(5,5,'job.update','job',9,'{\"fields\": [\"category\", \"company\", \"description\", \"job_type\", \"level\", \"location\", \"salary_max\", \"salary_min\", \"title\"]}','2026-10-20 11:21:50'),(6,5,'applicant.review','skill_gap',17,'{\"job_id\": 9, \"review_status\": \"shortlisted\"}','2026-10-20 11:22:19'),(7,5,'applicant.review','skill_gap',17,'{\"job_id\": 9, \"review_status\": \"hired\"}','2026-10-20 11:22:23'),(8,5,'applicant.review','skill_gap',17,'{\"job_id\": 9, \"review_status\": \"new\"}','2026-10-20 11:22:25'),(9,1,'job.delete','job',9,'null','2026-10-20 11:24:10'),(10,1,'recruiter.verify','user',5,'{\"is_verified\": false}','2026-10-20 11:24:38'),(11,1,'recruiter.verify','user',5,'{\"is_verified\": true}','2026-10-20 11:24:39'),(12,1,'recruiter.verify','user',5,'{\"is_verified\": false}','2026-10-20 11:24:43'),(13,1,'recruiter.verify','user',5,'{\"is_verified\": true}','2026-10-20 11:24:45');
/*!40000 ALTER TABLE `audit_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `cv_skills`
--

DROP TABLE IF EXISTS `cv_skills`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
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
) ENGINE=InnoDB AUTO_INCREMENT=164 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `cv_skills`
--

LOCK TABLES `cv_skills` WRITE;
/*!40000 ALTER TABLE `cv_skills` DISABLE KEYS */;
INSERT INTO `cv_skills` VALUES (123,28,4,'intermediate',1,'ai_extracted'),(124,28,5,'intermediate',1,'ai_extracted'),(125,28,34,'beginner',0,'ai_extracted'),(126,28,35,'beginner',0,'ai_extracted'),(127,28,36,'intermediate',1,'ai_extracted'),(128,28,37,'intermediate',1,'ai_extracted'),(129,28,38,'beginner',0,'ai_extracted'),(130,28,12,'intermediate',1,'ai_extracted'),(131,28,39,'intermediate',1,'ai_extracted'),(132,28,42,'intermediate',1,'ai_extracted'),(133,28,43,'beginner',0,'ai_extracted'),(134,28,14,'beginner',0,'ai_extracted'),(136,29,4,'intermediate',2,'ai_extracted'),(137,29,7,'intermediate',2,'ai_extracted'),(138,29,74,'intermediate',1,'ai_extracted'),(139,29,37,'intermediate',1,'ai_extracted'),(140,29,42,'intermediate',1,'ai_extracted'),(141,29,43,'beginner',0,'ai_extracted'),(142,29,75,'beginner',0,'ai_extracted'),(143,29,12,'intermediate',1,'ai_extracted'),(144,29,39,'intermediate',1,'ai_extracted'),(146,30,3,'beginner',0,'ai_extracted'),(147,30,6,'beginner',0,'ai_extracted'),(148,30,76,'beginner',0,'ai_extracted'),(149,30,74,'beginner',0,'ai_extracted'),(150,30,42,'beginner',0,'ai_extracted'),(151,30,19,'beginner',0,'ai_extracted'),(152,31,2,'intermediate',1,'ai_extracted'),(153,31,3,'intermediate',1,'ai_extracted'),(154,31,4,'intermediate',1,'ai_extracted'),(155,31,5,'intermediate',1,'ai_extracted'),(156,31,6,'intermediate',1,'ai_extracted'),(157,31,7,'intermediate',1,'ai_extracted'),(158,31,15,'intermediate',1,'ai_extracted'),(159,31,12,'intermediate',1,'ai_extracted'),(160,31,10,'intermediate',1,'ai_extracted'),(161,31,11,'intermediate',1,'ai_extracted'),(162,31,14,'intermediate',0,'manual'),(163,31,43,'intermediate',1,'manual');
/*!40000 ALTER TABLE `cv_skills` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `cvs`
--

DROP TABLE IF EXISTS `cvs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
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
) ENGINE=InnoDB AUTO_INCREMENT=32 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `cvs`
--

LOCK TABLES `cvs` WRITE;
/*!40000 ALTER TABLE `cvs` DISABLE KEYS */;
INSERT INTO `cvs` VALUES (28,4,'Huynh-Tran-Son-Sanh-TopCV.vn-160426.00202.pdf','uploads/cvs\\374fa467fb6643be9e529e68bd61fe93.pdf',216953,'analyzed','Huỳnh Trần Sơn Sanh\nLập trình viên\n\n0799392717\n\nhuynhsanh2k4@gmail.com\n\nĐiện Bàn Bắc, Đà Nẵng\n📅\n12/12/2004\n👤\nNam\nMục tiêu nghề nghiệp\nNgắn hạn: Tìm kiếm cơ hội thực tập\ntại môi trường chuyên nghiệp để áp\ndụng kiến thức nền tảng về lập\ntrình (như Node.js, Python, java...)\nvào dự án thực tế, làm quen với quy\ntrình phát triển phần mềm của\ndoanh nghiệp.\nDài hạn: Trở thành một lập trình\nviên Full-stack cứng cáp, có khả\nnăng đóng góp trực tiếp vào core\nproduct của công ty trong 1-2 năm\ntới.\nKỹ năng\nKỹ năng giao tiếp\nKỹ năng đàm phán\nKỹ năng thuyết trình\n💡\nHọc vấn\nCông nghệ thông tin\n2022 - 2027\nTrường Đại học Kiến Trúc Đà Nẵng\n• Chưa tốt nghiệp\n• GPA hiện tại: 3.0/4.0\n✏\nKỹ năng chuyên môn\nNgôn ngữ lập trình: Java, Python, Dart, PHP.\nFramework/Thư viện: ReactJS, Django, VueJS.\nDatabase: MySQL, PostgreSQL.\nTesting: Pytest, Robot Framework, thiết kế Test Case thủ công.\nCông cụ & Môi trường: Git, Docker, Linux (Terminal), Maven, Android\nStudio.\n✏\nDự án nổi bật\nDự án Chatbot AI\n• Mô tả: Xây dựng hệ thống chatbot hỗ trợ xử lý ngôn ngữ tự nhiên và\nnhận diện hình ảnh.\n• Công nghệ: Django (Backend), TensorFlow, Roboflow (Computer\nVision), PostgreSQL.\nWeb Quản lý Sự Kiện Nội Bộ\n• Mô tả: Phát triển nền tảng quản lý sự kiện giúp tự động hóa toàn bộ quy\ntrình từ đăng ký, phê duyệt đến điều phối nhân sự trong tổ chức.\n• Công nghệ sử dụng: ReactJS, Node.js (Express), MySQL.\nHệ thống Quản lý Spa\n• Mô tả: Hệ thống quản lý dịch vụ, lịch hẹn và doanh thu cho Spa.\n• Công nghệ: Java (Eclipse), JDBC/Hibernate, MySQL.\n🖹\nChứng chỉ\n2022\nTin Học Văn Phòng\n2024\nTiếng Anh cơ bản\n⭐\nHoạt động\nThành viên\n2024 - 2026\nTHAM GIA CÂU LẠC BỘ GG CỦA TRƯỜNG\n• Tham gia trao đổi kiến thức chuyên ngành\n• Tham gia các khóa học lập trình cơ bản và nâng cao do CLB tổ chức để\nhiểu sâu hơn và nâng cao kiến thức, dự án sát với thực tế.\nSở thích\n●\nThể thao\n●\nDu lịch\n© topcv.vn','{\"email\": \"[EMAIL]\", \"phone\": \"[PHONE]\", \"skills\": [{\"name\": \"Python\", \"category\": \"programming_language\", \"years_experience\": 1.0, \"proficiency_level\": \"intermediate\"}, {\"name\": \"Java\", \"category\": \"programming_language\", \"years_experience\": 1.0, \"proficiency_level\": \"intermediate\"}, {\"name\": \"Dart\", \"category\": \"programming_language\", \"years_experience\": 0.0, \"proficiency_level\": \"beginner\"}, {\"name\": \"PHP\", \"category\": \"programming_language\", \"years_experience\": 0.0, \"proficiency_level\": \"beginner\"}, {\"name\": \"ReactJS\", \"category\": \"framework\", \"years_experience\": 1.0, \"proficiency_level\": \"intermediate\"}, {\"name\": \"Django\", \"category\": \"framework\", \"years_experience\": 1.0, \"proficiency_level\": \"intermediate\"}, {\"name\": \"VueJS\", \"category\": \"framework\", \"years_experience\": 0.0, \"proficiency_level\": \"beginner\"}, {\"name\": \"MySQL\", \"category\": \"database\", \"years_experience\": 1.0, \"proficiency_level\": \"intermediate\"}, {\"name\": \"PostgreSQL\", \"category\": \"database\", \"years_experience\": 1.0, \"proficiency_level\": \"intermediate\"}, {\"name\": \"Git\", \"category\": \"tool\", \"years_experience\": 1.0, \"proficiency_level\": \"intermediate\"}, {\"name\": \"Docker\", \"category\": \"cloud\", \"years_experience\": 0.0, \"proficiency_level\": \"beginner\"}, {\"name\": \"Linux\", \"category\": \"devops\", \"years_experience\": 0.0, \"proficiency_level\": \"beginner\"}], \"summary\": \"Lập trình viên với kiến thức nền tảng về lập trình và mong muốn trở thành lập trình viên Full-stack.\", \"location\": \"Điện Bàn Bắc, Đà Nẵng\", \"projects\": [{\"url\": \"\", \"name\": \"Dự án Chatbot AI\", \"description\": \"Xây dựng hệ thống chatbot hỗ trợ xử lý ngôn ngữ tự nhiên và nhận diện hình ảnh.\", \"technologies\": [\"Django\", \"TensorFlow\", \"Roboflow\", \"PostgreSQL\"]}, {\"url\": \"\", \"name\": \"Web Quản lý Sự Kiện Nội Bộ\", \"description\": \"Phát triển nền tảng quản lý sự kiện giúp tự động hóa toàn bộ quy trình từ đăng ký, phê duyệt đến điều phối nhân sự trong tổ chức.\", \"technologies\": [\"ReactJS\", \"Node.js\", \"MySQL\"]}, {\"url\": \"\", \"name\": \"Hệ thống Quản lý Spa\", \"description\": \"Hệ thống quản lý dịch vụ, lịch hẹn và doanh thu cho Spa.\", \"technologies\": [\"Java\", \"JDBC\", \"Hibernate\", \"MySQL\"]}], \"education\": [{\"gpa\": 3.0, \"degree\": \"Chưa tốt nghiệp\", \"end_year\": 2023, \"start_year\": 2019, \"institution\": \"Trường Đại học Kiến Trúc Đà Nẵng\", \"field_of_study\": \"Công nghệ thông tin\"}], \"full_name\": \"Huỳnh Trần Sơn Sanh\", \"experience\": [], \"certificates\": [{\"name\": \"Tin Học Văn Phòng\", \"year\": 2022, \"issuer\": \"\"}, {\"name\": \"Tiếng Anh cơ bản\", \"year\": 2024, \"issuer\": \"\"}], \"total_experience_years\": 0.0}','2026-10-10 18:21:59','2026-10-10 18:22:14','cf782a5a509aff581d6b553b939d3c0babcb2321dbf8eb80664f17b2aeb92907',NULL),(29,4,'BUI-VAN-DAT1-TopCV.vn-150426.234004.pdf','uploads/cvs\\8e7ade1cfdd34bd5bc8e893330304e7d.pdf',203475,'analyzed','BÙI VẠN ĐẠT\nLập trình viên\n\n0903518371\n\nbuid8181@gmail.com\n\nQuận Hải Châu,TP.Đà Nẵng\n📅\n20/09/2004\n👤\nNam\nMục tiêu nghề nghiệp\nSinh viên năm 4 ngành Công nghệ\nthông tin tại Đại học Kiến trúc Đà\nNẵng, định hướng trở thành Front-\nend Developer.\nMong muốn được tham gia chương\ntrình thực tập tại INTERN WEB\nDEVELOPER để áp dụng kiến thức\nđã học vào dự án thực tế, nâng cao\nkỹ năng lập trình, làm việc nhóm và\ntích lũy kinh nghiệm trong môi\ntrường chuyên nghiệp.\nTrong dài hạn, hướng tới trở thành\nlập trình viên có khả năng phát\ntriển sản phẩm chất lượng và mang\nlại giá trị cho doanh nghiệp.\nKỹ năng\nKỹ năng giao tiếp\nKỹ năng đàm phán\nKỹ năng thuyết trình\n💡\nHọc vấn\nChuyên ngành: Công nghệ thông tin\n2022 - 2026\nĐại học Kiến trúc Đà Nẵng\nSinh viên năm 4 (Chưa tốt nghiệp)\nGPA: (3.1)\nCác môn tiêu biểu: Cấu trúc dữ liệu & giải thuật, Lập trình Web, Cơ sở dữ\nliệu, OOP\n\nKinh nghiệm làm việc\nFront End Developer\n2022 - 2026\nĐại học Kiến trúc Đà Nẵng\nHiện chưa có kinh nghiệm làm việc chính thức.\nTuy nhiên đã:\n• Tham gia làm bài tập nhóm tại trường\n• Tự xây dựng các dự án cá nhân\n• Làm quen với quy trình Git và làm việc nhóm cơ bản\n✏\nKỹ Năng Chuyên Môn (Technical Skills)\nNgôn ngữ: Java (Core), Python (Scripting & Data), SQL.\nFramework/Library: Spring Boot, Django, Pandas, NumPy.\nCông cụ: Git (GitHub/GitLab), Docker (Cơ bản), Postman.\nCơ sở dữ liệu: MySQL, PostgreSQL.\n✏\nDự Án Tiêu Biểu(Key Projects)\n2022: Website Kinh Doanh Đồ Câu(Java Spring Boot)\n2022: Đồ án Cơ sở dữ liệu – Xây dựng hệ thống quản lý Đồ Nội Thất\n2026: Đồ án chuyên ngành công nghệ phần mềm – Xây dựng Website\nquản lý tổ chức sự kiện nội bộ\n🖹\nChứng chỉ\n2024\nTiếng Anh Cơ Bản\n2022\nTin Học Văn Phòng\n⭐\nHoạt động\nThành viên\n2015 - 2017\nTHAM GIA CÂU LẠC BỘ HIT CỦA TRƯỜNG\n• Tham gia trao đổi kiến thức chuyên ngành\n• Tham gia các khóa học lập trình cơ bản và nâng cao do CLB tổ chức để\nhiểu sâu hơn và nâng cao kiến thức, dự án sát với thực tế.\n© topcv.vn','{\"email\": \"[EMAIL]\", \"phone\": \"[PHONE]\", \"skills\": [{\"name\": \"Java\", \"category\": \"programming_language\", \"years_experience\": 2.0, \"proficiency_level\": \"intermediate\"}, {\"name\": \"Python\", \"category\": \"programming_language\", \"years_experience\": 2.0, \"proficiency_level\": \"intermediate\"}, {\"name\": \"SQL\", \"category\": \"database\", \"years_experience\": 2.0, \"proficiency_level\": \"intermediate\"}, {\"name\": \"Spring Boot\", \"category\": \"framework\", \"years_experience\": 1.0, \"proficiency_level\": \"intermediate\"}, {\"name\": \"Django\", \"category\": \"framework\", \"years_experience\": 1.0, \"proficiency_level\": \"intermediate\"}, {\"name\": \"Git\", \"category\": \"devops\", \"years_experience\": 1.0, \"proficiency_level\": \"intermediate\"}, {\"name\": \"Docker\", \"category\": \"cloud\", \"years_experience\": 0.0, \"proficiency_level\": \"beginner\"}, {\"name\": \"Postman\", \"category\": \"tool\", \"years_experience\": 0.0, \"proficiency_level\": \"beginner\"}, {\"name\": \"MySQL\", \"category\": \"database\", \"years_experience\": 1.0, \"proficiency_level\": \"intermediate\"}, {\"name\": \"PostgreSQL\", \"category\": \"database\", \"years_experience\": 1.0, \"proficiency_level\": \"intermediate\"}], \"summary\": \"Sinh viên năm 4 ngành Công nghệ thông tin tại Đại học Kiến trúc Đà Nẵng, định hướng trở thành Front-end Developer.\", \"location\": \"Quận Hải Châu,TP.Đà Nẵng\", \"projects\": [{\"url\": \"\", \"name\": \"Website Kinh Doanh Đồ Câu\", \"description\": \"Dự án xây dựng website kinh doanh đồ câu sử dụng Java Spring Boot.\", \"technologies\": [\"Java\", \"Spring Boot\"]}, {\"url\": \"\", \"name\": \"Hệ thống quản lý Đồ Nội Thất\", \"description\": \"Đồ án Cơ sở dữ liệu – Xây dựng hệ thống quản lý Đồ Nội Thất.\", \"technologies\": [\"SQL\"]}, {\"url\": \"\", \"name\": \"Website quản lý tổ chức sự kiện nội bộ\", \"description\": \"Đồ án chuyên ngành công nghệ phần mềm – Xây dựng Website quản lý tổ chức sự kiện nội bộ.\", \"technologies\": [\"Web Development\"]}], \"education\": [{\"gpa\": 3.1, \"degree\": \"Cử nhân\", \"end_year\": 2023, \"start_year\": 2019, \"institution\": \"Đại học Kiến trúc Đà Nẵng\", \"field_of_study\": \"Công nghệ thông tin\"}], \"full_name\": \"BÙI VẠN ĐẠT\", \"experience\": [{\"company\": \"Đại học Kiến trúc Đà Nẵng\", \"end_date\": \"Present\", \"position\": \"Front End Developer\", \"start_date\": \"MM/YYYY\", \"description\": \"Hiện chưa có kinh nghiệm làm việc chính thức. Tuy nhiên đã tham gia làm bài tập nhóm tại trường, tự xây dựng các dự án cá nhân, làm quen với quy trình Git và làm việc nhóm cơ bản.\", \"skills_used\": [\"Java\", \"Python\", \"SQL\", \"Spring Boot\", \"Django\", \"Git\"]}], \"certificates\": [{\"name\": \"Tiếng Anh Cơ Bản\", \"year\": 2024, \"issuer\": \"Tổ chức cấp\"}, {\"name\": \"Tin Học Văn Phòng\", \"year\": 2022, \"issuer\": \"Tổ chức cấp\"}], \"total_experience_years\": 0.0}','2026-10-10 18:27:28','2026-10-10 18:27:49','f39af3705af75f51fa481ebd373414d43c2069da3f40b10f4290c83bd6c30353',NULL),(30,4,'Pham-Thanh-Nhat-TopCV.vn-150426.235527.pdf','uploads/cvs\\212f5bb3c2204eeda3e295b87b38f63e.pdf',198745,'analyzed','Phạm Thanh Nhất\nLập trình viên\n\n0329706334\n\nnhatdinhtan654@gmail.com\n\nQuận Hải Châu,TP.Đà Nẵng\n📅\n02/12/2004\n👤\nNam\nMục tiêu nghề nghiệp\nMong muốn được tham gia vị trí\nthực tập sinh trong lĩnh vực Công\nnghệ thông tin để áp dụng kiến\nthức vào thực tế và nâng cao kỹ\nnăng lập trình. Đồng thời, hướng\nđến việc học hỏi nhanh, thích nghi\ntốt và hoàn thành hiệu quả các\nnhiệm vụ được giao.\nKỹ năng\nNgôn ngữ lập trình: (Java / C# /\nJavaScript / …)\nFramework: (NodeJS / Spring Boot\n/ Flutter…)\nCông cụ: Git, VS Code\nSở thích\n●\nĐọc sách\n●\nNấu ăn\n💡\nHọc vấn\nCông nghệ thông tin\n2022 - 2026\nĐại Học Kiến Trúc Đà Nẵng\n• Chưa tốt nghiệp\n• Đạt học bổng 2024\n\nKinh nghiệm làm việc\nFront End Developer\n2022 - 2026\nĐại học kiến Trúc Đà Nẵng\nMặc dù chưa có kinh nghiệm làm việc chính thức, tôi đã tích lũy được kinh\nnghiệm thực tế thông qua học tập và các dự án cá nhân:\n• Tham gia các dự án nhóm, phối hợp phân tích yêu cầu, thiết kế và hoàn\nthành sản phẩm đúng tiến độ\n• Tự phát triển các dự án cá nhân nhằm nâng cao kỹ năng lập trình và tư\nduy giải quyết vấn đề\n• Sử dụng Git để quản lý mã nguồn và hỗ trợ làm việc nhóm\n• Làm quen với quy trình phát triển phần mềm: phân tích, thiết kế, lập\ntrình và kiểm thử\nDự Án\n2024 - 2026\nDự án cá nhân :\nWebsite Thương mại điện tử\n03/2026 – 04/2026\n• Xây dựng website bán hàng trên WordPress, tùy chỉnh giao diện và chức\nnăng\n• Cấu hình môi trường Apache, MySQL trên Linux/WSL\n• Cài đặt và tùy chỉnh plugin phục vụ chức năng bán hàng\nMobile App & UI/UX Design\n02/2026 – 04/2026\n• Thiết kế UI/UX cho ứng dụng Web và Mobile bằng Figma\n• Xây dựng Wireframe, Prototype và hoàn thiện giao diện\n• Đảm bảo tính nhất quán và trải nghiệm người dùng\n🏆\nDanh hiệu và giải thưởng\n2023\nHọc sinh giỏi của trường\n🖹\nChứng chỉ\n2024\nTiếng Anh Cơ Bản\n2024\nTin Học Cơ Bản\n⭐\nHoạt động\nThành viên\n2023 - 2024\nTHAM GIA CÂU LẠC BỘ HIT CỦA TRƯỜNG\n• Tham gia trao đổi kiến thức chuyên ngành\n© topcv.vn','{\"email\": \"[EMAIL]\", \"phone\": \"[PHONE]\", \"skills\": [{\"name\": \"Java\", \"category\": \"programming_language\", \"years_experience\": 0.0, \"proficiency_level\": \"beginner\"}, {\"name\": \"C#\", \"category\": \"programming_language\", \"years_experience\": 0.0, \"proficiency_level\": \"beginner\"}, {\"name\": \"JavaScript\", \"category\": \"programming_language\", \"years_experience\": 0.0, \"proficiency_level\": \"beginner\"}, {\"name\": \"NodeJS\", \"category\": \"framework\", \"years_experience\": 0.0, \"proficiency_level\": \"beginner\"}, {\"name\": \"Spring Boot\", \"category\": \"framework\", \"years_experience\": 0.0, \"proficiency_level\": \"beginner\"}, {\"name\": \"Git\", \"category\": \"tool\", \"years_experience\": 0.0, \"proficiency_level\": \"beginner\"}, {\"name\": \"VS Code\", \"category\": \"tool\", \"years_experience\": 0.0, \"proficiency_level\": \"beginner\"}], \"summary\": \"Mong muốn được tham gia vị trí thực tập sinh trong lĩnh vực Công nghệ thông tin để áp dụng kiến thức vào thực tế và nâng cao kỹ năng lập trình.\", \"location\": \"Quận Hải Châu,TP.Đà Nẵng\", \"projects\": [{\"url\": null, \"name\": \"Website Thương mại điện tử\", \"description\": \"Xây dựng website bán hàng trên WordPress, tùy chỉnh giao diện và chức năng.\", \"technologies\": [\"WordPress\", \"Apache\", \"MySQL\", \"Linux\"]}, {\"url\": null, \"name\": \"Mobile App & UI/UX Design\", \"description\": \"Thiết kế UI/UX cho ứng dụng Web và Mobile bằng Figma.\", \"technologies\": [\"Figma\"]}], \"education\": [{\"gpa\": null, \"degree\": \"Chưa tốt nghiệp\", \"end_year\": 2024, \"start_year\": 2019, \"institution\": \"Đại Học Kiến Trúc Đà Nẵng\", \"field_of_study\": \"Công nghệ thông tin\"}], \"full_name\": \"Phạm Thanh Nhất\", \"experience\": [{\"company\": \"Đại học kiến Trúc Đà Nẵng\", \"end_date\": \"Present\", \"position\": \"Front End Developer\", \"start_date\": \"MM/YYYY\", \"description\": \"Mặc dù chưa có kinh nghiệm làm việc chính thức, tôi đã tích lũy được kinh nghiệm thực tế thông qua học tập và các dự án cá nhân.\", \"skills_used\": [\"Java\", \"JavaScript\", \"Git\"]}], \"certificates\": [{\"name\": \"Tiếng Anh Cơ Bản\", \"year\": 2024, \"issuer\": null}, {\"name\": \"Tin Học Cơ Bản\", \"year\": 2024, \"issuer\": null}], \"total_experience_years\": 0.0}','2026-10-10 18:27:58','2026-10-10 18:28:05','80a9c39a3aa35f5135e435a53f39f32c108bcb1d227f5df5398c5ca968622b1c',NULL),(31,4,'NguyenHuyDucCV.pdf','uploads/cvs\\a5608cfda93e488186394cfa2d875562.pdf',263533,'analyzed','Mục Tiêu Nghề Nghiệp\nDự Án & Kinh Nghiệm\n2/2026 - 4/2026\n10/2024 - 12/2024\nNGUYỄN HUY ĐỨC\nINTERN / FRESHER SOFTWARE DEVELOPER\nHọc Vấn\nEducation\nSinh viên năm 4 ngành Công nghệ Thông tin với nền tảng kỹ thuật vững chắc và kinh nghiệm thực tế trong phát\ntriển phần mềm, ứng\ndụng web và triển khai thuật toán. Mong muốn tìm kiếm cơ hội Intern / Fresher Software Developer để ứng dụng\ncác kỹ năng (C++, C#, Python, Java, JavaScript, SQL) vào môi trường thực tế. Khát khao học hỏi công nghệ mới,\nhướng tới mục tiêu phát triển chuyên sâu trong mảng Web\nDevelopment và Software Development.\nWebsite Thương mại điện tử\n3/2026 - 4/2026\nMobile & Web App\nỨng dụng Chat Client-Server\nTriển khai WordPress & Server Local\nUI/UX Designer (Figma)\nLập trình C# WinForms\nTriển khai website bán hàng hoàn chỉnh trên nền tảng WordPress.\nCấu hình hệ thống Apache và MySQL trên môi trường Linux/WSL.\nTrực tiếp xử lý lỗi kết nối database và thiết lập server local.\nThiết kế giao diện UI/UX cho ứng dụng Web và Mobile sử dụng\nFigma.\nBao quát toàn bộ vòng đời thiết kế từ Research, Ideation, xây dựng\nWireframe, tạo Prototype cho đến Testing.\nXây dựng ứng dụng chat trực tuyến sử dụng C# WinForms và\nSocket Programming.\nTriển khai đa dạng tính năng như gửi/nhận tin nhắn (rich text),\nemoji, gửi file/hình ảnh.\nTích hợp chức năng thu hồi, xóa, tìm kiếm tin nhắn và lưu trữ lịch\nsử chat có hiển thị timestamp.\nXếp loại: Khá (GPA 2.9)\nSoftware Engineering\nDatabase Systems\nArtificial Intelligence\nUI/UX Design, Web Dev\nFramework/Library:\nWinForms(.NET), Pygame,\nReact, Flutter\nCơ sở dữ liệu: MySQL\nCông cụ: Git/GitHub, XAMPP,\nApache, Figma, Android\nStudio, VS Code, Visual Studio\nChuyên môn khác:\nDebugging,Port forwarding,\nthiết kế UI/UX, lệnhLinux cơ\nbản\n0896940821\nnguyenduc842004@gmail.com\nPhường Hòa Cường, TP.Đà Nẵng\nKỹ Năng\nCông nghệ Thông tin\nĐại học Kiến Trúc Đà Nẵng\n2022 - 2027\nSở thích\nTìm hiểu các công nghệ\nmới\nChơi thể thao\nĐọc sách\n2023 - 2026\nKinh nghiệm thực hành\nDự án cá nhân & Bài tập nhóm\nTham gia làm bài tập nhóm tại trường và tự xây dựng các dự án cá\nnhân.\nLàm quen với quy trình Git và làm việc nhóm .','{\"email\": \"[EMAIL]\", \"phone\": \"[PHONE]\", \"skills\": [{\"name\": \"C++\", \"category\": \"programming_language\", \"years_experience\": 1.0, \"proficiency_level\": \"intermediate\"}, {\"name\": \"C#\", \"category\": \"programming_language\", \"years_experience\": 1.0, \"proficiency_level\": \"intermediate\"}, {\"name\": \"Python\", \"category\": \"programming_language\", \"years_experience\": 1.0, \"proficiency_level\": \"intermediate\"}, {\"name\": \"Java\", \"category\": \"programming_language\", \"years_experience\": 1.0, \"proficiency_level\": \"intermediate\"}, {\"name\": \"JavaScript\", \"category\": \"programming_language\", \"years_experience\": 1.0, \"proficiency_level\": \"intermediate\"}, {\"name\": \"SQL\", \"category\": \"database\", \"years_experience\": 1.0, \"proficiency_level\": \"intermediate\"}, {\"name\": \"Figma\", \"category\": \"tool\", \"years_experience\": 1.0, \"proficiency_level\": \"intermediate\"}, {\"name\": \"MySQL\", \"category\": \"database\", \"years_experience\": 1.0, \"proficiency_level\": \"intermediate\"}, {\"name\": \"React\", \"category\": \"framework\", \"years_experience\": 1.0, \"proficiency_level\": \"intermediate\"}, {\"name\": \"Flutter\", \"category\": \"framework\", \"years_experience\": 1.0, \"proficiency_level\": \"intermediate\"}], \"summary\": \"Sinh viên năm 4 ngành Công nghệ Thông tin với nền tảng kỹ thuật vững chắc và kinh nghiệm thực tế trong phát triển phần mềm, ứng dụng web và triển khai thuật toán.\", \"location\": \"Phường Hòa Cường, TP.Đà Nẵng\", \"projects\": [], \"education\": [{\"gpa\": 2.9, \"degree\": \"Cử nhân\", \"end_year\": 2023, \"start_year\": 2019, \"institution\": \"Đại học Kiến Trúc Đà Nẵng\", \"field_of_study\": \"Công nghệ Thông tin\"}], \"full_name\": \"NGUYỄN HUY ĐỨC\", \"experience\": [{\"company\": \"Dự án cá nhân\", \"end_date\": \"04/2026\", \"position\": \"Intern / Fresher Software Developer\", \"start_date\": \"02/2026\", \"description\": \"Triển khai website bán hàng hoàn chỉnh trên nền tảng WordPress. Cấu hình hệ thống Apache và MySQL trên môi trường Linux/WSL. Thiết kế giao diện UI/UX cho ứng dụng Web và Mobile sử dụng Figma.\", \"skills_used\": [\"C#\", \"MySQL\", \"Figma\"]}, {\"company\": \"Dự án cá nhân\", \"end_date\": \"04/2026\", \"position\": \"Intern / Fresher Software Developer\", \"start_date\": \"03/2026\", \"description\": \"Xây dựng ứng dụng chat trực tuyến sử dụng C# WinForms và Socket Programming. Triển khai đa dạng tính năng như gửi/nhận tin nhắn, emoji, gửi file/hình ảnh.\", \"skills_used\": [\"C#\", \"Socket Programming\"]}], \"certificates\": [], \"total_experience_years\": 0.0}','2026-10-15 21:39:13','2026-10-15 21:39:30','78c3dfb53ed805c16b49d8b5fe883f4266eb90cb8c12abec8e489e882ea906e5',NULL);
/*!40000 ALTER TABLE `cvs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `job_skills`
--

DROP TABLE IF EXISTS `job_skills`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
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
) ENGINE=InnoDB AUTO_INCREMENT=53 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `job_skills`
--

LOCK TABLES `job_skills` WRITE;
/*!40000 ALTER TABLE `job_skills` DISABLE KEYS */;
INSERT INTO `job_skills` VALUES (7,3,6,1,'high'),(8,3,52,1,'high'),(9,3,10,1,'high'),(10,3,53,1,'medium'),(11,3,54,1,'medium'),(12,3,55,0,'low'),(13,3,43,0,'low'),(14,4,7,1,'high'),(15,4,4,1,'medium'),(16,4,56,1,'medium'),(17,4,57,0,'medium'),(18,4,58,0,'low'),(19,5,4,1,'high'),(20,5,59,1,'high'),(21,5,40,1,'high'),(22,5,7,1,'medium'),(23,5,60,0,'medium'),(24,5,43,0,'medium'),(25,5,61,0,'low'),(26,6,14,1,'high'),(27,6,43,1,'high'),(28,6,62,1,'high'),(29,6,61,1,'medium'),(30,6,42,1,'medium'),(31,6,63,0,'medium'),(32,6,4,0,'low'),(39,2,4,1,'high'),(40,2,50,1,'high'),(41,2,7,1,'medium'),(42,2,42,1,'medium'),(43,2,43,0,'medium'),(44,2,51,0,'low'),(46,7,65,1,'medium'),(47,7,10,1,'medium'),(48,7,66,1,'medium'),(49,7,52,1,'medium'),(50,7,14,0,'medium'),(51,8,3,1,'medium'),(52,9,4,1,'medium');
/*!40000 ALTER TABLE `job_skills` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `jobs`
--

DROP TABLE IF EXISTS `jobs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
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
  `owner_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_jobs_id` (`id`),
  KEY `idx_jobs_is_deleted` (`is_deleted`),
  KEY `ix_jobs_owner_id` (`owner_id`),
  CONSTRAINT `fk_jobs_owner_id_users` FOREIGN KEY (`owner_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `jobs`
--

LOCK TABLES `jobs` WRITE;
/*!40000 ALTER TABLE `jobs` DISABLE KEYS */;
INSERT INTO `jobs` VALUES (1,'Dev','ABC','Đà Nẵng','full_time','junior','backend','Không yêu cầu kinh nghiệm, ',NULL,NULL,0,'2026-09-20 17:50:32','2026-10-10 16:59:36',1,'2026-10-10 09:59:37',NULL),(2,'Junior Backend Developer','TechNova Labs','Hà Nội / Hybrid','full_time','junior','backend','Phát triển API backend cho sản phẩm SaaS. Required: Python, FastAPI, SQL, Git. Preferred: Docker, Redis.',900,1500,1,'2026-10-09 12:13:19',NULL,0,NULL,NULL),(3,'Frontend React Developer','PixelWorks','Remote','full_time','mid','frontend','Xây dựng giao diện web hiện đại. Required: JavaScript, TypeScript, React, HTML, CSS. Preferred: Vue, Docker.',1200,2200,1,'2026-10-09 12:13:19',NULL,0,NULL,NULL),(4,'Data Analyst Intern','Insight Analytics','Đà Nẵng','internship','intern','data','Hỗ trợ phân tích dữ liệu và báo cáo kinh doanh. Required: SQL, Python, Excel. Preferred: Power BI, Statistics.',300,600,1,'2026-10-09 12:13:19',NULL,0,NULL,NULL),(5,'Machine Learning Engineer','AI Horizon','Hồ Chí Minh','full_time','senior','ai_ml','Phát triển và triển khai mô hình AI. Required: Python, Machine Learning, TensorFlow, SQL. Preferred: PyTorch, Docker, AWS.',2200,4000,1,'2026-10-09 12:13:19',NULL,0,NULL,NULL),(6,'DevOps Engineer','CloudBridge','Remote / Việt Nam','full_time','mid','devops','Quản lý hạ tầng cloud và pipeline CI/CD. Required: Linux, Docker, Kubernetes, AWS, Git. Preferred: Terraform, Python.',1800,3200,1,'2026-10-09 12:13:19',NULL,0,NULL,NULL),(7,'Senior Fullstack Developer','Bluera','TP. Hồ Chí Minh','full_time','senior','fullstack','Nghiên cứu, thiết kế kiến trúc tổng thể, xây dựng và triển khai toàn diện hệ thống phần mềm',1000,1500,1,'2026-10-10 17:17:14',NULL,0,NULL,NULL),(8,'fsd',NULL,NULL,'full_time','junior','backend',NULL,NULL,NULL,0,'2026-10-15 22:05:13','2026-10-15 22:05:42',1,'2026-10-15 15:05:42',NULL),(9,'fdgf','fdsf',NULL,'full_time','junior','backend',NULL,NULL,NULL,0,'2026-10-20 11:20:05','2026-10-20 11:24:10',1,'2026-10-20 04:24:10',5);
/*!40000 ALTER TABLE `jobs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `profiles`
--

DROP TABLE IF EXISTS `profiles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
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
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `profiles`
--

LOCK TABLES `profiles` WRITE;
/*!40000 ALTER TABLE `profiles` DISABLE KEYS */;
INSERT INTO `profiles` VALUES (1,1,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-09-17 16:51:24',NULL),(2,2,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-09-17 16:56:25',NULL),(3,3,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-09-18 15:58:58',NULL),(4,4,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-09-18 16:10:43',NULL),(5,5,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-10-20 11:13:22',NULL);
/*!40000 ALTER TABLE `profiles` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `skill_gaps`
--

DROP TABLE IF EXISTS `skill_gaps`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
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
  `created_at` datetime DEFAULT (now()),
  `job_snapshot` json DEFAULT NULL,
  `matched_at` datetime(6) DEFAULT NULL,
  `cv_input_hash` varchar(64) DEFAULT NULL,
  `review_status` enum('new','viewed','shortlisted','rejected','hired') NOT NULL DEFAULT 'new',
  `recruiter_note` text,
  `reviewed_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `cv_id` (`cv_id`),
  KEY `job_id` (`job_id`),
  KEY `ix_skill_gaps_id` (`id`),
  CONSTRAINT `skill_gaps_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `skill_gaps_ibfk_2` FOREIGN KEY (`cv_id`) REFERENCES `cvs` (`id`) ON DELETE CASCADE,
  CONSTRAINT `skill_gaps_ibfk_3` FOREIGN KEY (`job_id`) REFERENCES `jobs` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `skill_gaps`
--

LOCK TABLES `skill_gaps` WRITE;
/*!40000 ALTER TABLE `skill_gaps` DISABLE KEYS */;
INSERT INTO `skill_gaps` VALUES (9,4,29,7,0,'[]','[{\"priority\": \"high\", \"skill_id\": 65, \"importance\": \"medium\", \"skill_name\": \"Node.Js\", \"is_required\": true}, {\"priority\": \"high\", \"skill_id\": 10, \"importance\": \"medium\", \"skill_name\": \"React\", \"is_required\": true}, {\"priority\": \"high\", \"skill_id\": 66, \"importance\": \"medium\", \"skill_name\": \"React Native\", \"is_required\": true}, {\"priority\": \"high\", \"skill_id\": 52, \"importance\": \"medium\", \"skill_name\": \"TypeScript\", \"is_required\": true}, {\"priority\": \"low\", \"skill_id\": 14, \"importance\": \"medium\", \"skill_name\": \"Linux\", \"is_required\": false}]','[]','Để phù hợp hơn với vị trí Senior Fullstack Developer, bạn nên:\n1. Bổ sung Node.Js (high): học kiến thức nền và thực hành bằng một dự án nhỏ liên quan đến vị trí Senior Fullstack Developer.\n2. Bổ sung React (high): học kiến thức nền và thực hành bằng một dự án nhỏ liên quan đến vị trí Senior Fullstack Developer.\n3. Bổ sung React Native (high): học kiến thức nền và thực hành bằng một dự án nhỏ liên quan đến vị trí Senior Fullstack Developer.\n4. Bổ sung TypeScript (high): học kiến thức nền và thực hành bằng một dự án nhỏ liên quan đến vị trí Senior Fullstack Developer.\n5. Bổ sung Linux (low): học kiến thức nền và thực hành bằng một dự án nhỏ liên quan đến vị trí Senior Fullstack Developer.','2026-10-10 18:31:36',NULL,NULL,NULL,'new',NULL,NULL),(10,4,30,7,0,'[]','[{\"priority\": \"high\", \"skill_id\": 65, \"importance\": \"medium\", \"skill_name\": \"Node.Js\", \"is_required\": true}, {\"priority\": \"high\", \"skill_id\": 10, \"importance\": \"medium\", \"skill_name\": \"React\", \"is_required\": true}, {\"priority\": \"high\", \"skill_id\": 66, \"importance\": \"medium\", \"skill_name\": \"React Native\", \"is_required\": true}, {\"priority\": \"high\", \"skill_id\": 52, \"importance\": \"medium\", \"skill_name\": \"TypeScript\", \"is_required\": true}, {\"priority\": \"low\", \"skill_id\": 14, \"importance\": \"medium\", \"skill_name\": \"Linux\", \"is_required\": false}]','[]','Để phù hợp hơn với vị trí Senior Fullstack Developer, bạn nên:\n1. Bổ sung Node.Js (high): học kiến thức nền và thực hành bằng một dự án nhỏ liên quan đến vị trí Senior Fullstack Developer.\n2. Bổ sung React (high): học kiến thức nền và thực hành bằng một dự án nhỏ liên quan đến vị trí Senior Fullstack Developer.\n3. Bổ sung React Native (high): học kiến thức nền và thực hành bằng một dự án nhỏ liên quan đến vị trí Senior Fullstack Developer.\n4. Bổ sung TypeScript (high): học kiến thức nền và thực hành bằng một dự án nhỏ liên quan đến vị trí Senior Fullstack Developer.\n5. Bổ sung Linux (low): học kiến thức nền và thực hành bằng một dự án nhỏ liên quan đến vị trí Senior Fullstack Developer.','2026-10-10 18:31:53','{\"id\": 7, \"level\": \"senior\", \"title\": \"Senior Fullstack Developer\", \"company\": \"Bluera\", \"category\": \"fullstack\", \"job_type\": \"full_time\", \"location\": \"TP. Hồ Chí Minh\", \"is_active\": true, \"created_at\": \"2026-10-10T17:17:14\", \"job_skills\": [{\"skill_id\": 65, \"importance\": \"medium\", \"skill_name\": \"Node.Js\", \"is_required\": true}, {\"skill_id\": 10, \"importance\": \"medium\", \"skill_name\": \"React\", \"is_required\": true}, {\"skill_id\": 66, \"importance\": \"medium\", \"skill_name\": \"React Native\", \"is_required\": true}, {\"skill_id\": 52, \"importance\": \"medium\", \"skill_name\": \"TypeScript\", \"is_required\": true}, {\"skill_id\": 14, \"importance\": \"medium\", \"skill_name\": \"Linux\", \"is_required\": false}], \"salary_max\": 1500, \"salary_min\": 1000, \"description\": \"Nghiên cứu, thiết kế kiến trúc tổng thể, xây dựng và triển khai toàn diện hệ thống phần mềm\"}','2026-10-19 15:28:25.111120','20390cebfae00469ed96d7123a98cd63e4bbbf93ca44489b79050a81f00dbd8c','new',NULL,NULL),(11,4,28,7,8.6,'[{\"cv_level\": \"beginner\", \"skill_id\": 14, \"importance\": \"medium\", \"skill_name\": \"Linux\", \"is_required\": false, \"years_experience\": 0.0}]','[{\"priority\": \"high\", \"skill_id\": 65, \"importance\": \"medium\", \"skill_name\": \"Node.Js\", \"is_required\": true}, {\"priority\": \"high\", \"skill_id\": 10, \"importance\": \"medium\", \"skill_name\": \"React\", \"is_required\": true}, {\"priority\": \"high\", \"skill_id\": 66, \"importance\": \"medium\", \"skill_name\": \"React Native\", \"is_required\": true}, {\"priority\": \"high\", \"skill_id\": 52, \"importance\": \"medium\", \"skill_name\": \"TypeScript\", \"is_required\": true}]','[]','Để phù hợp hơn với vị trí Senior Fullstack Developer, bạn nên:\n1. Bổ sung Node.Js (high): học kiến thức nền và thực hành bằng một dự án nhỏ liên quan đến vị trí Senior Fullstack Developer.\n2. Bổ sung React (high): học kiến thức nền và thực hành bằng một dự án nhỏ liên quan đến vị trí Senior Fullstack Developer.\n3. Bổ sung React Native (high): học kiến thức nền và thực hành bằng một dự án nhỏ liên quan đến vị trí Senior Fullstack Developer.\n4. Bổ sung TypeScript (high): học kiến thức nền và thực hành bằng một dự án nhỏ liên quan đến vị trí Senior Fullstack Developer.','2026-10-10 18:32:05','{\"id\": 7, \"level\": \"senior\", \"title\": \"Senior Fullstack Developer\", \"company\": \"Bluera\", \"category\": \"fullstack\", \"job_type\": \"full_time\", \"location\": \"TP. Hồ Chí Minh\", \"is_active\": true, \"created_at\": \"2026-10-10T17:17:14\", \"job_skills\": [{\"skill_id\": 65, \"importance\": \"medium\", \"skill_name\": \"Node.Js\", \"is_required\": true}, {\"skill_id\": 10, \"importance\": \"medium\", \"skill_name\": \"React\", \"is_required\": true}, {\"skill_id\": 66, \"importance\": \"medium\", \"skill_name\": \"React Native\", \"is_required\": true}, {\"skill_id\": 52, \"importance\": \"medium\", \"skill_name\": \"TypeScript\", \"is_required\": true}, {\"skill_id\": 14, \"importance\": \"medium\", \"skill_name\": \"Linux\", \"is_required\": false}], \"salary_max\": 1500, \"salary_min\": 1000, \"description\": \"Nghiên cứu, thiết kế kiến trúc tổng thể, xây dựng và triển khai toàn diện hệ thống phần mềm\"}','2026-10-19 15:28:29.541522','de0f1b5ff6703d1276343903d9692548932900142a7f9a8a7c5589b57942adf2','new',NULL,NULL),(12,4,31,7,8.6,'[{\"cv_level\": \"intermediate\", \"skill_id\": 14, \"importance\": \"medium\", \"skill_name\": \"Linux\", \"is_required\": false, \"years_experience\": 0.0}]','[{\"priority\": \"high\", \"skill_id\": 65, \"importance\": \"medium\", \"skill_name\": \"Node.Js\", \"is_required\": true}, {\"priority\": \"high\", \"skill_id\": 66, \"importance\": \"medium\", \"skill_name\": \"React Native\", \"is_required\": true}, {\"priority\": \"high\", \"skill_id\": 52, \"importance\": \"medium\", \"skill_name\": \"TypeScript\", \"is_required\": true}]','[{\"priority\": \"high\", \"skill_id\": 10, \"importance\": \"medium\", \"skill_name\": \"React\", \"is_required\": true, \"needed_level\": \"advanced\", \"current_level\": \"intermediate\"}]','Để phù hợp hơn với vị trí Senior Fullstack Developer, bạn nên:\n1. Bổ sung Node.Js (high): học kiến thức nền và thực hành bằng một dự án nhỏ liên quan đến vị trí Senior Fullstack Developer.\n2. Bổ sung React Native (high): học kiến thức nền và thực hành bằng một dự án nhỏ liên quan đến vị trí Senior Fullstack Developer.\n3. Bổ sung TypeScript (high): học kiến thức nền và thực hành bằng một dự án nhỏ liên quan đến vị trí Senior Fullstack Developer.\n4. Nâng cao React từ mức intermediate lên advanced: luyện tập qua bài tập thực tế và cập nhật vào CV.','2026-10-15 21:44:45','{\"id\": 7, \"level\": \"senior\", \"title\": \"Senior Fullstack Developer\", \"company\": \"Bluera\", \"category\": \"fullstack\", \"job_type\": \"full_time\", \"location\": \"TP. Hồ Chí Minh\", \"is_active\": true, \"created_at\": \"2026-10-10T17:17:14\", \"job_skills\": [{\"skill_id\": 65, \"importance\": \"medium\", \"skill_name\": \"Node.Js\", \"is_required\": true}, {\"skill_id\": 10, \"importance\": \"medium\", \"skill_name\": \"React\", \"is_required\": true}, {\"skill_id\": 66, \"importance\": \"medium\", \"skill_name\": \"React Native\", \"is_required\": true}, {\"skill_id\": 52, \"importance\": \"medium\", \"skill_name\": \"TypeScript\", \"is_required\": true}, {\"skill_id\": 14, \"importance\": \"medium\", \"skill_name\": \"Linux\", \"is_required\": false}], \"salary_max\": 1500, \"salary_min\": 1000, \"description\": \"Nghiên cứu, thiết kế kiến trúc tổng thể, xây dựng và triển khai toàn diện hệ thống phần mềm\"}','2026-10-19 15:28:19.382616','b87138ec6531af16e28e0209dfa61932806ad3bf7ed831c31d6f618bef8e391c','new',NULL,NULL),(13,4,31,6,43.1,'[{\"cv_level\": \"intermediate\", \"skill_id\": 14, \"importance\": \"high\", \"skill_name\": \"Linux\", \"is_required\": true, \"years_experience\": 0.0}, {\"cv_level\": \"intermediate\", \"skill_id\": 43, \"importance\": \"high\", \"skill_name\": \"Docker\", \"is_required\": true, \"years_experience\": 1.0}, {\"cv_level\": \"intermediate\", \"skill_id\": 4, \"importance\": \"low\", \"skill_name\": \"Python\", \"is_required\": false, \"years_experience\": 1.0}]','[{\"priority\": \"high\", \"skill_id\": 62, \"importance\": \"high\", \"skill_name\": \"Kubernetes\", \"is_required\": true}, {\"priority\": \"high\", \"skill_id\": 61, \"importance\": \"medium\", \"skill_name\": \"AWS\", \"is_required\": true}, {\"priority\": \"high\", \"skill_id\": 42, \"importance\": \"medium\", \"skill_name\": \"Git\", \"is_required\": true}, {\"priority\": \"low\", \"skill_id\": 63, \"importance\": \"medium\", \"skill_name\": \"Terraform\", \"is_required\": false}]','[]','Dưới đây là những đề xuất học tập cho ứng viên DevOps Engineer:\n\n1. **Kubernetes**\n   - **Lý do**: Đây là công cụ quản lý container phổ biến, rất cần thiết trong môi trường DevOps.\n   - **Cách thực hành**: Tham gia các khóa học trực tuyến (như Udemy, Coursera) để học lý thuyết, sau đó thực hành triển khai ứng dụng trên Kubernetes bằng cách sử dụng Minikube hoặc các dịch vụ cloud như GKE.\n\n2. **AWS (Amazon Web Services)**\n   - **Lý do**: AWS là nền tảng điện toán đám mây hàng đầu, nhiều công ty sử dụng để triển khai ứng dụng.\n   - **Cách thực hành**: Đăng ký tài khoản AWS miễn phí và thực hành tạo và quản lý các dịch vụ như EC2, S3, và RDS thông qua các bài hướng dẫn trên AWS Training.\n\n3. **Terraform**\n   - **Lý do**: Công cụ này giúp tự động hóa việc quản lý hạ tầng, rất quan trọng trong DevOps.\n   - **Cách thực hành**: Tham gia khóa học trực tuyến về Terraform và thực hành tạo hạ tầng trên AWS hoặc GCP từ mã nguồn.\n\n4. **Git**\n   - **Lý do**: Quản lý mã nguồn là kỹ năng quan trọng cho mọi lập trình viên và DevOps.\n   - **Cách thực hành**: Thực hành sử dụng Git để quản lý dự án cá nhân, tham gia vào các dự án mã nguồn mở trên GitHub để cải thiện kỹ năng.\n\n5. **Tham gia vào cộng đồng DevOps**\n   - **Lý do**: Kết nối với các chuyên gia và nhận được sự hỗ trợ, chia sẻ kinh nghiệm.\n   - **Cách thực hành**: Tham gia các diễn đàn, nhóm trên mạng xã hội hoặc các buổi meetup liên quan đến DevOps để học hỏi và trao đổi kiến thức.\n\nTập trung vào việc thực hành và dự án thực tế sẽ giúp bạn tự tin hơn trong quá trình ứng tuyển.','2026-10-15 21:45:21',NULL,NULL,NULL,'new',NULL,NULL),(14,4,31,8,100,'[{\"cv_level\": \"intermediate\", \"skill_id\": 3, \"importance\": \"medium\", \"skill_name\": \"C#\", \"is_required\": true, \"years_experience\": 1.0}]','[]','[]','CV hiện tại đã đáp ứng các kỹ năng chính cho vị trí fsd. Hãy tiếp tục củng cố kinh nghiệm qua dự án thực tế.','2026-10-15 22:05:26',NULL,NULL,NULL,'new',NULL,NULL),(15,4,31,5,6.5,'[{\"cv_level\": \"intermediate\", \"skill_id\": 43, \"importance\": \"medium\", \"skill_name\": \"Docker\", \"is_required\": false, \"years_experience\": 1.0}]','[{\"priority\": \"high\", \"skill_id\": 59, \"importance\": \"high\", \"skill_name\": \"Machine Learning\", \"is_required\": true}, {\"priority\": \"high\", \"skill_id\": 40, \"importance\": \"high\", \"skill_name\": \"TensorFlow\", \"is_required\": true}, {\"priority\": \"low\", \"skill_id\": 60, \"importance\": \"medium\", \"skill_name\": \"PyTorch\", \"is_required\": false}, {\"priority\": \"low\", \"skill_id\": 61, \"importance\": \"low\", \"skill_name\": \"AWS\", \"is_required\": false}]','[{\"priority\": \"high\", \"skill_id\": 4, \"importance\": \"high\", \"skill_name\": \"Python\", \"is_required\": true, \"needed_level\": \"advanced\", \"current_level\": \"intermediate\"}, {\"priority\": \"high\", \"skill_id\": 7, \"importance\": \"medium\", \"skill_name\": \"SQL\", \"is_required\": true, \"needed_level\": \"advanced\", \"current_level\": \"intermediate\"}]','Để phù hợp hơn với vị trí Machine Learning Engineer, bạn nên:\n1. Bổ sung Machine Learning (high): học kiến thức nền và thực hành bằng một dự án nhỏ liên quan đến vị trí Machine Learning Engineer.\n2. Bổ sung TensorFlow (high): học kiến thức nền và thực hành bằng một dự án nhỏ liên quan đến vị trí Machine Learning Engineer.\n3. Bổ sung PyTorch (low): học kiến thức nền và thực hành bằng một dự án nhỏ liên quan đến vị trí Machine Learning Engineer.\n4. Bổ sung AWS (low): học kiến thức nền và thực hành bằng một dự án nhỏ liên quan đến vị trí Machine Learning Engineer.\n5. Nâng cao Python từ mức intermediate lên advanced: luyện tập qua bài tập thực tế và cập nhật vào CV.\n6. Nâng cao SQL từ mức intermediate lên advanced: luyện tập qua bài tập thực tế và cập nhật vào CV.','2026-10-19 22:28:45','{\"id\": 5, \"level\": \"senior\", \"title\": \"Machine Learning Engineer\", \"company\": \"AI Horizon\", \"category\": \"ai_ml\", \"job_type\": \"full_time\", \"location\": \"Hồ Chí Minh\", \"is_active\": true, \"created_at\": \"2026-10-09T12:13:19\", \"job_skills\": [{\"skill_id\": 4, \"importance\": \"high\", \"skill_name\": \"Python\", \"is_required\": true}, {\"skill_id\": 59, \"importance\": \"high\", \"skill_name\": \"Machine Learning\", \"is_required\": true}, {\"skill_id\": 40, \"importance\": \"high\", \"skill_name\": \"TensorFlow\", \"is_required\": true}, {\"skill_id\": 7, \"importance\": \"medium\", \"skill_name\": \"SQL\", \"is_required\": true}, {\"skill_id\": 60, \"importance\": \"medium\", \"skill_name\": \"PyTorch\", \"is_required\": false}, {\"skill_id\": 43, \"importance\": \"medium\", \"skill_name\": \"Docker\", \"is_required\": false}, {\"skill_id\": 61, \"importance\": \"low\", \"skill_name\": \"AWS\", \"is_required\": false}], \"salary_max\": 4000, \"salary_min\": 2200, \"description\": \"Phát triển và triển khai mô hình AI. Required: Python, Machine Learning, TensorFlow, SQL. Preferred: PyTorch, Docker, AWS.\"}','2026-10-19 15:28:45.482795','b87138ec6531af16e28e0209dfa61932806ad3bf7ed831c31d6f618bef8e391c','new',NULL,NULL),(16,4,31,4,58.1,'[{\"cv_level\": \"intermediate\", \"skill_id\": 7, \"importance\": \"high\", \"skill_name\": \"SQL\", \"is_required\": true, \"years_experience\": 1.0}, {\"cv_level\": \"intermediate\", \"skill_id\": 4, \"importance\": \"medium\", \"skill_name\": \"Python\", \"is_required\": true, \"years_experience\": 1.0}]','[{\"priority\": \"high\", \"skill_id\": 56, \"importance\": \"medium\", \"skill_name\": \"Excel\", \"is_required\": true}, {\"priority\": \"low\", \"skill_id\": 57, \"importance\": \"medium\", \"skill_name\": \"Power BI\", \"is_required\": false}, {\"priority\": \"low\", \"skill_id\": 58, \"importance\": \"low\", \"skill_name\": \"Statistics\", \"is_required\": false}]','[]','Để phù hợp hơn với vị trí Data Analyst Intern, bạn nên:\n1. Bổ sung Excel (high): học kiến thức nền và thực hành bằng một dự án nhỏ liên quan đến vị trí Data Analyst Intern.\n2. Bổ sung Power BI (low): học kiến thức nền và thực hành bằng một dự án nhỏ liên quan đến vị trí Data Analyst Intern.\n3. Bổ sung Statistics (low): học kiến thức nền và thực hành bằng một dự án nhỏ liên quan đến vị trí Data Analyst Intern.','2026-10-19 22:28:52','{\"id\": 4, \"level\": \"intern\", \"title\": \"Data Analyst Intern\", \"company\": \"Insight Analytics\", \"category\": \"data\", \"job_type\": \"internship\", \"location\": \"Đà Nẵng\", \"is_active\": true, \"created_at\": \"2026-10-09T12:13:19\", \"job_skills\": [{\"skill_id\": 7, \"importance\": \"high\", \"skill_name\": \"SQL\", \"is_required\": true}, {\"skill_id\": 4, \"importance\": \"medium\", \"skill_name\": \"Python\", \"is_required\": true}, {\"skill_id\": 56, \"importance\": \"medium\", \"skill_name\": \"Excel\", \"is_required\": true}, {\"skill_id\": 57, \"importance\": \"medium\", \"skill_name\": \"Power BI\", \"is_required\": false}, {\"skill_id\": 58, \"importance\": \"low\", \"skill_name\": \"Statistics\", \"is_required\": false}], \"salary_max\": 600, \"salary_min\": 300, \"description\": \"Hỗ trợ phân tích dữ liệu và báo cáo kinh doanh. Required: SQL, Python, Excel. Preferred: Power BI, Statistics.\"}','2026-10-19 15:28:52.131050','b87138ec6531af16e28e0209dfa61932806ad3bf7ed831c31d6f618bef8e391c','new',NULL,'2026-10-20 04:18:56'),(17,4,31,9,100,'[{\"cv_level\": \"intermediate\", \"skill_id\": 4, \"importance\": \"medium\", \"skill_name\": \"Python\", \"is_required\": true, \"years_experience\": 1.0}]','[]','[]','CV hiện tại đã đáp ứng các kỹ năng chính cho vị trí fdgf. Hãy tiếp tục củng cố kinh nghiệm qua dự án thực tế.','2026-10-20 11:20:49','{\"id\": 9, \"level\": \"junior\", \"title\": \"fdgf\", \"company\": \"fdsf\", \"category\": \"backend\", \"job_type\": \"full_time\", \"location\": null, \"owner_id\": 5, \"is_active\": true, \"created_at\": \"2026-10-20T11:20:05\", \"job_skills\": [{\"skill_id\": 4, \"importance\": \"medium\", \"skill_name\": \"Python\", \"is_required\": true}], \"salary_max\": null, \"salary_min\": null, \"description\": null}','2026-10-20 04:22:01.872583','b87138ec6531af16e28e0209dfa61932806ad3bf7ed831c31d6f618bef8e391c','new',NULL,'2026-10-20 04:22:26');
/*!40000 ALTER TABLE `skill_gaps` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `skills`
--

DROP TABLE IF EXISTS `skills`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
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
) ENGINE=InnoDB AUTO_INCREMENT=77 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `skills`
--

LOCK TABLES `skills` WRITE;
/*!40000 ALTER TABLE `skills` DISABLE KEYS */;
INSERT INTO `skills` VALUES (2,'C++','c++','programming_language',NULL,0,NULL),(3,'C#','c#','programming_language',NULL,0,NULL),(4,'Python','python','programming_language',NULL,0,NULL),(5,'Java','java','programming_language',NULL,0,NULL),(6,'JavaScript','javascript','programming_language',NULL,0,NULL),(7,'SQL','sql','programming_language',NULL,0,NULL),(8,'WinForms(.NET)','winforms(.net)','framework',NULL,0,NULL),(9,'Pygame','pygame','framework',NULL,0,NULL),(10,'React','react','framework',NULL,0,NULL),(11,'Flutter','flutter','framework',NULL,0,NULL),(12,'MySQL','mysql','database',NULL,0,NULL),(13,'Git/GitHub','git/github','devops',NULL,0,NULL),(14,'Linux','linux','devops',NULL,0,NULL),(15,'Figma','figma','tool',NULL,0,NULL),(16,'XAMPP','xampp','tool',NULL,0,NULL),(17,'Apache','apache','tool',NULL,0,NULL),(18,'Android Studio','android_studio','tool',NULL,0,NULL),(19,'VS Code','vs_code','tool',NULL,0,NULL),(20,'Visual Studio','visual_studio','tool',NULL,0,NULL),(21,'Teamwork','teamwork','soft_skill',NULL,0,NULL),(34,'Dart','dart','programming_language',NULL,0,NULL),(35,'PHP','php','programming_language',NULL,0,NULL),(36,'ReactJS','reactjs','framework',NULL,0,NULL),(37,'Django','django','framework',NULL,0,NULL),(38,'VueJS','vuejs','framework',NULL,0,NULL),(39,'PostgreSQL','postgresql','database',NULL,0,NULL),(40,'TensorFlow','tensorflow','ai_ml',NULL,0,NULL),(41,'Roboflow','roboflow','ai_ml',NULL,0,NULL),(42,'Git','git','devops',NULL,0,NULL),(43,'Docker','docker','cloud',NULL,0,NULL),(44,'Maven','maven','tool',NULL,0,NULL),(45,'Pytest','pytest','other',NULL,0,NULL),(46,'Robot Framework','robot_framework','other',NULL,0,NULL),(47,'Kỹ năng giao tiếp','kỹ_năng_giao_tiếp','soft_skill',NULL,0,NULL),(48,'Kỹ năng đàm phán','kỹ_năng_đàm_phán','soft_skill',NULL,0,NULL),(49,'Kỹ năng thuyết trình','kỹ_năng_thuyết_trình','soft_skill',NULL,0,NULL),(50,'FastAPI','fastapi','other',NULL,0,NULL),(51,'Redis','redis','other',NULL,0,NULL),(52,'TypeScript','typescript','other',NULL,0,NULL),(53,'HTML','html','other',NULL,0,NULL),(54,'CSS','css','other',NULL,0,NULL),(55,'Vue','vue','other',NULL,0,NULL),(56,'Excel','excel','other',NULL,0,NULL),(57,'Power BI','power_bi','other',NULL,0,NULL),(58,'Statistics','statistics','other',NULL,0,NULL),(59,'Machine Learning','machine_learning','other',NULL,0,NULL),(60,'PyTorch','pytorch','other',NULL,0,NULL),(61,'AWS','aws','other',NULL,0,NULL),(62,'Kubernetes','kubernetes','other',NULL,0,NULL),(63,'Terraform','terraform','other',NULL,0,NULL),(64,'Node.Js, React, React Native, TypeScript','node.js,_react,_react_native,_typescript','other',NULL,0,NULL),(65,'Node.Js','node.js','other',NULL,0,NULL),(66,'React Native','react_native','other',NULL,0,NULL),(74,'Spring Boot','spring_boot','framework',NULL,0,NULL),(75,'Postman','postman','tool',NULL,0,NULL),(76,'NodeJS','nodejs','framework',NULL,0,NULL);
/*!40000 ALTER TABLE `skills` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `email` varchar(255) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `full_name` varchar(255) NOT NULL,
  `role` enum('user','admin','recruiter') NOT NULL DEFAULT 'user',
  `is_active` tinyint(1) DEFAULT NULL,
  `created_at` datetime DEFAULT (now()),
  `updated_at` datetime DEFAULT NULL,
  `token_version` int NOT NULL DEFAULT '0',
  `is_verified` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_users_email` (`email`),
  KEY `ix_users_id` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (1,'huyduc0804@gmail.com','$2b$12$JCmGTZoBnaCCwRJox.8pzuMjs4byfxO5p3clVPd3kbe.P74HzEzWK','Nguyễn Huy Đức','admin',1,'2026-09-17 16:51:24',NULL,0,1),(2,'organizer@eventpro.com','$2b$12$grlGwyPCOtFr2PCT5AtJLuaZxFae.Kle1FN7Pf8YiHANy/1eLa0ca','Văn A','user',1,'2026-09-17 16:56:25',NULL,0,1),(3,'vanb123@gamil.com','$2b$12$9F.1kPcaS2O14b3iMBEdtuquNL2D9MOJ1Dh145eubUfoeGUK8HN8q','Văn B','user',1,'2026-09-18 15:58:58',NULL,0,1),(4,'nguyenduc842004@gmail.com','$2b$12$9A9.32MqL.wDUimIx/ViS.O.KE7544Pqi0MmNT8BPVPYZcpXiBDPa','nguyenduc','user',1,'2026-09-18 16:10:43','2026-09-18 16:11:24',0,1),(5,'recruiter123@gmail.com','$2b$12$cj8a5LeRVvATxr5qYxVLiuS24brIrtFjfrh3jQvuqTr7pr4ya37Zi','TuyenDungA','recruiter',1,'2026-10-20 11:13:22','2026-10-20 11:24:45',5,1);
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping events for database 'ai_cv_skillgap'
--

--
-- Dumping routines for database 'ai_cv_skillgap'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-10-22  9:24:53
