import re
import csv
import os
from datetime import datetime
import pandas as pd

# ==============================================
# KONFIGURASI
# ==============================================
input_file = r"C:\Users\HYPE AMD\Documents\KERJA\Dashboad Risalah\data\Chat WhatsApp dengan Info Cuaca Ketapang - Gilimanuk.txt"
output_excel = r"C:\Users\HYPE AMD\Documents\KERJA\Dashboad Risalah\data"

# tanggal cutoff: hanya ambil data >= tanggal ini
cutoff_date = datetime.strptime("01/01/26 00.00", "%d/%m/%y %H.%M")

# ==============================================
# FUNGSI HELPER
# ==============================================
def normalize_number_string(s):
    if not s:
        return None
    s = str(s).strip().replace(',', '.')
    sign = ''
    if s.startswith('-'):
        sign = '-'
        s = s[1:]
    s = re.sub(r'[^0-9.]', '', s)
    if s == '':
        return None
    parts = s.split('.')
    if len(parts) == 1:
        integer = parts[0] or '0'
        normalized = integer
    else:
        integer = ''.join(parts[:-1]) or '0'
        decimal = parts[-1]
        normalized = integer + '.' + decimal
    return sign + normalized

def safe_float(s):
    num_s = normalize_number_string(s)
    if num_s is None:
        return None
    try:
        return float(num_s)
    except Exception:
        return None
    
def parse_block(text):
    res = {
        "tanggal": None, "jam": None, "datetime": None, "pelabuhan": None,
        "kondisi_cuaca": None,
        "angin_arah": None, "angin_kecepatan_knots": None,
        "gelombang_min_m": None, "gelombang_max_m": None,
        "arus_arah": None, "arus_min_mps": None, "arus_max_mps": None,
        "arus_min_knots": None, "arus_max_knots": None,
        "peringatan_dini": None,
        "visibility_m": None
    }

# tanggal
    m = re.match(r"(\d{2}/\d{2}/\d{2})", text)
    if m:
        res["tanggal"] = m.group(1)

    # jam
    m = re.search(r"Pukul\s*([0-9]{1,2}[.:][0-9]{2})", text, re.IGNORECASE)
    if m:
        res["jam"] = m.group(1).replace(':', '.').strip()

    # pelabuhan
    m = re.search(r"Pelabuhan\s+([A-Za-z]+)", text, re.IGNORECASE)
    if m:
        res["pelabuhan"] = m.group(1).strip()

    # kondisi cuaca
    m = re.search(r"Kondisi Cuaca\s*:\s*([^\n\r*]+)", text, re.IGNORECASE)
    if m:
        res["kondisi_cuaca"] = m.group(1).strip()

    # arah angin
    m = re.search(r"dari\s+([A-Za-z\s\-]+?)\s+dengan", text, re.IGNORECASE)
    if m:
        res["angin_arah"] = m.group(1).strip()

    # kecepatan angin (dengan atau tanpa "maksimum")
    m = re.search(r"kecepatan(?: maksimum)?\s*([0-9\.,]+)", text, re.IGNORECASE)
    if m:
        res["angin_kecepatan_knots"] = safe_float(m.group(1))

    # gelombang
    m = re.search(r"gelombang.*?([0-9\.,]+)\s*[–\-]\s*([0-9\.,]+)\s*m", text, re.IGNORECASE)
    if m:
        res["gelombang_min_m"] = safe_float(m.group(1))
        res["gelombang_max_m"] = safe_float(m.group(2))

    # arus
    m = re.search(
    r"Arus.*?menuju(?:\s+arah)?\s*([A-Za-z\s\-]+?)\s+dengan\s+kecepatan\s*([0-9\.,]+)\s*[–\-]\s*([0-9\.,]+)\s*m/s",
    text,
    re.IGNORECASE)

    if m:
        res["arus_arah"] = m.group(1).strip()
        res["arus_min_mps"] = safe_float(m.group(2))
        res["arus_max_mps"] = safe_float(m.group(3))

        # konversi ke knot
        if res["arus_min_mps"] is not None:
            res["arus_min_knots"] = round(res["arus_min_mps"] * 1.94384, 2)

        if res["arus_max_mps"] is not None:
            res["arus_max_knots"] = round(res["arus_max_mps"] * 1.94384, 2)
        
    # visibility / jarak pandang
    m = re.search(
        r"Jarak\s*Pandang.*?([0-9]{3,5})\s*m",
        text,
        re.IGNORECASE
    )

    if m:
        res["visibility_m"] = int(m.group(1))

    # peringatan dini (PD1, PD2, PD3)
    m = re.search(
        r"PD[123]\)?\s*[:\-]?\s*(Awas|Waspada|Siaga)",
        text,
        re.IGNORECASE
    )

    if m:
        res["peringatan_dini"] = m.group(1).capitalize()

    return res

