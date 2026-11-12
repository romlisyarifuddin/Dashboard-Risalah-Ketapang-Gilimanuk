import dash
import os
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
import webbrowser
import tempfile
import calendar
from docx import Document
from docx.shared import Inches, Cm, Pt
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from dash import dcc, html, dash_table, Input, Output, State
from threading import Timer
from config import DATA_PARQUET
from utils.data_loader import load_data_parquet
from config import DATA_EVENT
from utils.data_loader import load_event_excel
from datetime import datetime

df_event = load_event_excel(DATA_EVENT)
# =============================
# LOAD DATA (HANYA SEKALI + CACHE)
# =============================

df_all = load_data_parquet(DATA_PARQUET)

# pastikan datetime benar
df_all['datetime'] = pd.to_datetime(df_all['datetime'])

df_all = df_all.sort_values("datetime")
# =============================
# APP INIT
# =============================

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY]
)

# =============================
# HEADER
# =============================

header = dbc.Card(
    dbc.CardBody([
        dbc.Row([
            
            # LOGO
            dbc.Col(
                html.Img(src="/assets/logo_bmkg.png", height="60px"),
                width="auto"
            ),

            # JUDUL
            dbc.Col([
                html.H3("Dashboard Cuaca Selat Bali", className="text-white mb-0"),
                html.Div("Meteorologi Maritim Ketapang", className="text-white")
            ]),

            # 🔥 UPDATE TIME (KANAN)
            dbc.Col(
                html.Div(
                    id="last-update",
                    className="text-white",
                    style={
                        "textAlign": "right",
                        "fontSize": "14px"
                    }
                ),
                width="auto"
            ),

        ], align="center", justify="between")  # 🔥 penting!
    ]),
    style={"background": "linear-gradient(90deg,#0b3d91,#1565c0)"}
)

# =============================
# FILTER
# =============================
end = df_all['datetime'].max()
start = end - pd.Timedelta(days=3)

filter_card = dbc.Card([
    dbc.CardBody([
        dbc.Row([

            dbc.Col([
                html.Label("Pelabuhan"),
                dcc.Checklist(
                    id='dropdown-pelabuhan',  # ID tetap sama biar callback tidak berubah
                    options=[
                        {'label': 'Gilimanuk', 'value': 'Gilimanuk'},
                        {'label': 'Ketapang', 'value': 'Ketapang'}
                    ],
                    value=['Gilimanuk','Ketapang'],
                    inline=True
                )
            ], md=4),

            dbc.Col([
                html.Label("Tanggal"),
                dcc.DatePickerRange(
                    id='date-range',
                    start_date=start,
                    end_date=end,
                    initial_visible_month=end
                )
            ], md=4),

            dbc.Col([
                html.Label("Jenis Grafik"),
                dcc.RadioItems(
                    id='graph-type',
                    options=[
                        {'label':'Line','value':'line'},
                        {'label':'Bar','value':'bar'}
                    ],
                    value='line',
                    inline=True
                )
            ], md=4),

        ]),
        dbc.Row([
            dbc.Col([
                html.Label("Analisis Kejadian Penutupan"),
                dcc.Dropdown(
                    id='event-dropdown',
                    options=[
                        {
                            'label': f"{row['Tanggal'].strftime('%d-%m-%Y')} {row['Jam_fix']} | {row['Cuaca']}",
                            'value': i
                        }
                        for i, row in df_event.iterrows()
                    ],
                    placeholder="Pilih kejadian penutupan..."
                ),
                dbc.Button("Periksa", id="btn-periksa", color="warning", className="mt-2")
            ], md=12)
        ])
    ])
], className="shadow-sm mb-3")

# =============================
# KPI
# =============================
def create_kpi():
    return dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Max Kecepatan Angin", className="text-muted text-center"),
            html.H3(id="kpi-angin", className="text-center text-primary fw-bold")
        ]), className="shadow-sm border-0 border-start border-primary border-4"), md=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Max Gelombang", className="text-muted text-center"),
            html.H3(id="kpi-gelombang", className="text-center text-info fw-bold")
        ]), className="shadow-sm border-0 border-start border-info border-4"), md=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Max Arus", className="text-muted text-center"),
            html.H3(id="kpi-arus", className="text-center text-warning fw-bold")
        ]), className="shadow-sm border-0 border-start border-warning border-4"), md=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Min Visibility", className="text-muted text-center"),
            html.H3(id="kpi-visibility", className="text-center text-success fw-bold")
        ]), className="shadow-sm border-0 border-start border-success border-4"), md=3),
    ], className="mb-4 mt-3")

@app.callback(
    Output("kpi-angin", "children"),
    Output("kpi-gelombang", "children"),
    Output("kpi-arus", "children"),
    Output("kpi-visibility", "children"),
    Input('dropdown-pelabuhan', 'value'),
    Input('date-range', 'start_date'),
    Input('date-range', 'end_date')
)

def update_kpi(pelabuhan, start_date, end_date):

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    dff = df_all[
        (df_all['pelabuhan'].isin(pelabuhan)) &
        (df_all['datetime'] >= start_date) &
        (df_all['datetime'] <= end_date)
    ]

    if dff.empty:
        return "-", "-", "-", "-"

    max_angin = f"{dff['angin_kecepatan_knots'].max()} knots"
    max_gelombang = f"{dff['gelombang_max_m'].max()} m"
    max_arus = f"{dff['arus_max_knots'].max()} knots"
    min_visibility = f"{dff['visibility_m'].min()} m"

    return max_angin, max_gelombang, max_arus, min_visibility

@app.callback(
    Output("last-update", "children"),
    Input('dropdown-pelabuhan', 'value'),
    Input('date-range', 'start_date'),
    Input('date-range', 'end_date')
)
def update_last_update(pelabuhan, start_date, end_date):

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    dff = df_all[
        (df_all['pelabuhan'].isin(pelabuhan)) &
        (df_all['datetime'] >= start_date) &
        (df_all['datetime'] <= end_date)
    ]

    if dff.empty:
        return "Data tidak tersedia"

    last_time = dff['datetime'].max()

    return f"⏱️ Update data terakhir: {last_time.strftime('%d %B %Y %H:%M')} WITA"

