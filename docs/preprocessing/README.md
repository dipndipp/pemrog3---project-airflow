# Validate & Transform Online Retail II

`validate_and_transform(df)` menerima DataFrame mentah dari Extract dan mengembalikan DataFrame transaksi dengan 11 kolom. Modul memeriksa struktur, mencatat temuan kualitas, menormalisasi nilai, dan menghitung nilai transaksi bertanda. Fungsi ini dapat dijalankan dengan pandas di luar Airflow dan PostgreSQL.

## Pemakaian dari root repo

```python
import logging

import pandas as pd

from src.extract import extract_data
from src.validate_transform import validate_and_transform

logging.basicConfig(level=logging.INFO)
raw_path = extract_data()
raw_df = pd.read_pickle(raw_path)
clean_df = validate_and_transform(raw_df)
```

Extract menulis `data/interim/retail_raw.pkl` secara default. Buka pickle dari proses Extract yang tepercaya. Untuk laporan terstruktur, panggil `assess_data_quality(raw_df)` dan simpan dictionary hasilnya sebagai JSON bila diperlukan. Pemanggilan terpisah ini menghitung ulang audit.

Extract memeriksa keberadaan delapan kolom wajib. Validate & Transform juga menolak label ganda dan kolom tambahan agar perubahan skema sumber terlihat. Urutan kolom raw bebas.

## Pengujian lokal

```powershell
python -m pytest tests/test_validate_transform.py -v
python -m pytest tests/test_extract.py -v
python -m pytest tests/ -v
```

Fixture pengujian dibuat dari DataFrame kecil. Uji handoff menulis CSV dan pickle ke direktori sementara.

## Dokumen

- [Laporan kualitas data](data_quality_report.md) memuat audit CSV lokal dan perbandingan dengan hasil Extract.
- [Aturan cleaning](cleaning_rules.md) menjelaskan alasan setiap perubahan dan kondisi fatal.
- [Skema output](output_schema.md) memuat contoh data dan kontrak untuk Zeva dan Noval.
- [Hasil pengujian](test_results.md) mencatat skenario, hasil pytest, dan verifikasi integrasi.
