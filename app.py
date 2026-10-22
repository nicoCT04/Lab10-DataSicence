import pandas as pd
from dash import Dash, Input, Output, State, dash_table, dcc, html

from src.data import ROOT, VIAS, load_arrivals, yearly_by_via
from src.figures import forecast_lines, market_bars, monthly_lines, yearly_bars
from src.models import MODELS, SERIES

df = load_arrivals()
yearly = yearly_by_via(df)
preds = pd.read_csv(ROOT / "outputs" / "predictions.csv", parse_dates=["Fecha"])
metrics = pd.read_csv(ROOT / "outputs" / "metrics.csv")
YEARS = sorted(int(y) for y in df["Año"].unique())
LAST_FULL_YEAR = 2025

FONTS = "https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600&display=swap"
app = Dash(__name__, title="Observatorio de turismo — Guatemala", external_stylesheets=[FONTS])


def card(label, value, note=""):
    return html.Div([html.Div(label, className="label"), html.Div(value, className="value"),
                     html.Div(note, className="note")], className="card")


def kpis():
    y = df.groupby("Año")["Viajero"].sum()
    growth = (y[LAST_FULL_YEAR] / y[LAST_FULL_YEAR - 1] - 1) * 100
    vs_2019 = y[LAST_FULL_YEAR] / y[2019] * 100
    air = df[(df["Año"] == LAST_FULL_YEAR) & (df["Vía"] == "Aérea")]["Viajero"].sum()
    return html.Div([
        card(f"Llegadas {LAST_FULL_YEAR}", f"{y[LAST_FULL_YEAR] / 1e6:.2f} M", "turistas + excursionistas"),
        card("Variación anual", f"{growth:+.1f} %", f"{LAST_FULL_YEAR} frente a {LAST_FULL_YEAR - 1}"),
        card("Recuperación", f"{vs_2019:.0f} %", "del nivel de 2019 (prepandemia)"),
        card("Llegadas por aire", f"{air / y[LAST_FULL_YEAR] * 100:.0f} %", f"del total {LAST_FULL_YEAR}"),
    ], className="cards")


def tab_overview():
    return html.Div([
        html.P("¿Cuántos visitantes llegan a Guatemala, por dónde entran y en qué meses? "
               "Haga clic en un año del primer gráfico para ver su detalle mensual y sus mercados principales.",
               className="tab-intro"),
        kpis(),
        html.Div([
            html.Div([html.Label("Vías de ingreso", className="title"),
                      dcc.Checklist(id="via-filter", options=VIAS, value=["Aérea", "Terrestre"], inline=True,
                                    inputStyle={"marginRight": "4px"}, labelStyle={"marginRight": "14px"})]),
            html.Div([html.Label("Rango de años", className="title"),
                      dcc.RangeSlider(id="year-range", min=YEARS[0], max=YEARS[-1], step=1,
                                      value=[YEARS[0], YEARS[-1]],
                                      marks={y: str(y) for y in YEARS if (y - YEARS[0]) % 3 == 0 or y == YEARS[-1]})],
                     style={"flex": "1", "minWidth": "280px"}),
        ], className="controls"),
        html.Div([
            html.H3("Llegadas anuales por vía de ingreso"),
            html.P([html.Span("Observado", className="badge obs"),
                    "Cada barra es un año; los colores separan aire, tierra y mar. "
                    "Haga clic en un año para actualizar los dos gráficos de abajo. "
                    "Desde 2017 la base no distingue turistas y excursionistas por vía marítima."],
                   className="help"),
            dcc.Graph(id="yearly-bars", config={"displaylogo": False}),
        ], className="panel"),
        html.Div([
            html.Div([html.H3(id="monthly-title"),
                      html.P("Llegadas de cada mes del año seleccionado: muestra la temporada alta y baja.",
                             className="help"),
                      dcc.Graph(id="monthly-lines", config={"displaylogo": False})], className="panel"),
            html.Div([html.H3(id="markets-title"),
                      html.P("Países o grupos de residencia con más visitantes en el año seleccionado "
                             "(se excluyen guatemaltecos residentes en el exterior).", className="help"),
                      dcc.Graph(id="market-bars", config={"displaylogo": False})], className="panel"),
        ], className="grid-2"),
        dcc.Store(id="selected-year", data=LAST_FULL_YEAR),
    ])


