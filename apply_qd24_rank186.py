"""Áp dụng cập nhật QĐ24 lên chính CSV hiện có trong repository; không viết lại toàn bộ CSV."""
from pathlib import Path
import hashlib, json, sys
BASE=Path(__file__).resolve().parent / 'data' / 'aptos'
review=BASE/'data_quality'/'near_duplicate_review_v1.csv'
hashes=BASE/'reproducibility'/'file_hashes.json'
assert review.exists() and hashes.exists(), 'Hãy chạy script tại thư mục gốc repository sau khi giải nén ZIP.'
raw=review.read_bytes()
lines=raw.splitlines(keepends=True)
matched=[i for i,line in enumerate(lines) if line.startswith(b'top1000,186,')]
assert len(matched)==1, f'Không thấy chính xác một dòng rank=186: {len(matched)}'
i=matched[0]
old=b'Researcher reclassified previous U (suspected B) to A (same source image) on 2026-11-04. Grade 4/4: keep in same partition. Decision source: this conversation; images not independently re-verified.'
new=b'Initial U (suspected B) was revised to A on 2026-11-04. Original reviewer visually re-inspected both images on 2026-11-18 and confirmed A (same source image), Grade 4/4; keep together in same partition. This is a single-reviewer confirmation, not independent cross-check.'
row=lines[i]
for marker in (b'5bda2ed09e62',b'ba4d2c4b3039',b',A,D',b'2026-11-04'):
    assert marker in row, f'Không đúng mã ảnh/nhãn ban đầu, dừng để tránh ghi sai: {marker!r}'
if old in row:
    assert row.count(old)==1
    row=row.replace(old,new)
elif new in row:
    print('Dòng 186 đã được cập nhật trước đó; bỏ qua bước sửa ghi chú.')
else:
    raise AssertionError('Dòng 186 không khớp bản gốc mong đợi; vui lòng kiểm tra Git diff và cập nhật thủ công.')
oldurl=b'https://docs.google.com/document/d/1FO3GLoxIbg2xLZUOeuFFFyE2IDmn9iEgCrsrz53fiMw/edit?tab=t.0'
newurl=b'https://github.com/datachain-uit/CN-24520336-DungHD/blob/main/data/aptos/data_quality/evidence/NghiVan1.pdf'
if oldurl in row: row=row.replace(oldurl,newurl)
assert row.count(b',A,D')==1, 'Nhãn phải vẫn là A'
lines[i]=row
newraw=b''.join(lines)
assert len(lines)==len(raw.splitlines(keepends=True)), 'Số dòng CSV bị thay đổi'
assert all(a==b for k,(a,b) in enumerate(zip(raw.splitlines(keepends=True),lines)) if k!=i), 'Các dòng khác thay đổi!'
review.write_bytes(newraw)
h=json.loads(hashes.read_text(encoding='utf-8-sig'))
for relative in ['README.md','CHANGELOG.md','data_quality/near_duplicate_review_v1.csv']:
    p=BASE/relative
    value=hashlib.sha256(p.read_bytes()).hexdigest()
    h['sha256'][relative]=value
    print(f'{relative}: {value}')
assert h['sha256']['splits/splits.json']=='d53328d2a012c6b32d658b89494092b5deaf27b90258191362dc1695394e27ca'
hashes.write_text(json.dumps(h,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('QĐ24: cập nhật 1 dòng rank=186, README, CHANGELOG và SHA-256 thành công.')