# =============================
# KARTU LAPORAN BULANAN (UI BARU)
# =============================
# 👇 1. Definisikan card-nya di luar app.layout
laporan_bulanan_card = dbc.Card([
    dbc.CardBody([
        html.H4("Generate Laporan Operasional Bulanan", className="mb-4"),
        
        html.H6("1. Pilih Bulan & Tahun Laporan"),
        dbc.Row([
            dbc.Col([
                html.Label("Bulan", className="text-muted"),
                dcc.Dropdown(
                    id='input-bulan-laporan',
                    options=[
                        {'label': 'Januari', 'value': 1},
                        {'label': 'Februari', 'value': 2},
                        {'label': 'Maret', 'value': 3},
                        {'label': 'April', 'value': 4},
                        {'label': 'Mei', 'value': 5},
                        {'label': 'Juni', 'value': 6},
                        {'label': 'Juli', 'value': 7},
                        {'label': 'Agustus', 'value': 8},
                        {'label': 'September', 'value': 9},
                        {'label': 'Oktober', 'value': 10},
                        {'label': 'November', 'value': 11},
                        {'label': 'Desember', 'value': 12},
                    ],
                    value=pd.Timestamp.today().month, # Default ke bulan saat ini
                    clearable=False
                )
            ], md=3),
            
            dbc.Col([
                html.Label("Tahun", className="text-muted"),
                dcc.Dropdown(
                    id='input-tahun-laporan',
                    options=[{'label': str(y), 'value': y} for y in range(pd.Timestamp.today().year - 3, pd.Timestamp.today().year + 3)],
                    value=pd.Timestamp.today().year, # Default ke tahun saat ini
                    clearable=False
                )
            ], md=3, className="mb-3")
        ]),
        
        html.H6("2. Input Manual Data Pelayanan & Bimbingan", className="mt-3"),
        
        # 🆕 KELOMPOK BARU: Pengguna Jasa
        html.Label("A. Jumlah Pengguna Jasa", className="fw-bold text-primary mt-2"),
        dbc.Row([
            dbc.Col([
                html.Label("Instansi Pemerintah (Instansi)"), 
                dbc.Input(id="inp-pengguna-pemerintah", type="number", value=0)
            ], md=4),
        ], className="mb-3"),
        
        # KELOMPOK LAMA: Permintaan Data
        html.Label("B. Jumlah Permintaan Data", className="fw-bold text-primary"),
        dbc.Row([
            dbc.Col([html.Label("Pelabuhan (kali)"), dbc.Input(id="inp-pelabuhan", type="number", value=0)], md=2),
            dbc.Col([html.Label("Kapal (kali)"), dbc.Input(id="inp-kapal", type="number", value=0)], md=2),
            dbc.Col([html.Label("Swasta (kali)"), dbc.Input(id="inp-swasta", type="number", value=0)], md=2),
            dbc.Col([html.Label("Pemerintah (kali)"), dbc.Input(id="inp-pemerintah", type="number", value=0)], md=3),
            dbc.Col([html.Label("Perorangan (kali)"), dbc.Input(id="inp-perorangan", type="number", value=0)], md=3),
        ]),
        
        html.Hr(className="mt-4"),
        dbc.Row([
            dbc.Col([html.Label("Jml Kunjungan Kapal"), dbc.Input(id="inp-kunjungan-kapal", type="number", value=0)], md=3),
            dbc.Col([html.Label("Nama Kapal Dikunjungi"), dbc.Input(id="inp-nama-kapal", type="text", placeholder="-")], md=3),
            dbc.Col([html.Label("Jml Berlayar"), dbc.Input(id="inp-berlayar", type="number", value=0)], md=3),
            dbc.Col([html.Label("Nama Kapal Berlayar"), dbc.Input(id="inp-kapal-berlayar", type="text", placeholder="-")], md=3),
        ]),

        # 🆕 TAMBAHAN BARU: KOLOM ESAI UNTUK MASALAH DAN SARAN
        html.Hr(),
        html.H6("3. Input Masalah & Saran", className="mt-3"),
        dbc.Row([
            dbc.Col([
                html.Label("Masalah yang Ada"),
                dbc.Textarea(id="inp-masalah", placeholder="Ketikkan kendala/masalah bulan ini...", rows=4)
            ], md=6),
            dbc.Col([
                html.Label("Saran / Rekomendasi"),
                dbc.Textarea(id="inp-saran", placeholder="Ketikkan saran atau solusi pemecahan masalah...", rows=4)
            ], md=6),
        ]),

        dbc.Button("Download Laporan Bulanan (.docx)", id="btn-generate-bulanan", color="success", className="mt-4 w-100"),
        # 🔥 FITUR BARU: Animasi Loading saat proses generate berjalan
        dcc.Loading(
            id="loading-generate-laporan",
            type="circle",       # Pilihan bentuk animasi: "circle", "dot", atau "default"
            color="#2980b9",     # Warna loading disesuaikan dengan tema BMKG
            children=[
                dcc.Download(id="download-laporan-bulanan"),
                dcc.Download(id="download-report-bulanan")
            ]
        )

    ])
], className="shadow-sm mt-4 mb-4")


