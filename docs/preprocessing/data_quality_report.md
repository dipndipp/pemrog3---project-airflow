# Audit kualitas CSV lokal

Audit dijalankan pada `data/raw/online_retail_II.csv` dengan `assess_data_quality(read_csv())`, menggunakan pembaca Extract Nadine. File memuat **1.067.371 baris dan 8 kolom**, dengan periode 1 Desember 2009 07:45:00 sampai 9 Desember 2011 12:50:00. Angka di halaman ini berasal dari file lokal.

## Nilai hilang dan tipe raw

| Kolom | Tipe pandas | Jumlah null | Persentase | Nilai unik non-null |
|---|---|---:|---:|---:|
| `Invoice` | `str` | 0 | 0% | 53.628 |
| `StockCode` | `str` | 0 | 0% | 5.305 |
| `Description` | `str` | 4.382 | 0,4105% | 5.698 |
| `Quantity` | `int64` | 0 | 0% | 1.057 |
| `InvoiceDate` | `str` | 0 | 0% | 47.635 |
| `Price` | `float64` | 0 | 0% | 2.807 |
| `Customer ID` | `float64` | 243.007 | 22,7669% | 5.942 |
| `Country` | `str` | 0 | 0% | 43 |

Jumlah nilai unik dihitung dengan `read_csv().nunique()` dan cocok untuk kedelapan kolom pada kamus data.

## Duplikat, pembatalan, dan distribusi tanda

| Metrik | Hasil hitung ulang | Kamus data Nadine |
|---|---:|---:|
| Total baris | 1.067.371 | 1.067.371 |
| Duplikat penuh setelah kemunculan pertama | 34.335 (3,2168%) | 34.335 |
| Baris dengan invoice berawalan C | 19.494 | 19.494 |
| Quantity ≤ 0 | 22.950 | 22.950 |
| Price ≤ 0 | 6.207 | 6.207 |
| Customer ID kosong | 243.007 | 243.007 |
| Description kosong | 4.382 | 4.382 |

Rujukan pembanding tersedia di [kamus data Nadine](../data_dictionary.md).

| Field | Negatif | Nol | Positif |
|---|---:|---:|---:|
| Quantity | 22.950 | 0 | 1.044.421 |
| Price | 5 | 6.202 | 1.061.164 |

Dari 19.494 baris berawalan C, 19.493 memiliki kuantitas negatif. Sebanyak 3.457 baris berkuantitas negatif memiliki invoice tanpa prefiks C. Konversi `Quantity`, `Price`, `InvoiceDate`, dan `Customer ID` masing-masing mencatat nol kegagalan pada nilai raw yang terisi. Normalisasi menghasilkan 243.007 ID pelanggan null dan 4.382 deskripsi null sebelum penyaringan.

## Dampak cleaning

| Metrik | Baris |
|---|---:|
| Input | 1.067.371 |
| Dibuang karena harga negatif | 5 |
| Dibuang karena alasan lain | 0 |
| Output | 1.067.366 |
| Duplikat raw yang tetap lolos | 34.335 |
| Baris harga nol yang tetap lolos | 6.202 |

Output memuat 22.950 baris berkuantitas negatif dan 19.494 baris berawalan C. Setelah penyaringan, 243.002 ID pelanggan dan 4.382 deskripsi tetap null.

`missing` memakai definisi null pandas pada DataFrame mentah. `invalid_conversions` menghitung nilai terisi yang menjadi null saat normalisasi atau parsing. Rasio duplikat memakai total baris raw sebagai penyebut. Angka audit mengukur baris transaksi, termasuk pengulangan, sehingga jumlahnya berbeda dari jumlah invoice unik. Data ini tidak menjelaskan penyebab bisnis untuk tiap koreksi, harga nol, atau pengulangan.
