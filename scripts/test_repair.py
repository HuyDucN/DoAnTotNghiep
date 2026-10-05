sample = "toast.error('KhÃ´ng thá»ƒ táº£i dá»¯ liá»‡u dashboard. Kiá»ƒm tra káº¿t ná»‘i server.');"
print(sample)
print('---')
repaired = sample.encode('latin-1').decode('utf-8')
print(repaired)
