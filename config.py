import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_GILIMANUK = os.path.join(BASE_DIR, "data", "rekap_cuaca_gilimanuk.json")
DATA_KETAPANG  = os.path.join(BASE_DIR, "data", "rekap_cuaca_ketapang.json")
DATA_PARQUET = os.path.join(BASE_DIR, "data", "data_risalah.parquet")
DATA_EVENT = os.path.join(BASE_DIR, "data", "Data Analisis Penutupan Pelabuhan.xlsx")