# ==============================================
# PROSES UTAMA
# ==============================================
print("=== PROSES OTOMATIS REKAP CUACA ===")
print("🔍 Memfilter chat berdasarkan tanggal cutoff...")

if not os.path.exists(input_file):
    print(f"❌ File tidak ditemukan: {input_file}")
    raise SystemExit

with open(input_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

filtered_lines = []
for line in lines:
    try:
        date_str = line.split(" - ")[0]
        date_obj = datetime.strptime(date_str, "%d/%m/%y %H.%M")
        if date_obj >= cutoff_date:
            filtered_lines.append(line)
    except Exception:
        if filtered_lines:
            filtered_lines.append(line)

if not filtered_lines:
    print("⚠️ Tidak ada data yang cocok ditemukan pada tahap filter.")
    raise SystemExit

content = "".join(filtered_lines)

print("📖 Memproses blok chat...")

# regex diperlonggar agar tangkap semua blok dengan format tanggal di awal baris
blocks = re.split(r"(?=\d{2}/\d{2}/\d{2}\s+\d{2}[.:]\d{2}\s*-)", content)

parsed_data = []
for block in blocks:
    if not block.strip():
        continue
    data = parse_block(block)
    if data["pelabuhan"]:
        parsed_data.append(data)
        print(f"✅ {data['tanggal']} {data['jam']} {data['pelabuhan']} tersimpan")

if not parsed_data:
    print("⚠️ Tidak ada data yang cocok ditemukan setelah parsing.")
    raise SystemExit


df_all = pd.DataFrame(parsed_data)
df_all["datetime"] = pd.to_datetime(
    df_all["tanggal"] + " " + df_all["jam"],
    format="%d/%m/%y %H.%M",
    errors="coerce"
)
cols = list(df_all.columns)
cols.insert(cols.index("pelabuhan"), cols.pop(cols.index("datetime")))
df_all = df_all[cols]

df_all = df_all[df_all["pelabuhan"].isin(["Ketapang", "Gilimanuk"])]

print("\n💾 Menyimpan ke JSON (Menggabungkan dengan data lama jika ada)...")

output_dir = output_excel
os.makedirs(output_dir, exist_ok=True)

json_ketapang = os.path.join(output_dir, "rekap_cuaca_ketapang.json")
json_gilimanuk = os.path.join(output_dir, "rekap_cuaca_gilimanuk.json")

def save_and_append_json(df_new, file_path):
    if df_new.empty:
        return 0
    
    # Jika file JSON sudah ada, baca dan gabungkan
    if os.path.exists(file_path):
        try:
            df_old = pd.read_json(file_path, orient="records")
            # Gabungkan data lama dan baru
            df_combined = pd.concat([df_old, df_new], ignore_index=True)
            # Hapus duplikat berdasarkan 'datetime' dan 'pelabuhan' (atau kolom lain yang unik)
            df_combined.drop_duplicates(subset=['datetime', 'pelabuhan'], keep='last', inplace=True)
            # Urutkan berdasarkan datetime agar rapi
            df_combined.sort_values(by='datetime', inplace=True)
        except Exception as e:
            print(f"⚠️ Gagal membaca {file_path}, membuat file baru. Error: {e}")
            df_combined = df_new
    else:
        df_combined = df_new

    # Simpan kembali ke JSON
    df_combined.to_json(
        file_path,
        orient="records",
        indent=4,
        date_format="iso"
    )
    return len(df_combined)

# Eksekusi penyimpanan untuk masing-masing pelabuhan
total_ketapang = save_and_append_json(df_all[df_all["pelabuhan"] == "Ketapang"], json_ketapang)
total_gilimanuk = save_and_append_json(df_all[df_all["pelabuhan"] == "Gilimanuk"], json_gilimanuk)

print(f"✅ JSON Ketapang tersimpan : {json_ketapang}")
print(f"✅ JSON Gilimanuk tersimpan: {json_gilimanuk}")

print(f"📊 Total data Ketapang di file : {total_ketapang}")
print(f"📊 Total data Gilimanuk di file: {total_gilimanuk}")