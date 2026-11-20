import os
from pathlib import Path

import pandas as pd

# Root repo = satu level di atas folder src/. Bisa di-override lewat env var
# (di Docker/Airflow path-nya biasanya beda).
BASE_DIR = Path(os.getenv("PROJECT_DIR", Path(__file__).resolve().parents[1]))
CSV_PATH = Path(os.getenv("RETAIL_CSV_PATH", BASE_DIR / "data" / "raw" / "online_retail_II.csv"))
OUTPUT_PATH = Path(os.getenv("EXTRACT_OUTPUT_PATH", BASE_DIR / "data" / "interim" / "retail_raw.pkl"))

EXPECTED_COLUMNS = [
    "Invoice", "StockCode", "Description", "Quantity",
    "InvoiceDate", "Price", "Customer ID", "Country",
]


def read_csv(path=CSV_PATH):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset tidak ditemukan: {path}. Taruh online_retail_II.csv di folder data/."
        )
    last_err = None
    for enc in ("utf-8", "latin1"):
        try:
            return pd.read_csv(path, encoding=enc, dtype={"Invoice": str, "StockCode": str})
        except UnicodeDecodeError as e:
            last_err = e
        except pd.errors.EmptyDataError:
            raise ValueError(f"File CSV kosong: {path}")
        except pd.errors.ParserError as e:
            raise ValueError(f"File CSV tidak bisa di-parse (format rusak): {e}")
    raise ValueError(f"Encoding file tidak didukung: {last_err}")


def check_structure(df):
    missing_cols = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Kolom hilang di CSV: {missing_cols}")
    return {
        "rows": len(df),
        "columns": list(df.columns),
        "dtypes": df.dtypes.astype(str).to_dict(),
        "missing": df.isna().sum().to_dict(),
        "duplicates": int(df.duplicated().sum()),
    }


def extract_data(path=CSV_PATH, output_path=OUTPUT_PATH):
    """Baca CSV, cek struktur, simpan hasil mentah. Return path output (string)."""
    df = read_csv(path)
    info = check_structure(df)
    print(f"[EXTRACT] {info['rows']} baris, {len(info['columns'])} kolom")
    print(f"[EXTRACT] missing: {info['missing']}")
    print(f"[EXTRACT] duplikat: {info['duplicates']}")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_pickle(output_path)
    print(f"[EXTRACT] tersimpan di {output_path}")
    return str(output_path)


if __name__ == "__main__":
    extract_data()
