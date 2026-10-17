"""Đọc JD theo quy tắc cục bộ khi dịch vụ AI không khả dụng."""
import re


SKILL_CATALOG = {
    "python": "high", "java": "high", "javascript": "high", "typescript": "medium",
    "react": "high", "vue": "medium", "angular": "medium", "node.js": "medium",
    "fastapi": "medium", "django": "medium", "sql": "high", "mysql": "medium",
    "postgresql": "medium", "mongodb": "medium", "redis": "low", "docker": "medium",
    "kubernetes": "low", "aws": "medium", "azure": "low", "git": "medium",
    "machine learning": "high", "tensorflow": "medium", "pytorch": "medium",
}

# Nhận diện cụm dài trước để "không bắt buộc" không bị đọc thành "bắt buộc".
SECTION_MARKERS = re.compile(
    r"(?<!\w)(?:"
    r"(?P<preferred>không bắt buộc|not required|nice[- ]to[- ]have|"
    r"preferred(?: skills)?|optional|ưu tiên|lợi thế|điểm cộng)|"
    r"(?P<required>required(?: skills)?|requirements?|must[- ]have|bắt buộc|yêu cầu)|"
    r"(?P<other>benefits|responsibilities|quyền lợi|phúc lợi|mô tả công việc)"
    r")(?!\w)",
    re.IGNORECASE,
)


def _contains_term(text: str, term: str) -> bool:
    return re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text, re.IGNORECASE) is not None


def _extract_skills(text: str) -> tuple[list[dict], list[dict]]:
    # Trường hợp chưa có tiêu đề mục, giữ cách phân loại thận trọng là preferred.
    context = "preferred"
    found: dict[str, bool] = {}

    def collect(fragment: str, section: str) -> None:
        if section == "other":
            return
        for name in SKILL_CATALOG:
            if _contains_term(fragment, name):
                # Nếu JD yêu cầu ở một mục, lần xuất hiện preferred không hạ nó xuống.
                found[name] = found.get(name, False) or section == "required"

    for line in re.split(r"[\n;]+", text):
        position = 0
        for marker in SECTION_MARKERS.finditer(line):
            collect(line[position:marker.start()], context)
            context = marker.lastgroup
            position = marker.end()
        collect(line[position:], context)

    required = []
    preferred = []
    for name, is_required in found.items():
        item = {
            "skill_name": name.title(),
            "is_required": is_required,
            "importance": SKILL_CATALOG[name],
        }
        (required if is_required else preferred).append(item)
    return required, preferred


def _extract_salary(text: str) -> tuple[int | None, int | None]:
    # Schema/UI hiện dùng USD. Không chuyển VND, triệu hay đơn vị khác thành USD.
    label = re.compile(r"(?<!\w)(?:salary|compensation|lương)(?!\w)", re.IGNORECASE)
    unsupported = re.compile(
        r"(?<!\w)(?:vnd|vnđ|triệu|trieu|đồng|dong|eur|euro|gbp|k)(?!\w)|[₫€£]",
        re.IGNORECASE,
    )
    number = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?![\d.,])"
    currency = r"(?:USD\s*|\$\s*)?"
    amounts = re.compile(
        rf"\s*(?:range\s*)?[:：]?\s*{currency}(?P<minimum>{number})"
        rf"(?:(?:\s*USD)?\s*(?:[-–—]|to|đến|tới)\s*{currency}(?P<maximum>{number})"
        rf"|\s+{currency}(?P<second>{number}))?"
        r"\s*(?:USD|\$)?\s*(?:/\s*month|per month|/\s*tháng)?\s*[.,]?\s*$",
        re.IGNORECASE,
    )
    for line in re.split(r"[\n;]+", text):
        marker = label.search(line)
        if not marker:
            continue
        salary_text = line[marker.end():]
        if unsupported.search(salary_text):
            continue
        match = amounts.fullmatch(salary_text)
        if not match:
            continue
        minimum = int(match["minimum"].replace(",", ""))
        upper = match["maximum"] or match["second"]
        maximum = int(upper.replace(",", "")) if upper else None
        if maximum is not None and maximum < minimum:
            continue
        return minimum, maximum
    return None, None


def parse_job_description_locally(text: str) -> dict:
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    required, preferred = _extract_skills(text)
    salary_min, salary_max = _extract_salary(text)
    levels = ("lead", "senior", "mid", "junior", "fresher", "intern")
    level = "junior"
    for candidate_text in (first_line, text):
        detected = next((value for value in levels if _contains_term(candidate_text, value)), None)
        if detected:
            level = detected
            break

    categories = {
        "fullstack": ("fullstack", "full-stack", "full stack"),
        "backend": ("backend", "back-end", "server"),
        "frontend": ("frontend", "front-end", "react", "vue"),
        "data": ("data analyst", "data engineer", "data science"),
        "ai_ml": ("machine learning", "deep learning", "ai/ml"),
        "devops": ("devops", "ci/cd", "kubernetes"),
        "mobile": ("android", "ios", "mobile"),
        "qa": ("quality assurance", "tester", "qa engineer"),
    }
    category = "other"
    for candidate_text in (first_line, text):
        detected = next((
            name for name, markers in categories.items()
            if any(_contains_term(candidate_text, marker) for marker in markers)
        ), None)
        if detected:
            category = detected
            break

    return {
        "title": first_line[:255],
        "level": level,
        "category": category,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "required_skills": required,
        "preferred_skills": preferred,
    }
