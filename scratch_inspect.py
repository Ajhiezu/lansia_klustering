import pandas as pd
from pathlib import Path

file_path = Path("ind_pkg_elderly.xlsx")
if file_path.exists():
    df = pd.read_excel(file_path)
    print("=== Unique Kecamatan values ===")
    print(df["Kecamatan Domisili"].unique())
    print("\n=== Unique Desa/Kelurahan values ===")
    print(df["Desa Kelurahan Domisili"].unique())
    print("\n=== Count per Kecamatan ===")
    print(df["Kecamatan Domisili"].value_counts())
else:
    print("File not found")