def tab_forecast():
    return html.Div([
        html.P("¿Qué tan bien anticipan los modelos las llegadas? Compare lo observado con lo estimado "
               "por tres modelos sencillos del Laboratorio 1.", className="tab-intro"),
        html.Div([
            html.Div([html.Label("Serie", className="title"),
                      dcc.Dropdown(id="serie", options=SERIES, value="Total", clearable=False,
                                   style={"width": "200px"})]),
            html.Div([html.Label("Modelos a comparar", className="title"),
                      dcc.Checklist(id="model-filter", options=list(MODELS), value=list(MODELS), inline=True,
                                    inputStyle={"marginRight": "4px"}, labelStyle={"marginRight": "14px"})]),
        ], className="controls"),
        html.Div([
            html.H3("Llegadas observadas frente a las estimadas por cada modelo"),
            html.P([html.Span("Observado", className="badge obs"), html.Span("Estimado", className="badge est"),
                    "Los modelos aprendieron con datos hasta mar-2021 y estimaron el resto sin verlo. "
                    "Use la barra inferior o los botones para acercar o alejar el periodo."], className="help"),
            dcc.Graph(id="forecast-lines", config={"displaylogo": False}),
        ], className="panel"),
        html.Div([
            html.H3("Error promedio de cada modelo"),
            html.P("MAE: cuántos visitantes se equivoca en promedio cada mes. MAPE: ese error como "
                   "porcentaje de lo observado. Menor es mejor.", className="help"),
            dash_table.DataTable(id="metrics-table", style_as_list_view=True,
                                 style_cell={"fontFamily": '"Source Sans 3", Arial, sans-serif', "fontSize": 14,
                                             "padding": "6px 10px", "textAlign": "right"},
                                 style_header={"fontWeight": 600, "backgroundColor": "#F5F7FA"},
                                 style_cell_conditional=[{"if": {"column_id": "Modelo"}, "textAlign": "left"}]),
            html.P("Limitación: el periodo de entrenamiento termina en plena pandemia, por eso todos los modelos "
                   "subestiman la recuperación de 2022-2026. Úselos para comparar entre sí, no como cifra oficial.",
                   className="warning", style={"marginTop": "12px"}),
        ], className="panel"),
    ])


def tab_pending(text):
    return html.Div(html.P(text, className="tab-intro"))


app.layout = html.Div([
    html.Div([html.H1("Observatorio de turismo sostenible — Guatemala"),
              html.P("Ingreso de visitantes internacionales, ene-2009 a jun-2026 · Fuente: INGUAT / Migración")],
             className="header"),
    html.Div(dcc.Tabs(id="tabs", value="overview", children=[
        dcc.Tab(label="Panorama", value="overview", children=tab_overview()),
        dcc.Tab(label="Mercados y fronteras", value="markets",
                children=tab_pending("En construcción para la entrega final.")),
        dcc.Tab(label="Estacionalidad", value="season",
                children=tab_pending("En construcción para la entrega final.")),
        dcc.Tab(label="Pronósticos", value="forecast", children=tab_forecast()),
    ]), className="container"),
])

@app.callback(Output("selected-year", "data"),
              Input("yearly-bars", "clickData"), State("selected-year", "data"))
def select_year(click, current):
    if click and click["points"]:
        return int(click["points"][0]["x"])
    return current


@app.callback(Output("yearly-bars", "figure"),
              Input("selected-year", "data"), Input("via-filter", "value"), Input("year-range", "value"))
def update_yearly(year, vias, years):
    return yearly_bars(yearly, year, vias, years)


@app.callback(Output("monthly-lines", "figure"), Output("market-bars", "figure"),
              Output("monthly-title", "children"), Output("markets-title", "children"),
              Input("selected-year", "data"), Input("via-filter", "value"))
def update_detail(year, vias):
    return (monthly_lines(df, year, vias), market_bars(df, year, vias),
            f"Detalle mensual de {year}", f"Principales mercados de {year}")


@app.callback(Output("forecast-lines", "figure"), Output("metrics-table", "data"),
              Output("metrics-table", "columns"),
              Input("serie", "value"), Input("model-filter", "value"))
def update_forecast(serie, models):
    table = metrics[(metrics["Serie"] == serie) & metrics["Modelo"].isin(models)].sort_values("MAE")
    table = table.assign(MAE=table["MAE"].map("{:,.0f}".format), MAPE=table["MAPE"].map("{:.1f} %".format))
    cols = [{"name": c, "id": c} for c in ["Modelo", "MAE", "MAPE"]]
    return forecast_lines(preds, serie, models), table[["Modelo", "MAE", "MAPE"]].to_dict("records"), cols


if __name__ == "__main__":
    app.run(debug=True)
