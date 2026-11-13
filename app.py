import dash
from dash import dcc, html, dash_table, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io

from config import DATA_PARQUET
from utils.data_loader import load_data_parquet

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
            dbc.Col(html.Img(src="/assets/logo_bmkg.png", height="60px"), width="auto"),
            dbc.Col([
                html.H3("Dashboard Cuaca Selat Bali", className="text-white"),
                html.Div("Meteorologi Maritim Ketapang", className="text-white")
            ])
        ], align="center")
    ]),
    style={"background": "linear-gradient(90deg,#0b3d91,#1565c0)"}
)

# =============================
# FILTER
# =============================

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
                    start_date=df_all['datetime'].min(),
                    end_date=df_all['datetime'].max()
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

        ])
    ])
], className="shadow-sm mb-3")

# =============================
# KPI
# =============================

def create_kpi():
    return dbc.Row([

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Max Angin"),
            html.H4(id="kpi-angin")
        ])), md=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Max Gelombang"),
            html.H4(id="kpi-gelombang")
        ])), md=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Max Arus"),
            html.H4(id="kpi-arus")
        ])), md=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Min Visibility"),
            html.H4(id="kpi-visibility")
        ])), md=3),

    ], className="mb-3")

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

# =============================
# LAYOUT
# =============================

app.layout = dbc.Container([

    header,
    html.Br(),

    filter_card,
    create_kpi(),

    dbc.Row([
        dbc.Col(dcc.Graph(id='graph-cuaca'), md=6),
        dbc.Col(dcc.Graph(id='graph-peringatan'), md=6),
    ]),

    dbc.Row([
        dbc.Col(dcc.Graph(id='graph-angin'), md=6),
        dbc.Col(dcc.Graph(id='graph-gelombang'), md=6),
    ]),

    dbc.Row([
        dbc.Col(dcc.Graph(id='graph-arus'), md=6),
        dbc.Col(dcc.Graph(id='graph-visibility'), md=6),
    ]),

    # BUTTONS
    dbc.Button("Reset Filter", id="reset-filter", color="primary", className="mt-2"),
    dbc.Button("Download Excel", id="btn-download", color="success", className="mt-2 ms-2"),
    dcc.Download(id="download-excel"),

    html.H4("Data Detail", className="mt-4"),

    # 👇 DI SINI TEMPAT DataTable
    dash_table.DataTable(
        id='table-data',
        columns=[{"name": i, "id": i} for i in df_all.columns],
        data=[],  # 🔥 kosongkan awal
        page_size=20,
        page_action="native",
        virtualization=True,
        style_table={'height':'400px','overflowY':'auto'},
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
    Input('graph-type', 'value')
)
def update_graphs(pelabuhan, start_date, end_date, graph_type):
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    dff = df_all[
        (df_all['pelabuhan'].isin(pelabuhan)) &
        (df_all['datetime'] >= start_date) &
        (df_all['datetime'] <= end_date)
    ]

    fig_cuaca = px.line(dff, x="datetime", y="Kondisi_Cuaca", color="pelabuhan")
    fig_angin = px.line(dff, x="datetime", y="angin_kecepatan_knots", color="pelabuhan")
    fig_gelombang = px.line(dff, x="datetime", y="gelombang_max_m", color="pelabuhan")
    fig_arus = px.line(dff, x="datetime", y="arus_max_knots", color="pelabuhan")
    fig_visibility = px.line(dff, x="datetime", y="visibility_m", color="pelabuhan")

    df_warn = dff.copy()
    df_warn['peringatan_dini'] = df_warn['peringatan_dini'].fillna("Normal")

    df_warn_group = df_warn.groupby(['peringatan_dini','pelabuhan'],observed=True).size().reset_index(name='jumlah')

    fig_peringatan = px.bar(df_warn_group, x="peringatan_dini", y="jumlah", color="pelabuhan", 
    custom_data=["pelabuhan"])

    fig_peringatan.update_traces(
        hovertemplate="Pelabuhan: %{customdata[0]}<br>Kategori: %{x}<br>Jumlah: %{y}")

    return fig_cuaca, fig_angin, fig_gelombang, fig_arus, fig_visibility, fig_peringatan

#TABEL
@app.callback(
    Output('table-data', 'data'),
    Input('graph-peringatan', 'clickData'),
    Input('dropdown-pelabuhan', 'value'),
    Input('date-range', 'start_date'),
    Input('date-range', 'end_date'),
    Input("reset-filter","n_clicks")
)
def update_table(clickData, pelabuhan, start_date, end_date, reset_click):

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    dff = df_all[
        (df_all['pelabuhan'].isin(pelabuhan)) &
        (df_all['datetime'] >= start_date) &
        (df_all['datetime'] <= end_date)
    ]

    if reset_click and reset_click > 0:
        return dff.to_dict('records')

    if clickData is None:
        return dff.to_dict('records')

    kategori = clickData['points'][0]['x']
    pelabuhan_klik = clickData['points'][0]['customdata'][0]

    # FILTER PELABUHAN
    dff = dff[dff['pelabuhan'] == pelabuhan_klik]

    # FILTER KATEGORI
    if kategori == "Normal":
        dff = dff[dff['peringatan_dini'].isna()]
    else:
        dff = dff[dff['peringatan_dini'] == kategori]

    return dff.to_dict('records')

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

if __name__ == '__main__':
    app.run(debug=True)