# CHANGELOG — APTOS 2019 S0

Tài liệu ghi những mốc có căn cứ trong pipeline S0 và các cập nhật hồ sơ. **Thay đổi tài liệu không đồng nghĩa thay đổi phân hoạch Train/Validation/Test.** Các mục lịch sử mô tả trạng thái tại thời điểm tương ứng; xem mốc mới nhất để biết trạng thái hiện hành.

## 2026-11-18 — Bổ sung bằng chứng PDF, xác nhận hạng 186 và đồng bộ hồ sơ QĐ24

### Added
- Lưu bản PDF cố định bên cạnh bản DOCX gốc của hai tài liệu kiểm duyệt thủ công: [`data_quality/evidence/NghiVan1.pdf`](data_quality/evidence/NghiVan1.pdf) và [`data_quality/evidence/NghiVan2.pdf`](data_quality/evidence/NghiVan2.pdf).
- Ghi SHA-256 của từng PDF (chữ thường) vào `README.md` và `reproducibility/file_hashes.json`:
  - `NghiVan1.pdf`: `e1b597ac6aab834009379779f7ba44cbac0f99f3ea4eef499cfc50184d32c62a`
  - `NghiVan2.pdf`: `9bb3e71aeceb06c50d2f79fcd5cc8e2553411aa63335f4918596d2a2b3a29eef`
