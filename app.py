from dash import Dash, dcc, html

from src.data import load_arrivals, VIAS

df = load_arrivals()
YEARS = sorted(df["Año"].unique())
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
        html.Div(id="overview-body"),
    ])


def tab_forecast():
    return html.Div([
        html.P("¿Qué tan bien anticipan los modelos las llegadas? Compare lo observado con lo estimado "
               "por tres modelos sencillos del Laboratorio 1.", className="tab-intro"),
        html.Div(id="forecast-body"),
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

if __name__ == "__main__":
    app.run(debug=True)
