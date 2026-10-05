from pathlib import Path

p = Path(r'D:\DoAnTotNghiep\frontend\src\pages\dashboard\DashboardPage.tsx')
b = p.read_bytes()
print('FIRST20', b[:20])
try:
    s = b.decode('utf-8')
    idx = s.find("toast.error")
    print('UTF8 OK', repr(s[idx-20:idx+80]))
    try:
        x = s.encode('latin-1').decode('utf-8')
        print('REPAIRED', repr(x[idx-20:idx+80]))
    except Exception as e:
        print('REPAIR_ERR', type(e), e)
except Exception as e:
    print('UTF8_FAIL', type(e), e)
    s = b.decode('latin-1')
    idx = s.find('toast.error')
    print('LATIN1', repr(s[idx-20:idx+80]))
