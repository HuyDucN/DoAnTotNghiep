# Yêu cầu hệ thống

## Mục tiêu
- Cho phép ứng viên tải CV lên, xem dữ liệu đã trích xuất và phân tích lại CV.
- So sánh kỹ năng trong CV với các yêu cầu của vị trí đang tuyển.
- Hiển thị kỹ năng phù hợp, còn thiếu hoặc chưa đạt mức yêu cầu; đưa ra gợi ý học tập.
- Cung cấp giao diện quản trị người dùng, CV, vị trí tuyển dụng và danh mục kỹ năng.

## Vai trò và quyền hạn
- Người dùng đăng ký/đăng nhập, quản lý hồ sơ cá nhân, CV của mình và lịch sử so khớp.
- Người dùng chỉ được xem/tải/xóa CV thuộc tài khoản của mình.
- Admin quản lý người dùng, bật/tắt tài khoản, CV, job và skill.
- Không cho admin tự khóa tài khoản hoặc khóa admin hoạt động cuối cùng.
- Các thao tác quản trị dùng chung xác thực admin; endpoint đăng ký, đăng nhập, phục hồi mật khẩu, upload CV và match có giới hạn tần suất.

## Tính năng
- Xác thực bằng JWT; hỗ trợ đăng ký, đăng nhập, đăng xuất và đặt lại mật khẩu.
- Upload PDF hoặc DOCX, giới hạn mặc định 10 MB; trích xuất văn bản PDF/DOCX và OCR PDF scan bằng Tesseract.
- Phân tích CV qua API tương thích OpenAI; văn bản gửi đi được giới hạn 12.000 ký tự và che email/số điện thoại.
- Quản lý hồ sơ ứng viên, CV và kết quả phân tích.
- Tạo/cập nhật/xóa job cùng danh sách kỹ năng bắt buộc và ưu tiên.
- Lọc job theo danh mục, cấp bậc và từ khóa; job ngừng hoạt động không xuất hiện ở API chi tiết hoặc match.
- So khớp CV-job và lưu lịch sử kết quả; admin có màn hình tìm kiếm, khóa/mở khóa người dùng.

## Quy tắc so khớp
- Ngưỡng năng lực tối thiểu theo cấp bậc: intern/fresher = beginner; junior/mid = intermediate; senior/lead = advanced.
- Kỹ năng bắt buộc chỉ được tính là phù hợp khi có trong CV và đạt ngưỡng cấp bậc; kỹ năng yếu được ghi thành weak skill.
- Kỹ năng ưu tiên được tính phù hợp khi có trong CV.
- Điểm hiện tại là tỷ lệ trọng số kỹ năng đạt: bắt buộc 1.0 điểm mỗi kỹ năng, ưu tiên 0.3 điểm mỗi kỹ năng. Số năm kinh nghiệm được lưu trong kết quả nhưng chưa tham gia công thức điểm.

## API chính
- `/api/auth`: register, login, logout, forgot-password, reset-password.
- `/api/users`: thông tin cá nhân, hồ sơ và đổi mật khẩu.
- `/api/cv`: upload, list, chi tiết, file có xác thực chủ sở hữu, xóa và reanalyze.
- `/api/jobs`: danh sách/chi tiết job, match CV-job, lịch sử skill-gap; `/admin` quản lý job.
- `/api/skills`: danh sách và CRUD skill.
- `/api/admin`: danh sách/khóa người dùng, danh sách/xóa CV.

## Dữ liệu và tích hợp
- Cơ sở dữ liệu MySQL gồm users, profiles, cvs, skills, cv_skills, jobs, job_skills và skill_gaps.
- Phân tích AI gửi văn bản CV đã giới hạn và che email/số điện thoại đến endpoint OpenAI-compatible được cấu hình bằng `OPENAI_BASE_URL`. Nhà vận hành cần công bố chính sách xử lý dữ liệu và chọn nhà cung cấp phù hợp trước khi triển khai.
- Tập đánh giá đại diện, nhãn ground truth và phép đo Precision/Recall/F1 chưa được thiết lập.

## Yêu cầu vận hành
- Cấu hình bí mật, mật khẩu DB, URL AI, CORS, thư mục upload và Tesseract qua biến môi trường.
- Production yêu cầu `SECRET_KEY` tối thiểu 32 ký tự, DB password và `DEBUG=False`.
- Rate limit hiện lưu trong bộ nhớ từng tiến trình; triển khai nhiều worker/instance cần chuyển sang kho chia sẻ như Redis để có giới hạn nhất quán.
- Schema mới được tạo tự động trong môi trường development; thay đổi schema DB hiện hữu cần chạy migration có kiểm soát.
