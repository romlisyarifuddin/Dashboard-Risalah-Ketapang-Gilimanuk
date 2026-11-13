import pandas as pd
from functools import lru_cache

@lru_cache(maxsize=1)
def load_data_parquet(path):

    df = pd.read_parquet(path)

    # pastikan tipe data optimal
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['pelabuhan'] = df['pelabuhan'].astype('category')

    weather_map = {
        "Cerah": "C",
        "Cerah Berawan": "CB",
        "Berawan": "B",
        "Berawan Tebal": "BT",
        "Hujan Ringan": "HR",
        "Hujan Sedang": "HS",
        "Hujan Lebat": "HL",
        "Hujan Sangat Lebat": "HSL"
    }

    if 'Kondisi_Cuaca' not in df.columns:
        df['Kondisi_Cuaca'] = df['kondisi_cuaca'].map(weather_map).fillna("TJ")

    return df

def load_event_excel(path):

    df = pd.read_excel(path, sheet_name=None)

    # gabungkan semua sheet
    df = pd.concat(df.values(), ignore_index=True)

    # =============================
    # BERSIHKAN TANGGAL
    # =============================
    df['Tanggal'] = pd.to_datetime(
        df['Tanggal'],
        errors='coerce',
        dayfirst=True
    )

    # =============================
    # BERSIHKAN JAM
    # =============================
    def fix_jam(jam):
        if pd.isna(jam):
            return None

        jam = str(jam).strip()

        # ubah 10.00 → 10:00
        jam = jam.replace('.', ':')

        # kalau cuma angka (misal 0.5 dari excel)
        try:
            if float(jam) < 1:
                total_minutes = float(jam) * 24 * 60
                hours = int(total_minutes // 60)
                minutes = int(total_minutes % 60)
                return f"{hours:02d}:{minutes:02d}"
        except:
            pass

        return jam

    df['Jam_fix'] = df['Jam ( WIB )'].apply(fix_jam)

    # =============================
    # GABUNG DATETIME
    # =============================
    df['datetime_event'] = pd.to_datetime(
        df['Tanggal'].astype(str) + ' ' + df['Jam_fix'],
        errors='coerce'
    )

    return df