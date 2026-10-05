from pathlib import Path

root = Path(r'D:\DoAnTotNghiep\frontend\src')
fixed = []

for path in list(root.rglob('*.ts')) + list(root.rglob('*.tsx')) + list(root.rglob('*.css')):
    try:
        text = path.read_text(encoding='utf-8')
    except Exception:
        continue

    text = text.lstrip('\ufeff')
    if not text:
        continue

    try:
        repaired = text.encode('latin-1').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        continue

    if repaired != text:
        path.write_text(repaired, encoding='utf-8')
        fixed.append(str(path.relative_to(root.parent)))

print('\n'.join(fixed))
print(f'FIXED_COUNT={len(fixed)}')
