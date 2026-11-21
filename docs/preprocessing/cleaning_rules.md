# Aturan cleaning

| Kondisi | Perlakuan | Alasan |
|---|---|---|
| Spasi di tepi kolom teks | Pangkas spasi. Pertahankan kapitalisasi, spasi internal, dan nol di depan identifier. | Spasi tepi muncul pada deskripsi sumber. Karakter internal dapat menjadi bagian dari nama atau kode. |
| Nilai teks kosong setelah trim atau mengandung karakter NUL | Jadikan null. | Nilai kosong tidak memberi informasi dan PostgreSQL tidak menerima NUL di kolom teks. |
| `Customer ID` kosong atau invalid | Simpan transaksi dengan `customer_id = pd.NA`. ID valid berisi digit ASCII dengan paling sedikit satu digit bukan nol. Akhiran desimal yang seluruhnya nol dihapus, misalnya `13085.0` menjadi `"13085"` dan `"00123.00"` menjadi `"00123"`. | Transaksi tanpa pelanggan tetap berguna untuk agregasi. ID yang sudah berubah sebelum Extract tidak dapat dipulihkan. |
| `Description` kosong | Simpan transaksi dengan `description = pd.NA`. | Deskripsi opsional dan dapat dilengkapi dari referensi produk bila tersedia. |
| `Invoice`, `StockCode`, atau `Country` kosong | Buang baris dan hitung alasan. | Output membutuhkan identitas invoice, kode barang, dan negara untuk pengelompokan. |
| Baris identik penuh | Hitung duplikat dengan `duplicated(keep="first")` sebelum normalisasi. Duplikat yang memenuhi semua aturan tetap disimpan. | Data sumber tidak memiliki ID baris yang dapat membedakan pembelian identik dari pengulangan input. |
| `Quantity` | Terima bilangan bulat bertanda dalam rentang `int64`. Buang baris dengan nilai hilang, pecahan, di luar rentang, atau tidak valid. Simpan nilai nol. | Kuantitas menyatakan jumlah unit. Kuantitas nol memberi nilai transaksi nol dan tetap dapat diaudit. |
| `InvoiceDate` | Terima `YYYY-MM-DD HH:MM:SS` atau pemisah `T`, dengan pecahan detik opsional hingga enam digit. Terima juga kolom datetime tanpa zona waktu dengan presisi maksimal mikrodetik. Buang nilai hilang atau tidak valid, termasuk waktu dengan offset. | Timestamp sumber tidak menyertakan zona waktu. Skema mempertahankan waktu sumber dengan presisi PostgreSQL. |
| `Price < 0` | Buang baris dan catat sebagai `negative_price`. | Harga satuan negatif memerlukan aturan bisnis tersendiri. CSV mentah tetap menyimpan baris tersebut untuk peninjauan. |
| `Price = 0` | Simpan dengan nilai transaksi nol. | Transaksi masih memiliki informasi invoice dan kuantitas. |
| `Price > 0` | Simpan jika baris lolos aturan lain. Buang harga hilang, invalid, atau tidak berhingga. Buang hasil perkalian yang melampaui rentang float. | Harga dan nilai transaksi harus bisa diproses sebagai angka berhingga. |
| Invoice berawalan `C` | Set `is_cancelled = True` setelah trim dengan pembandingan tanpa membedakan huruf besar dan kecil. | Prefiks invoice menyatakan pembatalan. Nilai asli identifier dipertahankan setelah trim. |
| `Quantity < 0` | Set `is_return = True`. Pertahankan kuantitas dan nilai transaksi bertanda. | Kuantitas negatif adalah indikator retur atau koreksi. Satu baris dapat memiliki kedua flag. |

Penyaringan mempertahankan urutan relatif baris yang lolos dan membuat indeks baru mulai dari nol. Satu baris bisa terkena beberapa aturan. `rows_rejected` menghitung baris unik, sedangkan `filter_reasons` menghitung setiap alasan secara terpisah.

Tipe selain DataFrame memicu `TypeError`. Input tanpa baris, label kolom ganda, kolom hilang atau tambahan, dan batch tanpa transaksi yang lolos memicu `ValueError`. Exception fatal diteruskan ke caller. Batch parsial berlanjut dengan baris yang lolos.
