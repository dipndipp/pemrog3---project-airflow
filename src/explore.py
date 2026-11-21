import pandas as pd
from extract import read_csv, check_structure

df = read_csv()
info = check_structure(df)
print("Jumlah baris:", info["rows"])
print("Kolom & tipe:\n", df.dtypes)
print("\nMissing value:\n", df.isna().sum())
print("\nDuplikat:", info["duplicates"])
print("\nRingkasan Quantity & Price:\n", df[["Quantity", "Price"]].describe())
print("\nInvoice cancel (C):", df["Invoice"].str.startswith("C").sum())
print("Top 5 negara:\n", df["Country"].value_counts().head(5))
