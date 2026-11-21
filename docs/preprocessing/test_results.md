# Hasil pengujian

Pengujian dijalankan di Windows dengan Python 3.12.14, pandas 3.0.1, dan pytest 9.2.0. Karena `python` tidak ada di PATH sesi, perintah memakai executable Python lokal secara langsung dan menambahkan lokasi instalasi pytest temporer ke `PYTHONPATH`.

| Perintah | Passed | Failed | Skipped |
|---|---:|---:|---:|
| `python -m pytest tests/test_validate_transform.py -v` | 34 | 0 | 0 |
| `python -m pytest tests/test_extract.py -v` | 7 | 0 | 0 |
| `python -m pytest tests/ -v` | 41 | 0 | 0 |

Suite penuh mencakup dua file pengujian di atas.

## Skenario Validate & Transform

| Skenario | Ekspektasi | Hasil aktual | Status |
|---|---|---|---|
| Struktur valid, urutan kolom raw berbeda | Semua kolom dikenali. | Log validasi mengonfirmasi satu baris. | Lulus |
| Tipe salah, batch kosong, kolom hilang, kolom tambahan, label ganda | Exception fatal menyebut penyebab. | Masing-masing menghasilkan `TypeError` atau `ValueError` yang sesuai. | Lulus |
| Kuantitas invalid, kosong, pecahan, atau melewati batas | Audit menghitung alasan dan menyaring baris. | Satu baris invalid terfilter pada tiap kasus dan baris valid sama dengan hasil input kontrol. | Lulus |
| Harga invalid, tak berhingga, boolean, negatif, atau nilai transaksi meluap | Filter dan hitung sesuai alasan. | Harga negatif terhitung terpisah dari konversi gagal dan overflow. | Lulus |
| Tanggal invalid, ambigu, atau berzona waktu | Tanggal yang tidak sesuai kontrak dikeluarkan. | Setiap baris terhitung pada `invalid_or_missing_invoice_date`. | Lulus |
| Invoice, stock code, atau negara kosong | Audit mencatat field wajib yang hilang. | Baris invalid terfilter dengan nama field yang tepat. | Lulus |
| Seluruh baris terfilter | `ValueError` diteruskan. | Exception menyertakan alasan harga negatif untuk batch uji. | Lulus |
| Deskripsi dan ID pelanggan opsional | Baris bertahan dan nilai kosong menjadi null. | Ketiga baris bertahan. `" 00123.00 "` menjadi `"00123"`. | Lulus |
| Duplikat penuh | Hitung duplikat di raw dan pertahankan yang lolos. | Dua pengulangan tercatat, satu lolos dan satu ikut terfilter karena harga negatif. | Lulus |
| Pembatalan, kuantitas negatif, harga nol, dan kuantitas nol | Flag independen dan jumlah bertanda benar. | Flag sesuai tiap transaksi, termasuk saat keduanya aktif. Harga atau kuantitas nol menghasilkan total nol. | Lulus |
| Audit dan log | Audit dapat diserialisasi. Alasan per baris bisa tumpang tindih. | JSON mempertahankan angka audit, lima pemicu aturan menghasilkan dua baris ditolak, dan log memuat tahapan serta alasan. | Lulus |
| Skema dan total | Urutan, tipe, nol di depan ID, timestamp dan hasil perkalian sesuai kontrak. | Seluruh 11 tipe sesuai. Contoh `3 × 2,5` menghasilkan `7,5`. | Lulus |
| Mikrodetik dan batas BIGINT | Presisi waktu dan kuantitas valid dipertahankan. | Teks ISO dan datetime sama-sama mempertahankan enam digit. Batas atas BIGINT lolos dari input teks maupun `uint64`, dan nilai di atasnya terfilter. | Lulus |
| Repeatability dan mutasi | Pemrosesan ulang raw menghasilkan tabel identik. Input tetap sama. | Hasil pipeline berulang sama dengan komposisi fungsi publik. Pemanggilan memakai output memicu penolakan skema raw. | Lulus |
| Pickle sintetis dari Extract | Extract mengembalikan path string dan output pickle dapat digunakan. | Data setelah round-trip cocok dengan hasil DataFrame sintetis langsung. | Lulus |

## Simulasi dengan CSV asli

`extract_data(output_path=...)` membaca 1.067.371 baris dari CSV lokal dan menulis pickle di direktori sementara. `pd.read_pickle` lalu memasok input ke `validate_and_transform`, yang menghasilkan 1.067.366 baris. Pemeriksaan programatis mengonfirmasi tipe 11 kolom, seluruh harga output nonnegatif, dan `total_amount == quantity * unit_price` pada setiap baris output.
