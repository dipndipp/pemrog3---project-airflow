# Data Dictionary - Online Retail II

Sumber: `online_retail_II.csv` (hasil perhitungan langsung dari file, bukan estimasi).

- Jumlah baris: 1,067,371
- Jumlah kolom: 8
- Periode: 2009-12-01 07:45:00 sampai 2011-12-09 12:50:00

| Kolom | Tipe (pandas) | Keterangan | Missing | Nilai unik |
|---|---|---|---|---|
| Invoice | str | Nomor invoice; diawali "C" berarti pembatalan | 0 | 53,628 |
| StockCode | str | Kode produk | 0 | 5,305 |
| Description | str | Nama produk | 4,382 | 5,698 |
| Quantity | int64 | Jumlah barang per baris | 0 | 1,057 |
| InvoiceDate | str | Waktu transaksi | 0 | 47,635 |
| Price | float64 | Harga satuan | 0 | 2,807 |
| Customer ID | float64 | ID pelanggan | 243,007 | 5,942 |
| Country | str | Negara pelanggan | 0 | 43 |

## Catatan kualitas data (untuk Validate/Transform)

- Baris duplikat penuh: 34,335
- Invoice pembatalan (diawali "C"): 19,494 baris
- Quantity <= 0: 22,950 baris
- Price <= 0: 6,207 baris
- Customer ID kosong: 243,007 baris (22.8%)
