# Skema output dan handoff

Urutan kolom di bawah sesuai dengan DataFrame hasil `validate_and_transform`.

| Kolom | Tipe pandas | Tipe PostgreSQL yang sesuai | Nullable |
|---|---|---|---|
| `invoice_no` | `string` | `TEXT` | Tidak |
| `stock_code` | `string` | `TEXT` | Tidak |
| `description` | `string` | `TEXT` | Ya |
| `quantity` | `int64` | `BIGINT` | Tidak |
| `invoice_date` | `datetime64[us]` | `TIMESTAMP WITHOUT TIME ZONE` | Tidak |
| `unit_price` | `float64` | `DOUBLE PRECISION` | Tidak |
| `customer_id` | `string` | `TEXT` | Ya |
| `country` | `string` | `TEXT` | Tidak |
| `total_amount` | `float64` | `DOUBLE PRECISION` | Tidak |
| `is_cancelled` | `bool` | `BOOLEAN` | Tidak |
| `is_return` | `bool` | `BOOLEAN` | Tidak |

Contoh sintetis dengan identifier yang mengandung nol di depan dan nilai pelanggan null.

| invoice_no | stock_code | description | quantity | invoice_date | unit_price | customer_id | country | total_amount | is_cancelled | is_return |
|---|---|---|---:|---|---:|---|---|---:|---|---|
| `000123` | `0007A` | GLASS MUG | 3 | 2009-12-01 07:45:00 | 2.50 | `13085` | United Kingdom | 7.50 | false | false |
| `C000124` | `0007A` | NULL | -2 | 2009-12-01 08:00:00 | 2.50 | NULL | United Kingdom | -5.00 | true | true |

## Zeva · Load

- Ubah `pd.NA` pada kolom nullable menjadi `None` saat binding parameter untuk menghasilkan SQL `NULL`. Bind flag sebagai boolean dan simpan identifier sebagai teks.
- Simpan `invoice_date` sebagai timestamp tanpa zona waktu. Jika tahap berikutnya membutuhkan UTC, tetapkan dulu zona asal bersama tim.
- `total_amount = quantity * unit_price` memakai floating point tanpa pembulatan finansial. Untuk kebutuhan perhitungan desimal eksak, tim perlu menyepakati presisi serta sumber nilai desimal sebelum menetapkan definisi finansial.
- Retur, pembatalan, harga nol, dan duplikat yang lolos tetap ada. Lima baris harga negatif terfilter pada CSV lokal. Gunakan flag dan tanda kuantitas untuk menetapkan definisi penjualan, pembatalan, retur, dan nilai bersih. Kedua flag dapat aktif pada baris yang sama.
- Untuk retry idempoten, gunakan ID batch sumber yang stabil, misalnya checksum file raw, lalu ganti isi batch itu secara atomik dalam satu transaksi. Serialisasikan Load yang memakai ID batch sama. `invoice_no` dan pasangan `(invoice_no, stock_code)` dapat berulang. Deduplikasi berdasarkan gabungan kolom bisnis akan mengurangi jumlah baris sah yang identik.

## Noval · Airflow

- Panggil `validate_and_transform(pd.read_pickle(raw_path))` dengan path tepercaya yang dikembalikan Extract. Hasil fungsi adalah DataFrame sesi Python.
- Tangkap log `[VALIDATE]`, `[QUALITY]`, `[CLEAN]`, `[TRANSFORM]`, dan `[PIPELINE]` di level INFO. Alasan penyaringan muncul pada level WARNING. `assess_data_quality(raw_df)` dapat dipakai untuk artefak JSON bila monitoring perlu angka terstruktur.
- Biarkan `TypeError` dan `ValueError` fatal sampai ke Airflow agar task berstatus failed. Kesalahan membuka pickle juga diteruskan oleh adapter task.
- Jika Validate & Transform dan Load berjalan sebagai task berbeda, simpan hasil sebagai pickle pada volume bersama atau penyimpanan yang bisa diakses keduanya. Gunakan path khusus untuk setiap run, publikasikan file setelah penulisan selesai, dan teruskan hanya path atau metadata kecil melalui XCom. Load membuka artefak dengan `pd.read_pickle`.
- Retry memproses ulang pickle mentah. Pemanggilan terhadap skema hasil transformasi memicu `ValueError` karena kontrak fungsi utama menerima skema Extract.