# =============================
# LAYOUT UTAMA
# =============================
# 👇 2. Susun semua komponen di dalam app.layout
# =============================
# LAYOUT UTAMA
# =============================
app.layout = dbc.Container([

    header,
    html.Br(),

    filter_card,
    create_kpi(),

    # Membungkus setiap grafik ke dalam dbc.Card agar rapi dan modern
    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody(dcc.Graph(id='graph-cuaca')), className="shadow-sm mb-4"), md=6),
        dbc.Col(dbc.Card(dbc.CardBody(dcc.Graph(id='graph-peringatan')), className="shadow-sm mb-4"), md=6),
    ]),

    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody(dcc.Graph(id='graph-angin')), className="shadow-sm mb-4"), md=6),
        dbc.Col(dbc.Card(dbc.CardBody(dcc.Graph(id='graph-gelombang')), className="shadow-sm mb-4"), md=6),
    ]),

    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody(dcc.Graph(id='graph-arus')), className="shadow-sm mb-4"), md=6),
        dbc.Col(dbc.Card(dbc.CardBody(dcc.Graph(id='graph-visibility')), className="shadow-sm mb-4"), md=6),
    ]),
    
    # 👇 3. Panggil kartu laporan bulanan di sini (cukup panggil variabelnya saja)
    # Tombol utama untuk memicu munculnya form inputan
    dbc.Button(
        "📋 Isi & Generate Laporan Operasional Bulanan", 
        id="btn-toggle-laporan", 
        color="info", 
        className="w-100 mb-3 shadow-sm fw-bold"
    ),
    
    # Membungkus kartu laporan bulanan di dalam Collapse (Default: is_open=False / tertutup)
    dbc.Collapse(
        laporan_bulanan_card,
        id="collapse-laporan",
        is_open=False
    ),

    # BUTTONS
    dbc.Button("Reset Filter", id="reset-filter", color="primary", className="mt-2"),
    dbc.Button("Download Excel", id="btn-download", color="success", className="mt-2 ms-2"),
    dcc.Download(id="download-excel"),

    html.H4("Data Detail", className="mt-4"),

    # DI SINI TEMPAT DataTable
    # ====================================================
    # 👇 TEMPAT DATATABLE (SUDAH DISESUAIKAN DENGAN RISALAH)
    # ====================================================
    dash_table.DataTable(
        id='table-data',
        # Menentukan kolom dan mapping nama judul sesuai Lampiran Risalah
        columns=[
            {"name": "Tanggal", "id": "Tanggal"},
            {"name": "Jam", "id": "Jam"},
            {"name": "Pelabuhan", "id": "pelabuhan"},
            {"name": "Kondisi Cuaca", "id": "kondisi_cuaca"},
            {"name": "Arah Angin", "id": "angin_arah"},
            {"name": "Kecepatan Angin (kt)", "id": "angin_kecepatan_knots"},
            {"name": "Gelombang (m)", "id": "Gelombang (m)"},
            {"name": "Arah Arus", "id": "arus_arah"},
            {"name": "Arus (kt)", "id": "Arus (knots)"}
        ],
        data=[],  # Kosongkan awal, akan diisi lewat callback
        page_size=15,
        page_action="native",
        virtualization=True,
        style_table={'overflowX': 'auto', 'minWidth': '100%'},
        style_header={
            'backgroundColor': '#2C3E50',
            'color': 'white',
            'fontWeight': 'bold',
            'textAlign': 'center',
            'border': 'none'
        },
        style_cell={
            'textAlign': 'center',
            'padding': '10px',
            'fontFamily': 'sans-serif',
            'borderBottom': '1px solid #e2e8f0'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#f8f9fa'
            }
        ]
    )

], fluid=True)


#GRAFIK
@app.callback(
    Output('graph-cuaca', 'figure'),
    Output('graph-angin', 'figure'),
    Output('graph-gelombang', 'figure'),
    Output('graph-arus', 'figure'),
    Output('graph-visibility', 'figure'),
    Output('graph-peringatan', 'figure'),
    Input('dropdown-pelabuhan', 'value'),
    Input('date-range', 'start_date'),
    Input('date-range', 'end_date'),
    Input('graph-type', 'value'),
    Input("btn-periksa", "n_clicks"),       
    State("event-dropdown", "value")         
)

def update_graphs(pelabuhan, start_date, end_date, graph_type, n_clicks, event_id):
    # =============================
    # PRIORITAS: EVENT FILTER
    # =============================
    if n_clicks and event_id is not None:

        event = df_event.loc[event_id]
        event_time = event['datetime_event']

        start_date = event_time - pd.Timedelta(hours=3)
        end_date = event_time + pd.Timedelta(hours=3)

    else:
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)

    dff = df_all[
        (df_all['pelabuhan'].isin(pelabuhan)) &
        (df_all['datetime'] >= start_date) &
        (df_all['datetime'] <= end_date)
    ]

    # Menentukan palet warna yang konsisten dan elegan
    color_map = {"Ketapang": "#2980b9", "Gilimanuk": "#e67e22"}

    # Menambahkan template 'plotly_white' untuk menghilangkan garis abu-abu di background
    fig_cuaca = px.line(dff, x="datetime", y="kondisi_cuaca", color="pelabuhan", color_discrete_map=color_map, title="Kondisi Cuaca")
    fig_angin = px.line(dff, x="datetime", y="angin_kecepatan_knots", color="pelabuhan", color_discrete_map=color_map, title="Kecepatan Angin (Knots)")
    fig_gelombang = px.line(dff, x="datetime", y="gelombang_max_m", color="pelabuhan", color_discrete_map=color_map, title="Tinggi Gelombang Max (m)")
    fig_arus = px.line(dff, x="datetime", y="arus_max_knots", color="pelabuhan", color_discrete_map=color_map, title="Kecepatan Arus (Knots)")
    fig_visibility = px.line(dff, x="datetime", y="visibility_m", color="pelabuhan", color_discrete_map=color_map, title="Jarak Pandang (Visibility)")

    # Looping untuk menyeragamkan layout semua grafik garis
    for fig in [fig_cuaca, fig_angin, fig_gelombang, fig_arus, fig_visibility]:
        fig.update_layout(
            template="plotly_white",
            hovermode="x unified", # Menyatukan tooltip saat kursor digeser
            legend=dict(
                orientation="h", # Legend mendatar di atas
                yanchor="bottom", y=1.02, 
                xanchor="right", x=1,
                title=None
            ),
            margin=dict(l=20, r=20, t=50, b=20),
            title_font=dict(size=16, color="#2C3E50")
        )
        fig.update_xaxes(title_text="", showgrid=False)
        fig.update_yaxes(title_text="", showgrid=True, gridcolor="#f0f0f0")

    # === GRAFIK BAR PERINGATAN ===
    df_warn = dff.copy()
    df_warn['peringatan_dini'] = df_warn['peringatan_dini'].fillna("Normal")

    df_warn_group = df_warn.groupby(['peringatan_dini','pelabuhan'],observed=True).size().reset_index(name='jumlah')
    df_warn_group = df_warn_group[df_warn_group['peringatan_dini'] != "Normal"]
    
    fig_peringatan = px.bar(df_warn_group, x="peringatan_dini", y="jumlah", color="pelabuhan", 
                            color_discrete_map=color_map, custom_data=["pelabuhan"], title="Akumulasi Peringatan Dini")

    fig_peringatan.update_layout(
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=None),
        margin=dict(l=20, r=20, t=50, b=20),
        title_font=dict(size=16, color="#2C3E50")
    )
    fig_peringatan.update_traces(hovertemplate="Pelabuhan: %{customdata[0]}<br>Kategori: %{x}<br>Jumlah: %{y}")

    return fig_cuaca, fig_angin, fig_gelombang, fig_arus, fig_visibility, fig_peringatan

