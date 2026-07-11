import pandas as pd
from pathlib import Path

file_path = Path("ind_pkg_elderly.xlsx")
if file_path.exists():
    df = pd.read_excel(file_path)
    # Group by Kecamatan Domisili and check the unique Desa Kelurahan Domisili for each
    grouped = df.groupby("Kecamatan Domisili")["Desa Kelurahan Domisili"].unique()
    for kec, desas in grouped.items():
        print(f"Kecamatan: {kec} (Total {len(desas)} desas)")
        print(desas)
        print("-" * 40)
else:
    print("File not found")
