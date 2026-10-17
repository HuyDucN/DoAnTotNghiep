"""Tiện ích nhỏ để kiểm tra việc sửa chuỗi UTF-8 bị đọc sai encoding.

File này nằm trong thư mục scripts nên không được pytest xem là test của ứng
dụng. Mã chỉ chạy khi gọi trực tiếp bằng Python.
"""


def repair_text(value: str) -> str:
    """Khôi phục chuỗi UTF-8 đã bị đọc nhầm thành Latin-1."""
    try:
        return value.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def main() -> None:
    sample = "toast.error('KhÃ´ng thá»ƒ táº£i dá»¯ liá»‡u dashboard. Kiá»ƒm tra káº¿t ná»‘i server.');"
    print(sample)
    print("---")
    print(repair_text(sample))


if __name__ == "__main__":
    main()
