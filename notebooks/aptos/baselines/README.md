# APTOS 2019 — tái lập thực nghiệm 10 hàm loss (N32)

**Notebook huấn luyện duy nhất:** [`code-fixed.ipynb`](./code-fixed.ipynb).  
**Unit tests:** [`../../../test/test_aptos_mvp.py`](../../../test/test_aptos_mvp.py) (tính từ thư mục `notebooks/aptos/baselines/` thì đường dẫn đúng tới repo root là `../../../test/...`).  
**Bộ dữ liệu S0:** [`../../../data/aptos/README.md`](../../../data/aptos/README.md) — hướng dẫn kiểm toán/chia dữ liệu riêng; không tự tạo lại split khi huấn luyện.

> Tài liệu này mô tả cách chạy notebook đang lưu trong repository. Không coi log kiểm thử từ phiên bản cũ là bằng chứng rằng mọi thay đổi trong phiên bản mới đều đã được kiểm thử trên GPU.

## 1. Môi trường và phụ thuộc

- **Huấn luyện:** Kaggle Notebook, Python, **2 × NVIDIA Tesla T4**, CUDA hoạt động, đủ bộ nhớ/dung lượng lưu output.
- **Unit tests:** chạy trên CPU, không cần ảnh APTOS hay GPU. Đã ghi nhận **11/11 PASS** trên Windows/Python 3.12.10, pytest 9.2.0 vào 18/11/2026; log: `notebooks/aptos/evidence/pytest.log`.
- Cài phụ thuộc (nếu cần), từ thư mục gốc repository:

  ```bash
  python -m pip install -r notebooks/aptos/baselines/requirements.txt
  ```

- `requirements.txt` là **snapshot tham chiếu** lấy từ GPU preflight ngày 10/11/2026 (PyTorch `2.11.0+cu130`, torchvision `0.26.0+cu130`, CUDA 13.0) và pytest của log 18/11. Không tự động bảo đảm cùng CUDA trên mọi máy: trên Kaggle hãy **kiểm tra phiên bản torch/torchvision đang có trước khi thay thế**, vì cài lại có thể làm hỏng cấu hình GPU đang hoạt động. Lưu thêm `pip freeze`, phiên bản Python/CUDA/driver cho phiên FULL_TRAIN mới.

## 2. Chuẩn bị dữ liệu

Trên Kaggle, gắn **hai nguồn dữ liệu**:

1. **APTOS 2019 Blindness Detection**: cần `train.csv` và `train_images/` (3.662 ảnh train nguồn). **Không sử dụng** `test_images/` của cuộc thi làm Test nội bộ.
2. **S0-v1.0 đã phê duyệt**, với ba thư mục `splits/`, `data_quality/`, `reproducibility/`; `S0_ROOT` phải trỏ tới **thư mục cha** của cả ba. Dùng phân hoạch cố định trong `splits/splits.json`, không chia lại.

Ví dụ cây thư mục bên dưới `S0_ROOT`:

```text
S0_ROOT/
├── splits/
│   ├── splits.json
│   ├── clusters.csv
│   ├── acquisition_groups.csv
│   └── sensitivity_test_masks_preregistered.csv
├── data_quality/
│   ├── image_manifest.csv
│   └── excluded_images.csv
└── reproducibility/
    ├── s0_version_manifest.json
    ├── file_hashes.json
    └── sensitivity_preregistration.json
```

**S0 SHA-256 chính thức** của `splits/splits.json`:

```text
d53328d2a012c6b32d658b89494092b5deaf27b90258191362dc1695394e27ca
```

`FULL_TRAIN` từ chối S0 nếu manifest thiếu `status: "approved_frozen"`, `official: true`, hoặc `advisor_approval_ref`, và notebook kiểm SHA-256 của các tệp S0 cần thiết. Nếu sửa manifest trên GitHub, cần cập nhật đúng bản **Kaggle Dataset** (thư mục `/kaggle/input` là read-only), không bỏ qua bước kiểm hash.

## 3. Chạy trên Kaggle T4×2

1. Tạo Kaggle Notebook từ `notebooks/aptos/baselines/code-fixed.ipynb`.
2. Trong **Settings → Accelerator**, chọn **GPU T4 ×2**; gắn hai dataset ở mục 2.
3. Tại **cell 1 — CONFIG**, kiểm tra các biến:

   ```python
   MODE = 'MOCK_TRAIN'  # hoặc 'SANITY_CHECK', 'FULL_TRAIN'
   DATA_ROOT = '/kaggle/input/competitions/aptos2019-blindness-detection'
   S0_ROOT = '/kaggle/input/datasets/bondyyyyy/splitaptos/aptos'
   OUTPUT_ROOT = '/kaggle/working/output'
   RESUME_ROOT = None
   WEIGHTS_PATH = None
   ```

   Các đường dẫn trên là ví dụ theo notebook hiện tại; **xác minh đường dẫn mount thực tế** trong phiên Kaggle. `WEIGHTS_PATH=None` dùng cache/tải pretrained ResNet50 (cần Internet ở lần đầu); khi chạy offline, đặt đường dẫn tới file weights ResNet50 đúng phiên bản `resnet50-11ad3fa6.pth`.