# TABEL DETAIL (MENIRU FORMAT LAMPIRAN RISALAH)hsjd
@app.callback(
    Output('table-data', 'data'),
    Input('graph-peringatan', 'clickData'),
    Input('dropdown-pelabuhan', 'value'),
    Input('date-range', 'start_date'),
    Input('date-range', 'end_date'),
    Input("reset-filter","n_clicks"),
    Input("btn-periksa", "n_clicks"),        
    State("event-dropdown", "value")  
)
def update_table(clickData, pelabuhan, start_date, end_date, reset_click, n_clicks, event_id):
    # =============================
    # PRIORITAS EVENT
    # =============================
    if n_clicks and event_id is not None:
        event = df_event.loc[event_id]
        event_time = event['datetime_event']
        start_date = event_time - pd.Timedelta(hours=3)
        end_date = event_time + pd.Timedelta(hours=3)
    else:
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)

    dff = df_all[
        (df_all['pelabuhan'].isin(pelabuhan)) &
        (df_all['datetime'] >= start_date) &
        (df_all['datetime'] <= end_date)
    ]

    # Cek input mana yang memicu callback (untuk handling tombol reset secara aman)
    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None

    # Jika bukan tombol reset yang diklik, dan grafik peringatan diklik, lakukan filtering data detail
    if triggered_id != "reset-filter" and clickData is not None:
        kategori = clickData['points'][0]['x']
        pelabuhan_klik = clickData['points'][0]['customdata'][0]

        # Filter berdasarkan titik klik pada grafik
        dff = dff[dff['pelabuhan'] == pelabuhan_klik]
        if kategori == "Normal":
            dff = dff[dff['peringatan_dini'].isna()]
        else:
            dff = dff[dff['peringatan_dini'] == kategori]

    if dff.empty:
        return []

    # ====================================================
    # 📊 PROSES TRANSFORMASI DATA (MENIRU LAMPIRAN RISALAH)
    # ====================================================
    dff_table = dff.copy()

    # Formating Tanggal dan Jam
    dff_table['Tanggal'] = dff_table['datetime'].dt.strftime('%d-%m-%Y')
    dff_table['Jam'] = dff_table['datetime'].dt.strftime('%H:%M')

    # Gabungkan Gelombang Min dan Max (contoh hasil: "0.5 - 1.25")
    dff_table['Gelombang (m)'] = (
        dff_table['gelombang_min_m'].round(2).fillna("-").astype(str)
        + " - " +
        dff_table['gelombang_max_m'].round(2).fillna("-").astype(str)
    )

    # Gabungkan Arus Min dan Max (contoh hasil: "1.0 - 2.5")
    dff_table['Arus (knots)'] = (
        dff_table['arus_min_knots'].round(2).fillna("-").astype(str)
        + " - " +
        dff_table['arus_max_knots'].round(2).fillna("-").astype(str)
    )

    # Filter urutan kolom yang hanya ingin kita tampilkan di UI DataTable
    columns_used = [
        'Tanggal', 'Jam', 'pelabuhan', 'kondisi_cuaca', 
        'angin_arah', 'angin_kecepatan_knots', 'Gelombang (m)', 
        'arus_arah', 'Arus (knots)'
    ]

    return dff_table[columns_used].to_dict('records')
    
# RESET FILTER + EVENT
@app.callback(
    Output('dropdown-pelabuhan', 'value'),
    Output('date-range', 'start_date'),
    Output('date-range', 'end_date'),
    Output('event-dropdown', 'value'),   # 🔥 INI YANG DITAMBAHKAN
    Input('reset-filter', 'n_clicks'),
    prevent_initial_call=True
)
def reset_filter(n):
    end = df_all['datetime'].max()
    start = end - pd.Timedelta(days=3)

    return (
        ['Gilimanuk','Ketapang'],
        start,
        end,
        None
    )

