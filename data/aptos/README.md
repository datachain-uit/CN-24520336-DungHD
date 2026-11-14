# APTOS 2019 — S0-v1.0 \| Kiểm toán và chia dữ liệu

> **Mục đích:** Tài liệu hướng dẫn sử dụng, kiểm chứng và tái lập bộ chia S0-v1.0 cho nghiên cứu phân độ bệnh võng mạc đái tháo đường (DR, 5 mức 0–4). Đây là **pipeline kiểm toán/chia tập dữ liệu**, không phải notebook huấn luyện 10 hàm loss.

## 1\. Bắt đầu nhanh — sử dụng bộ S0 đã có

Nếu mục tiêu chỉ là **train/đánh giá mô hình APTOS** thì **không cần chạy lại pipeline chia tập**:

1. Tải/đính kèm bộ dữ liệu APTOS 2019 gồm `train.csv` và thư mục `train_images/`.  
2. Đính kèm **toàn bộ thư mục S0-v1.0 này** dưới dạng Kaggle Dataset (hoặc tải về máy rồi đặt ở một thư mục cố định).  
3. Trong notebook huấn luyện, trỏ `SPLIT_ROOT` đến thư mục chứa `splits/`, `data_quality/`, `reproducibility/` của S0. Đọc phân chia **cố định** từ `splits/splits.json` hoặc `splits/partition_membership.csv`, không tự gọi lại `train_test_split`.  
4. Dùng đúng fold 0–4 và tách Train/Validation/Test theo file S0. Tập Test của S0 là phân hoạch nội bộ từ **APTOS train images**, **không phải** thư mục `test_images/` của cuộc thi Kaggle.  
5. Xác minh SHA-256 của `splits/splits.json` trước khi so sánh thực nghiệm (mục 5).

**SHA-256 chính thức để đối chiếu nội dung S0 đang được sử dụng:**

```
d53328d2a012c6b32d658b89494092b5deaf27b90258191362dc1695394e27ca
```

Không sửa `splits.json` hoặc thay đổi các ID phân hoạch chỉ để cập nhật tài liệu.

## 2\. Dữ liệu và kết quả hiện có

| Mục | Giá trị được ghi nhận trong bản S0 này |
| :---- | :---- |
| Nguồn | APTOS 2019 Blindness Detection — `train.csv` \+ `train_images/` |
| Số ảnh nguồn | 3.662 |
| Ảnh đủ điều kiện dùng trong S0 | 3.583 |
| Ảnh bị loại/cách ly (ID duy nhất) | 79 |
| Phân bố nhãn hợp lệ (0 / 1 / 2 / 3 / 4\) | 1.801 / 360 / 975 / 172 / 275 |
| Số fold | 5; seed \= `42` |
| Tỷ lệ mục tiêu mỗi fold | Train \~70%, Validation \~10%, Test \~20% |
| Nhật ký near-duplicate | 1.200 cặp: 1.000 cặp hạng đầu và 200 cặp lấy mẫu cố định từ hạng 1.001–10.000 |
| Kết quả phân loại trong nhật ký | A \= 16, C \= 1.184 (không ghi nhận B trong 1.200 cặp đã xem) |

Đây là bộ chia theo **nhóm ảnh/các quan hệ trùng đã xác nhận**, **không phải patient-level split** do không có định danh bệnh nhân đáng tin cậy. Vẫn tồn tại rủi ro ảnh gần trùng hoặc cùng mắt chưa được xác minh.

## 3\. Cấu trúc thư mục

```
APTOS_S0_v1.0/
├── README.md                         # Hướng dẫn bạn đang đọc
├── CHANGELOG.md                      # Lịch sử thay đổi, phê duyệt và việc còn mở
├── aptos-s0-qd22-n25-n26-v3 (3).ipynb # Notebook tạo/kiểm toán S0 (bản lưu trong Drive)
├── Báo cáo dataset                  # Báo cáo đọc kết quả (Google Docs trong Drive)
├── splits/
│   ├── splits.json                  # Nguồn phân hoạch Train/Val/Test chính
│   ├── partition_membership.csv     # Dễ tra cứu ID và phân hoạch theo fold
│   ├── partition_counts.csv         # Số lượng theo fold/nhãn
│   ├── split_report.json            # Thống kê và đánh giá cân bằng
│   ├── clusters.csv                 # Các cụm ảnh đã xác nhận
│   ├── acquisition_groups.csv       # Proxy nhóm thu nhận ảnh
│   ├── stratification_mapping.csv   # Ánh xạ phân tầng
│   ├── validation_selection.csv     # Thông tin chọn Validation
│   └── sensitivity_test_masks_preregistered.csv # Mask phân tích độ nhạy, không đổi split
├── data_quality/
│   ├── image_manifest.csv           # Danh mục ảnh và hash/metadata
│   ├── exact_duplicates.csv         # Ảnh trùng pixel
│   ├── near_duplicates.csv          # Tất cả ứng viên gần trùng
│   ├── near_duplicates_ranked.csv   # Thứ tự ưu tiên rà soát
│   ├── near_duplicate_review_v1.csv # Nhật ký 1.200 cặp do người nghiên cứu kiểm tra
│   ├── manual_review_01_pairs.csv   # Quyết định các cặp kiểm duyệt ban đầu
│   ├── manual_review_02_groups.csv  # Quyết định theo cụm
│   ├── conflict_decisions.csv       # Quyết định với nhãn xung đột
│   ├── label_difference_pairs.csv   # Các cặp khác Grade
│   ├── excluded_images.csv          # Ảnh loại khỏi S0
│   └── evidence/                   # NghiVan1, NghiVan2; cần lưu thêm bản PDF cố định
├── reproducibility/
│   ├── config.json                  # Tham số chạy pipeline khi tạo S0
│   ├── environment.json             # Thư viện và phiên bản ghi nhận
│   ├── input_fingerprints.json      # Dấu vân tay dữ liệu và preprocessing
│   ├── provenance.json              # Truy vết phiên chạy
│   ├── bounded_sample_plan.json     # Seed và 200 rank lấy mẫu
│   ├── sensitivity_preregistration.json
│   ├── s0_version_manifest.json     # Trạng thái và SHA chính
│   └── file_hashes.json            # Bảng SHA-256 các file đầu ra
├── reports/                         # Audit, kiểm thử, log, metadata baselines
└── figures/                         # Biểu đồ và contact sheet kiểm duyệt
```