4. Với một lần chạy chính thức, ghi nhận `GIT_COMMIT` đúng **phiên bản code thực thi**, và giữ `PROTOCOL_REF` gắn với QĐ24–QĐ25, QĐ28. Commit code trước khi chạy và không sửa thuật toán mà không ghi nhận commit mới. Giá trị `GIT_COMMIT` chỉ được **ghi vào metadata**, không tự xác minh notebook với GitHub.
5. Đổi `MODE` và chọn **Save Version → Save & Run All**; kiểm tra trạng thái/lỗi trong `training.log`.

| `MODE` | Mục đích | Đặc điểm |
|---|---|---|
| `MOCK_TRAIN` | Kiểm tra pipeline với ảnh thật | Fold 0; mỗi phương pháp 2 optimizer steps và 1 batch validation; không tuning/Test |
| `SANITY_CHECK` | Kiểm tra overfit và shuffled-label | A0/A8 overfit 32 ảnh Train tối đa 200 steps; A0 shuffled labels 10 epochs; ghi `sanity_report.json`; không checkpoint/resume |
| `FULL_TRAIN` | Thực nghiệm chính thức | Gate phê duyệt S0; chọn BN, tuning/selection lock, đánh giá 5 fold, tổng hợp OOF và so sánh |

Cấu hình gốc trong notebook gồm **seed 42**, batch size **32**, ResNet50, tối đa **50 epoch**, early stopping **patience 10**, AdamW, AMP theo CONFIG. Các phương pháp: `A0`, `A3`, `A4`, `A6`, `A8`, `A9`, `A11`, `A12`, `SLACE`, `CORN`.

## 4. Output và tiếp tục phiên chạy

Notebook tự tách theo `OUT = Path(OUTPUT_ROOT) / MODE`:

```text
/kaggle/working/output/
├── MOCK_TRAIN/
│   ├── config.json
│   ├── metric.json
│   └── training.log
├── SANITY_CHECK/
│   ├── sanity_report.json
│   └── training.log
└── FULL_TRAIN/
    ├── config.json
    ├── metric.json
    ├── training.log
    ├── checkpoints/
    ├── predictions/
    └── selection_lock.json  # có khi hoàn tất giai đoạn khóa lựa chọn
```

`config.json` lưu cấu hình, S0/hash/protocol và phần metadata `git_commit`, `protocol_ref` lồng dưới `s0`; `metric.json` chứa thông tin tương ứng tại `experiment.data`, cùng trạng thái/chỉ số thực nghiệm. Không suy ra rằng metric đã hoàn chỉnh khi chạy kết thúc sớm.

Để **resume**, gắn output trước đó làm Kaggle Dataset, rồi đặt `RESUME_ROOT` trỏ **đúng thư mục chứa `metric.json` của cùng MODE/config/S0**. Notebook sao chép dữ liệu từ nguồn resume sang `OUTPUT_ROOT/MODE` nếu nơi đó trống; không trộn output khác phiên. `SANITY_CHECK` không dùng resume.

## 5. Chạy unit tests và lưu bằng chứng

Từ **thư mục gốc repository**:

```bash
python -m pytest test/test_aptos_mvp.py -v --tb=short -p no:cacheprovider
```

Ghi log trên Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force notebooks/aptos/evidence
python -m pytest test/test_aptos_mvp.py -v --tb=short -p no:cacheprovider 2>&1 | Tee-Object -FilePath notebooks/aptos/evidence/pytest.log
```

Trên Linux/Kaggle (nếu clone đủ repository):

```bash
set -o pipefail
python -m pytest test/test_aptos_mvp.py -v --tb=short -p no:cacheprovider 2>&1 | tee notebooks/aptos/evidence/pytest.log
```

`test/test_aptos_mvp.py` đọc **chính các hàm trong notebook**, không chạy `main()`, không cần ảnh hay weights. Chỉ công bố PASS khi pytest đã **collect đủ test và tất cả đều PASS**. Log lịch sử ngày 10/11 cùng GPU preflight ở `notebooks/aptos/evidence/2026-11-10/`; chúng thuộc **phiên bản code cũ** và không thay cho kiểm thử GPU của bản refactor hiện tại.

## 6. Checklist tái lập và bàn giao

- [ ] Ghi rõ Git commit thực sự đã chạy; đồng bộ đúng notebook và mã `GIT_COMMIT` trong log kết quả.
- [ ] Ghi môi trường Python, torch/torchvision, CUDA, driver, 2×T4 và các package thực tế (`pip freeze`).
- [ ] Xác minh dataset APTOS, S0 `approved_frozen`, manifest và SHA-256 split; **không resplit**.
- [ ] Chạy unit tests; giữ `pytest.log` với kết quả PASS.
- [ ] Chạy MODE phù hợp; giữ `config.json`, `metric.json`, `training.log`, và khi áp dụng, các checkpoints/predictions/selection lock.
- [ ] Nếu resume, giữ nguyên config, S0 và phiên bản code tương ứng; lưu nguồn output resume.

**Phạm vi:** Tài liệu này hỗ trợ tái lập có kiểm soát; không cam kết tái hiện bitwise kết quả GPU trên cấu hình khác. Việc tái lập kết quả `FULL_TRAIN` cần thực sự chạy và lưu đầy đủ output, không thể suy ra từ `MOCK_TRAIN` hay unit tests.
