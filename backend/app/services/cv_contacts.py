"""Đọc và che thông tin liên hệ thông dụng trong văn bản CV, không gọi AI."""
import re


EMAIL_PATTERN = re.compile(
    r"(?<![\w.+-])[\w.!#$%&'*+/=?^`{|}~-]+@"
    r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+"
    r"[A-Za-z]{2,63}(?![\w-])",
)
PHONE_SEPARATOR = r"[ \t.()-]*"
PHONE_PATTERN = re.compile(
    rf"(?<![\w+])(?:"
    rf"(?:\+84{PHONE_SEPARATOR}(?:0{PHONE_SEPARATOR})?|0084{PHONE_SEPARATOR}|0{PHONE_SEPARATOR})"
    rf"(?:[35789](?:{PHONE_SEPARATOR}[0-9]){{8}}|2(?:{PHONE_SEPARATOR}[0-9]){{9}})"
    rf"|\+[1-9](?:{PHONE_SEPARATOR}[0-9]){{7,14}}"
    rf")(?!\w)",
)


def _normalize_phone(value: str) -> str | None:
    digits = re.sub(r"[^0-9]", "", value)
    if value.startswith("+84") or digits.startswith("0084"):
        national = digits[2:] if value.startswith("+84") else digits[4:]
        national = national.removeprefix("0")
        if re.fullmatch(r"[35789][0-9]{8}|2[0-9]{9}", national):
            return "+84" + national
        return None
    if value.startswith("+"):
        if 8 <= len(digits) <= 15:
            return "+" + digits
        return None
    if re.fullmatch(r"0[35789][0-9]{8}|02[0-9]{9}", digits):
        return digits
    return None


def extract_cv_contacts(text: str) -> dict[str, str]:
    """Lấy email và số điện thoại hợp lệ đầu tiên theo thứ tự văn bản.

    Đọc email thông dụng; hỗ trợ số di động/cố định VN, +84/0084 và số quốc tế
    có dấu +. Định dạng không nhận diện được trả chuỗi rỗng.
    """
    email = EMAIL_PATTERN.search(text)
    # Không đọc nhầm tên email dạng 0901234567@example.test thành điện thoại.
    without_emails = EMAIL_PATTERN.sub("[EMAIL]", text)
    phone = next((
        normalized for match in PHONE_PATTERN.finditer(without_emails)
        if (normalized := _normalize_phone(match.group())) is not None
    ), "")
    return {"email": email.group() if email else "", "phone": phone}


def redact_cv_contacts(text: str) -> str:
    """Che mọi email/số điện thoại nhận diện được bằng cùng quy tắc trích xuất."""
    text = EMAIL_PATTERN.sub("[EMAIL]", text)
    return PHONE_PATTERN.sub(
        lambda match: "[PHONE]" if _normalize_phone(match.group()) is not None else match.group(),
        text,
    )