**Lưu ý:** Các CSV `near_duplicates*.csv` rất lớn. Không xóa các file nguồn này chỉ vì không dùng khi train; chúng phục vụ kiểm toán/tái lập. Thư mục `cache/` của pipeline có thể bỏ khi bàn giao nếu đầu ra đã đầy đủ và hash đã kiểm tra.

## 4\. Tái lập từ đầu trên Kaggle (dành cho người kiểm toán)

### 4.1. Chuẩn bị

- Tạo Kaggle Notebook Python, gắn dataset cuộc thi **APTOS 2019 Blindness Detection** với `train.csv` và `train_images/`.  
- Gắn một Kaggle Dataset thứ hai chứa `data_quality/near_duplicate_review_v1.csv` đã hoàn thiện (hoặc chuẩn bị CSV nhật ký để kiểm duyệt mới).  
- Dùng notebook `aptos-s0-qd22-n25-n26-v3 (3).ipynb` trong thư mục này. Dữ liệu làm việc có thể lớn; kiểm tra dung lượng Kaggle trước khi Run All.  
- Notebook yêu cầu Python, `numpy`, `pandas`, `Pillow`, `scipy`, `scikit-learn >= 1.8`, `scikit-image`, `matplotlib`, `tqdm`. Phiên bản đã ghi nhận trong `reproducibility/environment.json`; so sánh môi trường khi cần tái lập chính xác.

### 4.2. Đặt đường dẫn trong CONFIG

Đặt **đường dẫn theo dataset thực tế** (ví dụ cấu hình trong notebook gốc):

```py
CONFIG['train_csv'] = '/kaggle/input/competitions/aptos2019-blindness-detection/train.csv'
CONFIG['image_dir'] = '/kaggle/input/competitions/aptos2019-blindness-detection/train_images'
CONFIG['output_dir'] = '/kaggle/working/aptos_s0_v1_work'
CONFIG['bounded_review_log_csv'] = '/kaggle/input/<your-s0-dataset>/near_duplicate_review_v1.csv'
```

Giữ `seed=42`, `n_folds=5`, `validation_fraction_remaining=0.125` và cấu hình đã ghi trong `reproducibility/config.json` nếu mục tiêu là tái lập S0. `ranked_pairs_csv` chỉ cần khi có bảng xếp hạng lịch sử riêng tương ứng; không tự khẳng định thứ tự mới là thứ tự đã xem trước đó.

### 4.3. Hai lượt xử lý để tái lập một cuộc kiểm toán mới

1. **DRAFT:** đặt `bounded_review_log_csv=None`, chạy notebook để tạo ranking và template; xem ảnh theo contact sheet hoặc `show_pair(pair_id)`; người kiểm toán thực sự ghi nhãn A/B/C, ngày xem, người xem và chứng cứ vào CSV.  
2. **REVIEWED/CANDIDATE:** gắn CSV đã hoàn thiện vào `bounded_review_log_csv`, chạy lại với cùng dữ liệu/config; kiểm tra `reports/validation_checks.json`, `reports/unit_tests.json`, `reports/bounded_review_summary.json`, `splits/partition_counts.csv` và các hash.  
3. **PHÊ DUYỆT/KHÓA:** chỉ xác nhận `approved_frozen` khi hồ sơ chứng cứ, bản split cũ và quyết định giảng viên được lưu đủ theo QĐ24. Không đổi `splits.json` chỉ để sửa metadata trạng thái.

**Nếu chỉ sử dụng bộ S0 hiện có:** không chạy DRAFT, không làm lại 1.200 lượt đánh giá; làm theo mục 1\.

### 4.4. Pipeline thực hiện những gì?