- Minh chứng commit: [`cfbe91b`](https://github.com/datachain-uit/CN-24520336-DungHD/commit/cfbe91b5b90dbf0c7fd68c3ef2bbf271e7ee4958).

### Changed / Verified
- Manifest `reproducibility/s0_version_manifest.json` hiện có `version=S0-v1.0`, `status=approved_frozen`, `official=true`, `advisor_approval_ref="Review-2026-11-07 – QĐ24"` và `legacy_archived=true`; thông tin này đã được kiểm tra trong nhánh `main`. Các phát biểu ở mốc 07/11 và 14/11 bên dưới là **ghi nhận lịch sử trước khi cập nhật**, không phải trạng thái hiện tại.
- `README.md` hiện mô tả tình trạng phê duyệt và hai PDF bằng chứng. `reproducibility/file_hashes.json` cần lưu SHA-256 mới của CHANGELOG này sau khi chỉnh sửa (được cung cấp cùng bản cập nhật).
- **Không chỉnh sửa** `splits/splits.json`, danh sách ID của các fold hoặc cấu trúc Train/Validation/Test. SHA-256 chính thức của split vẫn là `d53328d2a012c6b32d658b89494092b5deaf27b90258191362dc1695394e27ca`.
- Người nghiên cứu xác nhận **đã trực tiếp xem 1.200 cặp ảnh trong một ngày**. Nhật ký hiện ghi `reviewer=Dũng`, `review_date=2026-11-04`. Đây là xác nhận của người nghiên cứu; việc đối chiếu mốc ngày cụ thể với lịch sử tạo/chỉnh sửa NghiVan1/NghiVan2 theo yêu cầu của giảng viên vẫn chưa được hoàn tất. Không tự sửa ngày trong CSV nếu chưa có căn cứ.

### Pending / Verification needed
- **Cặp hạng 186 đã được cùng người nghiên cứu xem lại ngày 18/11:** xác nhận A cho hai ảnh Grade 4/4 (ID `5bda2ed09e62` và `ba4d2c4b3039`); sẽ sửa ghi chú CSV để bỏ thông tin cũ 'images not independently re-verified' và chỉ rõ đây là xác minh cùng người, không phải người đánh giá thứ hai.
- Người nghiên cứu xác nhận trực tiếp xem toàn bộ 1.200 cặp trong một ngày. CSV đang ghi ngày 04/11, trong khi các tài liệu NghiVan có mốc tạo 03/11; chưa có bằng chứng độc lập phân định chính xác mốc. Không đổi đồng loạt `review_date` chỉ theo suy đoán. Cần xác minh lịch sử/giải trình với giảng viên; cập nhật liên kết `evidence` tới PDF cố định khi thích hợp.
- **Kiểm tra chéo độc lập 65 cặp** theo QĐ24: người nghiên cứu hiện là người đánh giá duy nhất, chưa có reviewer thứ hai. **Kính đề nghị giảng viên** xem xét hỗ trợ bố trí người kiểm tra độc lập hoặc phê duyệt phương án thay thế: cùng người thực hiện lượt đánh giá mù sau khoảng thời gian cách biệt, tính intra-rater agreement/Cohen's kappa theo hai lượt và nêu rõ hạn chế. Lựa chọn thay thế **không tương đương** inter-rater agreement; chưa được giảng viên phê duyệt nên tiếp tục Doing/Blocked.
- Bổ sung đường dẫn Drive cố định tới `near_duplicates_ranked.csv` và đối chiếu SHA-256 với `ranked_pairs_sha256` trong manifest.
- Rà soát tính đầy đủ của hồ sơ bằng chứng để kết thúc toàn bộ các tiểu mục QĐ24; **không suy diễn rằng `approved_frozen` đồng nghĩa tất cả công việc QĐ24 đã hoàn thành**.

## 2026-11-14 — Chuẩn hóa tài liệu và nhật ký kiểm toán

### Changed
- Viết lại `README.md` theo cấu trúc hướng dẫn kiểu GitHub: giới thiệu, Quick Start, cây thư mục, chạy lại pipeline trên Kaggle, xác minh hash và các giới hạn khoa học.
- Chuẩn hóa `CHANGELOG.md` thành lịch sử thay đổi có thời điểm, phạm vi và việc còn mở.
- Nhật ký `data_quality/near_duplicate_review_v1.csv` được cập nhật theo khai báo của người nghiên cứu: 1.200 dòng có `reviewer=Dũng`, `review_date=2026-11-04`; hạng 1–600 dẫn NghiVan1, các hạng còn lại dẫn NghiVan2.
- Giữ nguyên cách đọc phân hoạch S0, ID ảnh, `splits/splits.json` và SHA-256 tham chiếu.

### Pending tại thời điểm 14/11 (xem cập nhật 18/11 ở trên)
- Bổ sung bản PDF cố định của NghiVan1/NghiVan2 và SHA-256; bảo đảm `evidence` trỏ đến bằng chứng lưu trữ ổn định thay vì chỉ Google Docs đang chỉnh sửa được. **PDF/SHA-256 đã bổ sung ngày 18/11; cột evidence trong CSV vẫn cần rà soát.**
- Kiểm tra lại cặp hạng 186 bằng ảnh; làm rõ những `review_notes` cũ còn không khớp với ngày kiểm tra mới khai báo.
- Hoàn tất kiểm tra chéo độc lập 65 cặp và báo cáo đồng thuận/kappa theo QĐ24.
- Xác minh bản chia cũ 13/10 đã được lưu trữ đúng, cập nhật trạng thái/approval trong manifest cùng bộ bằng chứng trước khi tuyên bố `approved_frozen`. **Manifest hiện đã `approved_frozen` và `legacy_archived=true`; hồ sơ còn việc mở như nêu ở trên.**

## 2026-11-07 — Phê duyệt có điều kiện theo QĐ24

- Giảng viên duyệt S0-v1.0 và giao thức thực nghiệm để bắt đầu Giai đoạn 1 **có điều kiện** (Review-2026-11-07, QĐ24–QĐ26).
- Điều kiện kèm theo gồm khôi phục bằng chứng, điền người/ngày xem, sửa cặp hạng 186, lưu nhật ký hoàn chỉnh, lưu bản chia cũ, kiểm tra chéo và cập nhật manifest.
- **Ghi nhận lịch sử:** ở thời điểm được đánh giá trước các cập nhật sau đó, manifest từng là `ready_for_archive`. **Trạng thái hiện hành** trên GitHub là `approved_frozen` theo QĐ24; xem mục cập nhật 18/11.

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
- **Ghi nhận lịch sử:** bản ghi `s0_version_manifest.json` từng có `legacy_archived=false`; bản hiện tại đã có `legacy_archived=true`. Việc kiểm tra lại đầy đủ bằng chứng bản lưu trữ cũ là một bước kiểm toán riêng nếu giảng viên yêu cầu.

---

**S0 integrity:** SHA-256 của `splits/splits.json` = `d53328d2a012c6b32d658b89494092b5deaf27b90258191362dc1695394e27ca`.

**Chú ý:** Notebook tạo S0 có thể tự ghi lại README/CHANGELOG trong output khi Run All. Nếu tái chạy, cần giữ phiên bản tài liệu đã hoàn thiện ở đây hoặc đồng bộ lại cell sinh tài liệu trước khi bàn giao.
