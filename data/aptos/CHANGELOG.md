# CHANGELOG — APTOS 2019 S0


Tài liệu ghi những mốc có căn cứ trong pipeline S0 và các cập nhật hồ sơ. **Thay đổi tài liệu không đồng nghĩa thay đổi phân hoạch Train/Validation/Test.**


## 2026-11-14 — Chuẩn hóa tài liệu và nhật ký kiểm toán


### Changed
- Viết lại `README.md` theo cấu trúc hướng dẫn kiểu GitHub: giới thiệu, Quick Start, cây thư mục, chạy lại pipeline trên Kaggle, xác minh hash và các giới hạn khoa học.
- Chuẩn hóa `CHANGELOG.md` thành lịch sử thay đổi có thời điểm, phạm vi và việc còn mở.
- Nhật ký `data_quality/near_duplicate_review_v1.csv` được cập nhật theo khai báo của người nghiên cứu: 1.200 dòng có `reviewer=Dũng`, `review_date=2026-11-04`; hạng 1–600 dẫn NghiVan1, các hạng còn lại dẫn NghiVan2.
- Giữ nguyên cách đọc phân hoạch S0, ID ảnh, `splits/splits.json` và SHA-256 tham chiếu.


### Pending / Verification needed
- Bổ sung bản PDF cố định của NghiVan1/NghiVan2 và SHA-256; bảo đảm `evidence` trỏ đến bằng chứng lưu trữ ổn định thay vì chỉ Google Docs đang chỉnh sửa được.
- Kiểm tra lại cặp hạng 186 bằng ảnh; làm rõ những `review_notes` cũ còn không khớp với ngày kiểm tra mới khai báo.
- Hoàn tất kiểm tra chéo độc lập 65 cặp và báo cáo đồng thuận/kappa theo QĐ24.
- Xác minh bản chia cũ 13/10 đã được lưu trữ đúng, cập nhật trạng thái/approval trong manifest cùng bộ bằng chứng trước khi tuyên bố `approved_frozen`.


## 2026-11-07 — Phê duyệt có điều kiện theo QĐ24


- Giảng viên duyệt S0-v1.0 và giao thức thực nghiệm để bắt đầu Giai đoạn 1 **có điều kiện** (Review-2026-11-07, QĐ24–QĐ26).
- Điều kiện kèm theo gồm khôi phục bằng chứng, điền người/ngày xem, sửa cặp hạng 186, lưu nhật ký hoàn chỉnh, lưu bản chia cũ, kiểm tra chéo và cập nhật manifest.
- Trạng thái manifest thực tế vẫn là `ready_for_archive` cho đến khi có đủ điều kiện; quyết định duyệt có điều kiện không tự động chuyển file sang `approved_frozen`.


## 2026-11-03–04 — Xây dựng S0-v1.0 (QĐ22, N25, N26)


### Added
- Kiểm toán ảnh theo pixel SHA-256; xác định exact duplicates, near-duplicate candidates qua pHash/dHash và các chỉ số SSIM/NCC/IoU.
- Lập ranking cố định; kế hoạch xem 1.000 cặp hạng đầu cùng 200 cặp lấy mẫu seed `20261103` từ hạng 1.001–10.000; xuất nhật ký có thể truy vết và khoảng tin cậy Clopper–Pearson.
- Split duy nhất S0 bằng `StratifiedGroupKFold` 5 lượt, seed `42`, mỗi lượt mục tiêu khoảng 70/10/20; kiểm thử phân hoạch và shortcut baselines theo metadata.
- Đăng ký trước hai phân tích độ nhạy ở tập Test: mỗi pixel chỉ tính một lần; loại ảnh có liên kết pHash ≤ 4 chưa xác minh trực tiếp với Train **chỉ khi tính metric**, không sửa S0.
- Tệp `reproducibility/` lưu config, môi trường, fingerprint, provenance, SHA và trạng thái phiên.


### Rules and limitations
- QĐ22: A/exact cùng ảnh nhưng khác Grade → loại toàn bộ cụm liên quan; A cùng Grade/B đã xác nhận → giữ cùng partition; C → không nối nhóm.
- N25: `scikit-learn >= 1.8`, xử lý strata hiếm trong từng Grade, kiểm soát độ lệch phân bố.
- N26: quyết định A/B/C phải do người kiểm toán thực sự xem ảnh; không tự gán nhãn theo điểm tương đồng.
- Không có patient ID đáng tin cậy, nên **không** khẳng định patient-level disjoint.


## 2026-10-13 — Phiên chia tập cũ (legacy)


- Đây là bản tiền nhiệm của S0-v1.0, không sử dụng làm split chính thức khi so sánh 10 hàm loss.
- Bản ghi `s0_version_manifest.json` hiện còn `legacy_archived=false`; việc lưu trữ và xác minh bản legacy là **công việc chưa khép lại**, không được ghi là hoàn thành khi chưa có chứng cứ.


---


**S0 integrity:** SHA-256 của `splits/splits.json` = `d53328d2a012c6b32d658b89494092b5deaf27b90258191362dc1695394e27ca`.


**Chú ý:** Notebook tạo S0 có thể tự ghi lại README/CHANGELOG trong output khi Run All. Nếu tái chạy, cần giữ phiên bản tài liệu đã hoàn thiện ở đây hoặc đồng bộ lại cell sinh tài liệu trước khi bàn giao.