# ====================================================
# CALLBACK UNTUK TOGGLE FORM LAPORAN BULANAN
# ====================================================
@app.callback(
    Output("collapse-laporan", "is_open"),
    Input("btn-toggle-laporan", "n_clicks"),
    State("collapse-laporan", "is_open"),
    prevent_initial_call=True
)
def toggle_laporan_form(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open

# ====================================================
# 📋 CALLBACK: GENERATE LAPORAN MERGER (PORTRAIT + LANDSCAPE)
# ====================================================
@app.callback(
    [   # 👈 TAMBAHKAN KURUNG SIKU BUKA DI SINI
        Output("download-laporan-bulanan", "data"), 
        Output("download-report-bulanan", "data")
    ],  # 👈 TAMBAHKAN KURUNG SIKU TUTUP DI SINI
    Input("btn-generate-bulanan", "n_clicks"),
    State("input-bulan-laporan", "value"), 
    State("input-tahun-laporan", "value"), 
    State("inp-pengguna-pemerintah", "value"), 
    State("inp-pelabuhan", "value"), State("inp-kapal", "value"),
    State("inp-swasta", "value"), State("inp-pemerintah", "value"),
    State("inp-perorangan", "value"), State("inp-kunjungan-kapal", "value"),
    State("inp-nama-kapal", "value"), State("inp-berlayar", "value"),
    State("inp-kapal-berlayar", "value"),
    State("inp-masalah", "value"),  
    State("inp-saran", "value"),
    prevent_initial_call=True
)
def generate_laporan_bulanan(n_clicks, selected_month, selected_year, v_pengguna_pemerintah,
                             v_pelabuhan, v_kapal, v_swasta, v_pemerintah, 
                             v_perorangan, v_kunjungan_kapal, v_nama_kapal, v_berlayar, v_kapal_berlayar,
                             v_masalah, v_saran): 
    from docx.enum.section import WD_SECTION_START 

    if not n_clicks or not selected_month or not selected_year:
        return dash.no_update, dash.no_update #

    tahun = int(selected_year)
    bulan = int(selected_month)
    
    dt_dummy = datetime(tahun, bulan, 1)
    nama_bulan = dt_dummy.strftime('%B %Y')

    _, jml_hari = calendar.monthrange(tahun, bulan)
    jml_senin = sum(1 for day in range(1, jml_hari + 1) if calendar.weekday(tahun, bulan, day) == 0)
    jml_kamis = sum(1 for day in range(1, jml_hari + 1) if calendar.weekday(tahun, bulan, day) == 3)

    # 1. FILTER DATA BULANAN
    start_date_bulan = pd.Timestamp(year=tahun, month=bulan, day=1)
    end_date_bulan = pd.Timestamp(year=tahun, month=bulan, day=jml_hari, hour=23, minute=59, second=59)
    
    df_bulan = df_all[(df_all['datetime'] >= start_date_bulan) & (df_all['datetime'] <= end_date_bulan)]
    jml_risalah = len(df_bulan)
    
    peringatan = df_bulan['peringatan_dini'].dropna().str.lower()
    waspada = len(peringatan[peringatan == 'waspada'])
    siaga = len(peringatan[peringatan == 'siaga'])
    awas = len(peringatan[peringatan == 'awas'])

    # ====================================================
    # 📝 BAGIAN 1: LAPORAN OPERASIONAL (TEMPLATE UTAMA - PORTRAIT)
    # ====================================================
    replacements = {
        "[BULAN_LAPORAN]": str(nama_bulan), "[LAPCM]": str(2 * jml_hari), "[JP]": str(1 * jml_hari),
        "[IKHTISAR]": str(jml_senin), "[CUACA_MINGGUAN]": str(jml_senin + jml_kamis), "[SYNOP]": str(24 * jml_hari),
        "[JUMLAH_RISALAH]": str(jml_risalah), "[WASPADA]": str(waspada), "[SIAGA]": str(siaga), "[AWAS]": str(awas),
        
        # 🆕 Placeholder baru ditambahkan ke dalam dictionary
        "[PENGGUNA_PEMERINTAH]": str(v_pengguna_pemerintah or 0), 
        
        "[PELABUHAN]": str(v_pelabuhan or 0), "[KAPAL]": str(v_kapal or 0), "[SWASTA]": str(v_swasta or 0),
        "[PEMERINTAH]": str(v_pemerintah or 0), "[PERORANGAN]": str(v_perorangan or 0), "[KUNJUNGAN_KAPAL]": str(v_kunjungan_kapal or 0),
        "[KUNJUNGAN_NAMA_KAPAL]": str(v_nama_kapal or "-"), "[BERLAYAR]": str(v_berlayar or 0), "[BERLAYAR_KAPAL]": str(v_kapal_berlayar or "-"),
        "[MASALAH_YANG_ADA]": str(v_masalah or "-"), "[SARAN]": str(v_saran or "-")
    }

    template_path = r"C:\Users\HYPE AMD\Documents\KERJA\Dashboad Risalah\Templat_Laporan_Operasional.docx" 
    if not os.path.exists(template_path):
        print(f"⚠️ ERROR: Template {template_path} tidak ditemukan!")
        return dash.no_update

    doc1 = Document(template_path)

    # Mempertahankan fungsi hybrid agar format tidak rusak
    def replace_text_optimized(doc_obj, replace_dict):
        def proses_paragraf(paragraphs):
            for p in paragraphs:
                for target, replacement in replace_dict.items():
                    if target in p.text:
                        terganti_di_run = False
                        for run in p.runs:
                            if target in run.text:
                                run.text = run.text.replace(target, str(replacement))
                                terganti_di_run = True
                        if not terganti_di_run:
                            bold = p.runs[0].bold if p.runs else None
                            italic = p.runs[0].italic if p.runs else None
                            font_size = p.runs[0].font.size if (p.runs and p.runs[0].font) else None
                            font_name = p.runs[0].font.name if (p.runs and p.runs[0].font) else None
                            
                            p.text = p.text.replace(target, str(replacement))
                            
                            if p.runs:
                                p.runs[0].bold = bold
                                p.runs[0].italic = italic
                                if font_size: p.runs[0].font.size = font_size
                                if font_name: p.runs[0].font.name = font_name

        proses_paragraf(doc_obj.paragraphs)
        for table in doc_obj.tables:
            for row in table.rows:
                for cell in row.cells:
                    proses_paragraf(cell.paragraphs)

    replace_text_optimized(doc1, replacements)
    
    buffer1 = io.BytesIO()
    doc1.save(buffer1)
    buffer1.seek(0)
    file_operasional = dcc.send_bytes(buffer1.read(), f"Laporan_Operasional_{nama_bulan}.docx")

    # ====================================================
    # 📝 FILE 2: LAMPIRAN RISALAH (DIBUAT BARU - LANDSCAPE)
    # ====================================================
    doc2 = Document()
    section = doc2.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width = Inches(11.69)
    section.page_height = Inches(8.27)
    section.top_margin = Cm(1.5)
    section.bottom_margin = Cm(1.5)
    section.left_margin = Cm(1)
    section.right_margin = Cm(1)
    
    def buat_heading(dokumen, teks, ukuran_font, level=1):
        p = dokumen.add_paragraph()

        # Gunakan style Heading agar bisa Expand/Collapse di Microsoft Word
        p.style = f'Heading {level}'

        run = p.add_run(str(teks))
        run.bold = True
        run.font.size = Pt(ukuran_font)

        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(4)

        return p

    buat_heading(doc2, f'Lampiran Risalah Cuaca Selat Bali - {nama_bulan}', 16,1)

    if df_bulan.empty:
        doc2.add_paragraph("Tidak ada data risalah cuaca pada periode bulan ini.")
        buffer2 = io.BytesIO()
        doc2.save(buffer2)
        buffer2.seek(0)
        return file_operasional, dcc.send_bytes(buffer2.read(), f"Lampiran_Risalah_{nama_bulan}.docx")

    # --- INSIGHT EKSEKUTIF ---
    buat_heading(doc2, '1. Ringkasan Eksekutif (Catatan Ekstrem Bulanan)', 14,1)
    idx_max_angin = df_bulan['angin_kecepatan_knots'].idxmax()
    idx_max_gel = df_bulan['gelombang_max_m'].idxmax()
    idx_max_arus = df_bulan['arus_max_knots'].idxmax()
    idx_min_vis = df_bulan['visibility_m'].idxmin()

    p_eks = doc2.add_paragraph()
    p_eks.add_run("Kecepatan Angin Tertinggi: ").bold = True
    if pd.notna(idx_max_angin):
        r_angin = df_bulan.loc[idx_max_angin]
        p_eks.add_run(f"{r_angin['angin_kecepatan_knots']} Knots (Terjadi di {r_angin['pelabuhan']} pada {r_angin['datetime'].strftime('%d %B %Y %H:%M')})\n")
    
    p_eks.add_run("Tinggi Gelombang Maksimal: ").bold = True
    if pd.notna(idx_max_gel):
        r_gel = df_bulan.loc[idx_max_gel]
        p_eks.add_run(f"{r_gel['gelombang_max_m']} Meter (Terjadi di {r_gel['pelabuhan']} pada {r_gel['datetime'].strftime('%d %B %Y %H:%M')})\n")

    p_eks.add_run("Kecepatan Arus Tertinggi: ").bold = True
    if pd.notna(idx_max_arus):
        r_arus = df_bulan.loc[idx_max_arus]
        p_eks.add_run(f"{r_arus['arus_max_knots']} Knots (Terjadi di {r_arus['pelabuhan']} pada {r_arus['datetime'].strftime('%d %B %Y %H:%M')})\n")

    p_eks.add_run("Jarak Pandang Terendah: ").bold = True
    if pd.notna(idx_min_vis):
        r_vis = df_bulan.loc[idx_min_vis]
        p_eks.add_run(f"{r_vis['visibility_m']} Meter (Terjadi di {r_vis['pelabuhan']} pada {r_vis['datetime'].strftime('%d %B %Y %H:%M')})\n")

    buat_heading(doc2, '2. Rekapitulasi Kondisi Cuaca & Peringatan Dini', 14,1)
    
    cuaca_bersih = df_bulan['kondisi_cuaca'].dropna().astype(str)
    cuaca_bersih = cuaca_bersih.str.strip().replace(r'\s+', ' ', regex=True).str.title()
    top_cuaca = cuaca_bersih.value_counts()
    total_data = len(df_bulan)
    
    p_prop = doc2.add_paragraph()
    p_prop.add_run("Distribusi Kondisi Cuaca:\n").bold = True
    for cuaca, jumlah in top_cuaca.items():
        persen = (jumlah / total_data) * 100
        p_prop.add_run(f"  • {cuaca}: {jumlah} kejadian ({persen:.1f}%)\n")

    df_pd = df_bulan.dropna(subset=['peringatan_dini'])
    waspada_ktp = len(df_pd[(df_pd['pelabuhan'] == 'Ketapang') & (df_pd['peringatan_dini'].str.lower() == 'waspada')])
    waspada_glm = len(df_pd[(df_pd['pelabuhan'] == 'Gilimanuk') & (df_pd['peringatan_dini'].str.lower() == 'waspada')])
    siaga_ktp = len(df_pd[(df_pd['pelabuhan'] == 'Ketapang') & (df_pd['peringatan_dini'].str.lower() == 'siaga')])
    siaga_glm = len(df_pd[(df_pd['pelabuhan'] == 'Gilimanuk') & (df_pd['peringatan_dini'].str.lower() == 'siaga')])
    awas_ktp = len(df_pd[(df_pd['pelabuhan'] == 'Ketapang') & (df_pd['peringatan_dini'].str.lower() == 'awas')])
    awas_glm = len(df_pd[(df_pd['pelabuhan'] == 'Gilimanuk') & (df_pd['peringatan_dini'].str.lower() == 'awas')])

    p_prop.add_run("\nFrekuensi Peringatan Dini:\n").bold = True
    p_prop.add_run(f"  • Waspada: Ketapang ({waspada_ktp} kali) | Gilimanuk ({waspada_glm} kali)\n")
    p_prop.add_run(f"  • Siaga  : Ketapang ({siaga_ktp} kali) | Gilimanuk ({siaga_glm} kali)\n")
    p_prop.add_run(f"  • Awas   : Ketapang ({awas_ktp} kali) | Gilimanuk ({awas_glm} kali)\n")

    # --- GRAFIK & DATA PERINGATAN DINI ---
    buat_heading(doc2, '3. Grafik & Data Peringatan Dini', 14,1)
    
    color_map = {"Ketapang": "#2980b9", "Gilimanuk": "#e67e22"}
    df_warn = df_bulan.copy()
    df_warn['peringatan_dini'] = df_warn['peringatan_dini'].fillna("Normal")
    df_warn_group = df_warn.groupby(['peringatan_dini','pelabuhan'], observed=True).size().reset_index(name='jumlah')
    df_warn_group = df_warn_group[df_warn_group['peringatan_dini'] != "Normal"]
    
    if not df_warn_group.empty:
        fig_peringatan_bulan = px.bar(df_warn_group, x="peringatan_dini", y="jumlah", color="pelabuhan", color_discrete_map=color_map)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            go.Figure(fig_peringatan_bulan).write_image(tmp.name, format="png")
            tmp_path = tmp.name

        p = doc2.add_paragraph()
        p.add_run().add_picture(tmp_path, width=Inches(7.14))
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    dff_report = df_bulan.copy()
    dff_report['Tanggal'] = dff_report['datetime'].dt.strftime('%d-%m-%Y')
    dff_report['Jam'] = dff_report['datetime'].dt.strftime('%H:%M')
    dff_report['Gelombang (m)'] = dff_report['gelombang_min_m'].round(2).astype(str) + " - " + dff_report['gelombang_max_m'].round(2).astype(str)
    dff_report['Arus (knots)'] = dff_report['arus_min_knots'].round(2).astype(str) + " - " + dff_report['arus_max_knots'].round(2).astype(str)

    columns_used = ['Tanggal', 'Jam', 'pelabuhan', 'kondisi_cuaca', 'angin_arah', 'angin_kecepatan_knots', 'Gelombang (m)', 'arus_arah', 'Arus (knots)']
    column_mapping = {'Tanggal': 'Tanggal', 'Jam': 'Jam', 'pelabuhan': 'Pelabuhan', 'kondisi_cuaca': 'Kondisi Cuaca', 'angin_arah': 'Arah Angin', 'angin_kecepatan_knots': 'Kecepatan Angin (kt)', 'Gelombang (m)': 'Gelombang (m)', 'arus_arah': 'Arah Arus', 'Arus (knots)': 'Arus (kt)'}

    kategori_list = df_bulan['peringatan_dini'].dropna().unique()
    for kategori in kategori_list:
        buat_heading(doc2, f'Kategori: {kategori}', 13,2)
        for pel in ['Ketapang', 'Gilimanuk']:
            df_kat = dff_report[(dff_report['peringatan_dini'] == kategori) & (dff_report['pelabuhan'] == pel)][columns_used]
            if df_kat.empty: continue
            buat_heading(doc2, f'Pelabuhan: {pel}', 12,3)
            
            table = doc2.add_table(rows=1, cols=len(columns_used))
            table.style = 'Table Grid'
            hdr_cells = table.rows[0].cells
            for i, col in enumerate(columns_used): hdr_cells[i].text = column_mapping.get(col, col)
            for _, row in df_kat.iterrows():
                row_cells = table.add_row().cells
                for i, col in enumerate(columns_used): row_cells[i].text = str(row[col])
            doc2.add_paragraph("")

   # --- PENUTUPAN PELABUHAN ---
    buat_heading(doc2, '4. Analisis Penutupan Pelabuhan', 14, 1)
    df_event_filtered = df_event[(df_event['datetime_event'] >= start_date_bulan) & (df_event['datetime_event'] <= end_date_bulan)]

    if df_event_filtered.empty:
        doc2.add_paragraph("Tidak ada catatan kejadian penutupan pelabuhan akibat cuaca buruk pada bulan ini. Kondisi penyeberangan relatif aman dan lancar.")
    else:
        total_penutupan = len(df_event_filtered)
        
        # Mengambil sampel data di sekitar waktu penutupan untuk dihitung rata-ratanya
        df_kumpulan_event = []
        for _, event in df_event_filtered.iterrows():
            event_time = event['datetime_event']
            dff_ev = df_all[(df_all['pelabuhan'].isin(['Ketapang','Gilimanuk'])) & 
                            (df_all['datetime'] >= event_time - pd.Timedelta(hours=2)) & 
                            (df_all['datetime'] <= event_time + pd.Timedelta(hours=2))]
            if not dff_ev.empty:
                df_kumpulan_event.append(dff_ev)
        
        # Membuat Ringkasan Narasi Kreatif
        if df_kumpulan_event:
            df_all_events = pd.concat(df_kumpulan_event)
            avg_angin = df_all_events['angin_kecepatan_knots'].mean()
            avg_gelombang = df_all_events['gelombang_max_m'].mean()
            max_angin = df_all_events['angin_kecepatan_knots'].max()
            max_gelombang = df_all_events['gelombang_max_m'].max()
            
            p_summ = doc2.add_paragraph()
            p_summ.add_run(f"Selama bulan {nama_bulan}, telah terjadi ").bold = False
            p_summ.add_run(f"{total_penutupan} kejadian penutupan pelabuhan").bold = True
            p_summ.add_run(" yang menghentikan sementara aktivitas operasional penyeberangan di Selat Bali. "
                           "Dari data observasi, profil cuaca pada saat armada kapal dihentikan operasinya secara umum menunjukkan kondisi yang cukup ekstrem, dengan rincian:\n")
            p_summ.add_run(f"  • Kecepatan Angin: Rata-rata mencapai {avg_angin:.1f} Knots (Puncak tertinggi: {max_angin:.1f} Knots)\n")
            p_summ.add_run(f"  • Tinggi Gelombang: Rata-rata mencapai {avg_gelombang:.2f} Meter (Puncak tertinggi: {max_gelombang:.2f} Meter)\n\n")
            p_summ.add_run("Berikut adalah rincian historis untuk masing-masing kejadian, termasuk analisis evaluasi pengiriman peringatan dini sebelum penutupan diberlakukan:")

        counter = 1
        for _, event in df_event_filtered.iterrows():
            event_time_wib = event['datetime_event']
            event_time_wita = event_time_wib + pd.Timedelta(hours=1) # 🔥 KONVERSI WITA
            alasan = event['Cuaca'] if 'Cuaca' in event else "Cuaca Ekstrem"

            # Tulis waktu kejadian dengan eksplisit (WIB) agar jelas patokannya
            buat_heading(doc2, f"Kejadian {counter}: Penutupan {event_time_wib.strftime('%d %B %Y pukul %H:%M WIB')} ({alasan})", 12, 2)
            
            # --- 1. EVALUASI PERINGATAN DINI (3 JAM SEBELUMNYA) ---
            df_pd_ktp = df_all[(df_all['pelabuhan'] == 'Ketapang') & 
                               (df_all['datetime'] >= event_time_wib - pd.Timedelta(hours=3)) & 
                               (df_all['datetime'] <= event_time_wib)]
            
            df_pd_glm = df_all[(df_all['pelabuhan'] == 'Gilimanuk') & 
                               (df_all['datetime'] >= event_time_wita - pd.Timedelta(hours=3)) & 
                               (df_all['datetime'] <= event_time_wita)]
            
            kumpulan_pd = []
            if not df_pd_ktp.empty: kumpulan_pd.append(df_pd_ktp)
            if not df_pd_glm.empty: kumpulan_pd.append(df_pd_glm)

            df_pd_cek = pd.DataFrame()
            if kumpulan_pd:
                df_pd_cek = pd.concat(kumpulan_pd).copy()
                df_pd_cek = df_pd_cek.dropna(subset=['peringatan_dini'])
                df_pd_cek = df_pd_cek[~df_pd_cek['peringatan_dini'].str.lower().isin(['', 'normal', 'none', '-'])]
            
            p_pd = doc2.add_paragraph()
            p_pd.add_run("Evaluasi Peringatan Dini:\n").bold = True
            
            if df_pd_cek.empty:
                p_pd.add_run("⚠️ Tidak ditemukan riwayat Peringatan Dini yang terkirim pada rentang 3 jam sebelum kejadian ini. Kondisi cuaca buruk kemungkinan tumbuh secara sangat cepat, lokal, atau spontan.")
            else:
                p_pd.add_run("✅ Peringatan Dini telah berhasil diantisipasi dan diterbitkan oleh Forecaster sebelum pelabuhan ditutup. Berikut riwayat peringatan yang terekam sistem:\n")
                
                df_pd_cek['Jam'] = df_pd_cek['datetime'].dt.strftime('%H:%M')
                df_pd_unik = df_pd_cek.drop_duplicates(subset=['Jam', 'pelabuhan', 'peringatan_dini'])
                
                for _, pd_row in df_pd_unik.iterrows():
                    tz = "WIB" if pd_row['pelabuhan'] == 'Ketapang' else "WITA"
                    p_pd.add_run(f"   • Pukul {pd_row['Jam']} {tz} ({pd_row['pelabuhan']}) : Menerbitkan Status ")
                    p_pd.add_run(f"{pd_row['peringatan_dini'].upper()}").bold = True
                    p_pd.add_run("\n")

            # --- 2. TABEL RINCIAN CUACA SAAT KEJADIAN (-3 jam sampai +3 jam) ---
            df_saat_ktp = df_all[(df_all['pelabuhan'] == 'Ketapang') & 
                                 (df_all['datetime'] >= event_time_wib - pd.Timedelta(hours=3)) & 
                                 (df_all['datetime'] <= event_time_wib + pd.Timedelta(hours=3))]
                                 
            df_saat_glm = df_all[(df_all['pelabuhan'] == 'Gilimanuk') & 
                                 (df_all['datetime'] >= event_time_wita - pd.Timedelta(hours=3)) & 
                                 (df_all['datetime'] <= event_time_wita + pd.Timedelta(hours=3))]
            
            kumpulan_saat = []
            if not df_saat_ktp.empty: kumpulan_saat.append(df_saat_ktp)
            if not df_saat_glm.empty: kumpulan_saat.append(df_saat_glm)

            if kumpulan_saat:
                df_saat = pd.concat(kumpulan_saat).copy()
                
                p_tab = doc2.add_paragraph()
                p_tab.add_run("Rincian Cuaca Saat Kejadian (Rentang -3 Jam s.d +3 Jam dari waktu setempat):").italic = True
                
                # Memberi label WIB/WITA di tabel agar tidak ambigu saat dibaca
                df_saat['Jam'] = df_saat.apply(lambda row: row['datetime'].strftime('%H:%M') + (' WIB' if row['pelabuhan'] == 'Ketapang' else ' WITA'), axis=1)
                
                df_saat['Gel (m)'] = df_saat['gelombang_min_m'].round(2).astype(str) + " - " + df_saat['gelombang_max_m'].round(2).astype(str)
                df_saat['Arus (kt)'] = df_saat['arus_min_knots'].round(2).astype(str) + " - " + df_saat['arus_max_knots'].round(2).astype(str)
                
                # Setup mapping tabel
                cols_tbl = ['Jam', 'pelabuhan', 'kondisi_cuaca', 'angin_kecepatan_knots', 'Gel (m)', 'Arus (kt)']
                map_tbl = {'Jam':'Jam', 'pelabuhan':'Pelabuhan', 'kondisi_cuaca':'Cuaca', 'angin_kecepatan_knots':'Angin (kt)', 'Gel (m)':'Gel (m)', 'Arus (kt)':'Arus (kt)'}
                
                # Menggambar tabel di Word
                table = doc2.add_table(rows=1, cols=len(cols_tbl))
                table.style = 'Table Grid'
                
                # Menulis Header Tabel
                hdr_cells = table.rows[0].cells
                for i, col in enumerate(cols_tbl): 
                    hdr_cells[i].text = map_tbl.get(col, col)
                    hdr_cells[i].paragraphs[0].runs[0].bold = True # Jadikan header tabel Bold
                    
                # Mengisi isi data dari Pandas ke Tabel Word
                for _, row in df_saat.iterrows():
                    row_cells = table.add_row().cells
                    for i, col in enumerate(cols_tbl): 
                        row_cells[i].text = str(row[col])
                        
            doc2.add_paragraph("") # Memberi jeda jarak/spasi antar setiap kejadian
            counter += 1

    buffer2 = io.BytesIO()
    doc2.save(buffer2)
    buffer2.seek(0)
    file_lampiran = dcc.send_bytes(buffer2.read(), f"Lampiran_Risalah_{nama_bulan}.docx")

    # 🔥 MENGEMBALIKAN 2 FILE TERPISAH SEKALIGUS
    return [file_operasional, file_lampiran] # 👈 BUNGKUS RETURN DENGAN KURUNG SIKU

#DOWNLOAD

@app.callback(
    Output("download-excel", "data"),
    Input("btn-download", "n_clicks"),
    State('dropdown-pelabuhan', 'value'),
    State('date-range', 'start_date'),
    State('date-range', 'end_date'),
    State('graph-peringatan', 'clickData'),   # 👈 TAMBAH INI
    prevent_initial_call=True
)
def download_excel(n_clicks, pelabuhan, start_date, end_date, clickData):

    if not n_clicks:
        return dash.no_update

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    dff = df_all[
        (df_all['pelabuhan'].isin(pelabuhan)) &
        (df_all['datetime'] >= start_date) &
        (df_all['datetime'] <= end_date)
    ]

    # =============================
    # 🔥 TAMBAHAN FILTER DARI GRAFIK
    # =============================
    if clickData is not None:

        kategori = clickData['points'][0]['x']
        pelabuhan_klik = clickData['points'][0]['customdata'][0]

        # filter pelabuhan
        dff = dff[dff['pelabuhan'] == pelabuhan_klik]

        # filter kategori
        if kategori == "Normal":
            dff = dff[dff['peringatan_dini'].isna()]
        else:
            dff = dff[dff['peringatan_dini'] == kategori]

    # =============================
    # EXPORT
    # =============================
    buffer = io.BytesIO()

    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        dff.to_excel(writer, index=False)

    buffer.seek(0)

    filename = f"risalah_{start_date.date()}_{end_date.date()}.xlsx"

    return dcc.send_bytes(buffer.read(), filename)

# =============================
# RUN
# =============================

def open_browser():
    webbrowser.open_new("http://127.0.0.1:8050/")

if __name__ == '__main__':
    Timer(1, open_browser).start()   # delay 1 detik biar server siap
    app.run(debug=True, use_reloader=False)
