"""Chuẩn hóa tên kỹ năng, bảo toàn dấu và ký hiệu có ý nghĩa."""
import re
import unicodedata


def clean_skill_name(name: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", name).strip())


def normalize_skill_name(name: str) -> str:
    # C, C++, C# phải khác nhau; không bỏ dấu tiếng Việt hoặc dấu chấm Node.js.
    return re.sub(r"[\s_-]+", "_", clean_skill_name(name).casefold())


def validate_skill_name(value: str) -> str:
    """Kiểm tra tên trước khi ghi, dùng chung cho CV, Job và danh mục."""
    if not isinstance(value, str):
        raise ValueError("Tên kỹ năng phải là văn bản")
    if any(unicodedata.category(char).startswith("C") for char in value):
        raise ValueError("Tên kỹ năng chứa ký tự điều khiển không hợp lệ")
    value = clean_skill_name(value)
    if not any(char.isalnum() for char in value):
        raise ValueError("Tên kỹ năng phải có ít nhất một chữ hoặc số")
    if len(value) > 255 or len(normalize_skill_name(value)) > 255:
        raise ValueError("Tên kỹ năng và tên chuẩn hóa không được dài hơn 255 ký tự")
    return value
