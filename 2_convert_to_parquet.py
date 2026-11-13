import pandas as pd
import json
import os

# path file JSON (sesuaikan dengan config kamu)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_GILIMANUK = os.path.join(BASE_DIR, "data", "rekap_cuaca_gilimanuk.json")
DATA_KETAPANG  = os.path.join(BASE_DIR, "data", "rekap_cuaca_ketapang.json")

OUTPUT_FILE = os.path.join(BASE_DIR, "data", "data_risalah.parquet")


def load_json(path, pelabuhan):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['pelabuhan'] = pelabuhan
    return df


# load data
df_g = load_json(DATA_GILIMANUK, "Gilimanuk")
df_k = load_json(DATA_KETAPANG, "Ketapang")

df_all = pd.concat([df_g, df_k]).sort_values("datetime")

if not df_all.empty:
    df_all.sort_values("datetime", inplace=True)
    
    # FIX ERROR: Paksa kolom 'jam' (dan kolom teks lain) menjadi string
    df_all['jam'] = df_all['jam'].astype(str)
    df_all['tanggal'] = df_all['tanggal'].astype(str)
    
    # Simpan ke Parquet
    df_all.to_parquet(OUTPUT_FILE, index=False, engine="pyarrow")
    print(f"✅ Konversi selesai: {OUTPUT_FILE}")
else:
    print("❌ Tidak ada data untuk dikonversi.")