`train.csv` \+ `train_images/` → kiểm tra đầu vào → pixel SHA-256 và metadata → phát hiện trùng exact → tìm cặp near-duplicate bằng pHash/dHash (2 góc nhìn) → so khớp SSIM/NCC/IoU và xếp hạng → đối chiếu quyết định người xem → xử lý nhóm/nhãn xung đột → StratifiedGroupKFold → kiểm thử S0 → metadata shortcut baselines → báo cáo và biểu đồ.

Quy tắc QĐ22: ảnh **A** cùng ảnh nhưng xung đột nhãn thì loại toàn bộ cụm liên quan; A cùng nhãn và **B** đã xác nhận thì giữ cùng partition; **C** không tạo liên kết. Không được tự động gộp dựa chỉ trên độ tương đồng hash.

## 5\. Kiểm tra đầu ra và tính toàn vẹn

Trên Kaggle/Python, thay đường dẫn tương ứng:

```py
from hashlib import sha256
from pathlib import Path
p = Path('/kaggle/input/<your-s0-dataset>/splits/splits.json')
actual = sha256(p.read_bytes()).hexdigest()
expected = 'd53328d2a012c6b32d658b89494092b5deaf27b90258191362dc1695394e27ca'
assert actual == expected, f'S0 checksum mismatch: {actual}'
print('S0 checksum OK')
```

Trên Windows PowerShell có thể dùng `Get-FileHash .\splits\splits.json -Algorithm SHA256`.

Ngoài SHA, cần kiểm tra 5 fold, mỗi ảnh thuộc đúng 1 phân hoạch trong từng fold, không có liên kết A/B đã xác nhận đi qua ranh giới Train/Val/Test và tổng ảnh hợp lệ là 3.583. Đối chiếu `reports/validation_checks.json` và `reports/unit_tests.json`; các kết quả này đã ghi nhận PASS ở phiên nguồn, nhưng không thay thế việc kiểm tra khi dữ liệu đầu vào thay đổi.

## 6\. Hồ sơ kiểm toán và các việc còn mở (QĐ24)

- **Đã có:** nhật ký 1.200 cặp `near_duplicate_review_v1.csv`; thông tin `reviewer=Dũng`, `review_date=2026-11-04` và dẫn chứng NghiVan1 (rank 1–600), NghiVan2 (các rank còn lại), theo thông tin người nghiên cứu cung cấp.  
- **Chưa thể xác nhận hoàn tất từ thư mục hiện tại:** PDF bằng chứng cố định kèm SHA-256 (hiện thư mục `evidence/` chứa các tài liệu Google Docs gốc), kiểm chứng lại cặp hạng 186 theo ảnh, và kiểm tra chéo độc lập 65 cặp/các thống kê đồng thuận.  
- Manifest lưu trong Drive vẫn ở trạng thái `ready_for_archive` với `legacy_archived=false` và chưa gắn `advisor_approval_ref`. Giảng viên đã duyệt **có điều kiện** (Review-2026-11-07/QĐ24); cần hoàn thiện hồ sơ rồi mới xác nhận trạng thái cuối cùng. README không tự tạo ra phê duyệt.

Các ngày và người xem trong CSV là khai báo của người nghiên cứu; bản thân metadata này không thay thế bằng chứng xem ảnh hoặc lịch sử phiên bản. Không khẳng định không tồn tại ảnh gần trùng chưa phát hiện, và không khẳng định độc lập người bệnh.

## 7\. Nguồn, hướng dẫn thay đổi và bảo trì

- [Thư mục S0-v1.0 trên Google Drive](https://drive.google.com/drive/folders/1ker5gU1yys8mqxE5l0wp3JlwdNyGQBzP)  
- [Nhật ký `near_duplicate_review_v1.csv`](https://drive.google.com/file/d/11R6HYcIYiSxoQuFs0hyVhdIL8D9I7_lM/view)  
- [Báo cáo kiểm toán S0](https://docs.google.com/document/d/1avF8AUTxMTQhk_iHgKEaGP5_VBKY_bdy8rr_VAhgcbk/edit)  
- [Review-2026-11-07 (QĐ24)](https://docs.google.com/document/d/1kqn3fOBJ9D6O6ybT72SoE9T2r0gBTDhZ9igOX9Pp4_4/edit)  
- [Changelog](http://CHANGELOG.md)

**Quan trọng khi tái chạy:** notebook tạo S0 hiện có cell tự ghi `README.md` và `CHANGELOG.md` dạng ngắn. Nếu bấm Run All để tạo lại bộ output, hai file trong **output mới** sẽ bị ghi bằng bản tự sinh của notebook; sau đó hãy đưa bản tài liệu hướng dẫn này vào bộ bàn giao, hoặc sửa cell sinh tài liệu để dùng nội dung này. Không chỉnh sửa số liệu hay kết quả để khớp với hướng dẫn.

Mọi thay đổi làm ảnh hưởng nội dung file cần cập nhật lại hash tương ứng trong `reproducibility/file_hashes.json` và ghi lý do trong `CHANGELOG.md`. Nếu thay đổi ảnh, nhãn, phân hoạch hoặc thuật toán, đó là một phiên bản S0 mới — không ghi đè lên bản S0-v1.0 đang dùng để so sánh nghiên cứu.