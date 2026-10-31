import pandas as pd
from dash import Dash, Input, Output, State, dash_table, dcc, html

from src.data import (MONTHS, OTHERS, ROOT, ROOT_ID, VIAS, border_ranking, load_arrivals, market_tree,
                      parent_of, seasonal_matrix, seasonal_profile, select_node, visitors, yearly_by_via)
from dash import callback_context, no_update

from src.antigua import date_label, frames, load_current, month_label

from src.figures import (antigua_lines, border_bars, error_by_month, forecast_lines, market_bars, market_treemap, monthly_lines,
                         season_boxes, season_heatmap, yearly_bars)
from src.theme import empty_figure
from src.models import MODELS, SERIES, errors_by_month, test_errors, window_metrics

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


def year_slider(id_, value):
    return dcc.RangeSlider(id=id_, min=YEARS[0], max=YEARS[-1], step=1, value=value,
                           marks={y: str(y) for y in YEARS if (y - YEARS[0]) % 3 == 0 or y == YEARS[-1]})


def via_checklist(id_, value):
    return dcc.Checklist(id=id_, options=VIAS, value=value, inline=True,
                         inputStyle={"marginRight": "4px"}, labelStyle={"marginRight": "14px"})


def tab_markets():
    return html.Div([
        html.P("¿De qué países vienen los visitantes y por qué puntos del país entran? "
               "Haga clic en una región del primer gráfico para ver sus países; el segundo gráfico muestra "
               "por dónde ingresan los visitantes de lo que usted seleccione.", className="tab-intro"),
        html.Div(id="markets-cards", className="cards"),
        html.Div([
            html.Div([html.Label("Vías de ingreso", className="title"),
                      via_checklist("mk-vias", VIAS)]),
            html.Div([html.Label("Años", className="title"), year_slider("mk-years", [LAST_FULL_YEAR] * 2)],
                     style={"flex": "1", "minWidth": "280px"}),
        ], className="controls"),
        html.Div([
            html.Div([html.H3("Visitantes por región y país de residencia"),
                      html.P([html.Span("Observado", className="badge obs"),
                              "El tamaño de cada rectángulo es proporcional a sus visitantes. Clic en una región "
                              "para entrar a sus países; clic en la barra superior para volver. Los países "
                              f"pequeños de cada región se agrupan en «{OTHERS}». Se excluyen los guatemaltecos "
                              "residentes en el exterior."], className="help"),
                      dcc.Graph(id="market-tree", config={"displaylogo": False})], className="panel"),
            html.Div([html.H3(id="borders-title"),
                      html.P([html.Span("Observado", className="badge obs"),
                              "Puntos de ingreso ordenados por visitantes; el color indica la vía (aire, tierra o "
                              "mar). Se actualiza con la región o el país elegido a la izquierda."],
                             className="help"),
                      dcc.Graph(id="border-bars", config={"displaylogo": False})], className="panel"),
        ], className="grid-2"),
        dcc.Store(id="market-node", data=ROOT_ID),
    ])


PANDEMIC = [2020, 2021]


def tab_season():
    return html.Div([
        html.P("¿En qué meses se concentra la demanda y qué tan estable es ese patrón de un año a otro? "
               "Haga clic en un año del calendario (o en un punto del perfil) para compararlo con el patrón típico.",
               className="tab-intro"),
        html.Div(id="season-cards", className="cards"),
        html.Div([
            html.Div([html.Label("Vías de ingreso", className="title"),
                      via_checklist("ss-vias", ["Aérea", "Terrestre"])]),
            html.Div([html.Label("Medida", className="title"),
                      dcc.RadioItems(id="ss-measure", inline=True, value="idx",
                                     options=[{"label": "Índice estacional", "value": "idx"},
                                              {"label": "Llegadas", "value": "abs"}],
                                     inputStyle={"marginRight": "4px"}, labelStyle={"marginRight": "14px"})]),
            html.Div([html.Label("Años", className="title"), year_slider("ss-years", [YEARS[0], YEARS[-1]])],
                     style={"flex": "1", "minWidth": "280px"}),
            html.Div([html.Label("Perfil", className="title"),
                      dcc.Checklist(id="ss-exclude", value=["covid"], inputStyle={"marginRight": "4px"},
                                    options=[{"label": "Excluir 2020-2021 (pandemia)", "value": "covid"}])]),
        ], className="controls"),
        html.P("Índice estacional: compara cada mes con el mes promedio de su propio año (100). Un 130 significa "
               "30 % más visitantes que un mes típico de ese año; así se ve la temporada aunque el total crezca o "
               "caiga entre años. Solo se calcula para años completos.", className="help"),
        html.Div([
            html.Div([html.H3("Calendario de llegadas: año por mes"),
                      html.P([html.Span("Observado", className="badge obs"),
                              "Cada celda es un mes; más oscuro = más visitantes. Las columnas oscuras repetidas "
                              "son la temporada alta. ✕ = sin datos (p. ej. jul-dic 2026). El recuadro marca el "
                              "año elegido."], className="help"),
                      dcc.Graph(id="season-heatmap", config={"displaylogo": False})], className="panel"),
            html.Div([html.H3(id="profile-title"),
                      html.P([html.Span("Observado", className="badge obs"),
                              "Cada caja resume un mes en todos los años del periodo: la línea central es el valor "
                              "típico (mediana) y la caja abarca la mitad central de los años. Cajas altas = mes "
                              "variable. La línea oscura es el año elegido en el calendario."], className="help"),
                      dcc.Graph(id="season-boxes", config={"displaylogo": False}),
                      html.P(id="profile-note", className="help")], className="panel"),
        ], className="grid-2"),
        dcc.Store(id="season-year", data=LAST_FULL_YEAR),
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
            html.H3("¿En qué meses falla más cada modelo?"),
            html.P([html.Span("Estimado", className="badge est"),
                    "Error promedio de cada modelo según el mes del año. Está enlazado con el gráfico de "
                    "arriba: al acercar o mover su barra inferior, este gráfico y la tabla se recalculan solo "
                    "para ese periodo. Pase el cursor sobre una barra para ver si el modelo se quedó corto o "
                    "se pasó."], className="help"),
            html.P(id="window-label", className="help", style={"fontWeight": 600}),
            dcc.Graph(id="error-by-month", config={"displaylogo": False}),
        ], className="panel"),
        dcc.Store(id="forecast-window", data=None),
        html.Div([
            html.H3("Error promedio de cada modelo en el periodo elegido"),
            html.P("MAE: cuántos visitantes se equivoca en promedio cada mes. RMSE: parecido, pero castiga más "
                   "los errores grandes. MAPE: el error como porcentaje de lo observado. Menor es mejor en las "
                   "tres. Meses: cuántos meses de evaluación entran en el periodo elegido.", className="help"),
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


def tab_antigua():
    return html.Div([
        html.P("¿Cuántos visitantes recibe La Antigua Guatemala cada mes, incluidos enero y febrero de 2026, "
               "que no tienen medición directa? Las cifras vienen de la última versión aprobada del cálculo; "
               "cambiar la vista no recalcula nada.", className="tab-intro"),
        html.Div(id="ant-cards", className="cards"),
        html.Div([
            html.Div([html.Label("Periodo", className="title"),
                      dcc.RadioItems(id="ant-window", inline=True, value="all",
                                     options=[{"label": "sep 2025 – jun 2026", "value": "all"},
                                              {"label": "Solo 2026", "value": "2026"}],
                                     inputStyle={"marginRight": "4px"}, labelStyle={"marginRight": "14px"})]),
        ], className="controls"),
        html.Div([
            html.H3("Visitantes únicos del mes en La Antigua Guatemala"),
            html.P([html.Span("Observado", className="badge obs"), html.Span("Estimación", className="badge est"),
                    "La línea continua es lo medido con telefonía móvil en el polígono de Antigua. Los rombos "
                    "morados son estimaciones para meses sin medición; el hueco en la línea indica que ahí no hay "
                    "dato observado, no que hubo cero visitantes."], className="help"),
            dcc.Graph(id="ant-lines", config={"displaylogo": False}),
            html.P(id="ant-validation", className="help"),
        ], className="panel"),
        html.P(id="ant-warning", className="warning"),
        dcc.Store(id="ant-data"),
    ])


ANT_LIMITS = ("Limitaciones: enero y febrero de 2026 no tienen datos de telefonía, ni ese año ni en años anteriores. "
              "Su valor se estima con las llegadas de viajeros registradas por Migración y la proporción promedio "
              "entre ambas fuentes en los meses que sí tienen las dos. No hay un enero o febrero previo con qué "
              "comprobarlo y la prueba se hizo con otros meses: use las cifras como orden de magnitud, no como "
              "dato oficial.")


app.layout = html.Div([
    html.Div([html.H1("Observatorio de turismo sostenible — Guatemala"),
              html.P("Ingreso de visitantes internacionales, ene-2009 a jun-2026 · Fuente: INGUAT / Migración")],
             className="header"),
    html.Div(dcc.Tabs(id="tabs", value="overview", children=[
        dcc.Tab(label="Panorama", value="overview", children=tab_overview()),
        dcc.Tab(label="Mercados y fronteras", value="markets", children=tab_markets()),
        dcc.Tab(label="Estacionalidad", value="season", children=tab_season()),
        dcc.Tab(label="Pronósticos", value="forecast", children=tab_forecast()),
        dcc.Tab(label="Antigua Guatemala", value="antigua", children=tab_antigua()),
    ]), className="container"),
])

@app.callback(Output("selected-year", "data"),
              Input("yearly-bars", "clickData"), Input("year-range", "value"),
              State("selected-year", "data"))
def select_year(click, years, current):
    if callback_context.triggered_id == "yearly-bars" and click and click["points"]:
        current = int(click["points"][0]["x"])
    return min(max(current, years[0]), years[1])


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


def node_name(node):
    if node == ROOT_ID:
        return "todas las regiones"
    region, _, country = node.partition("/")
    return f"{country} ({region})" if country else region


@app.callback(Output("market-node", "data"),
              Input("market-tree", "clickData"), Input("mk-years", "value"), Input("mk-vias", "value"),
              State("market-node", "data"))
def pick_market(click, years, vias, current):
    # cambiar los filtros redibuja V5 desde la raíz
    if callback_context.triggered_id != "market-tree" or not click or not click["points"]:
        return ROOT_ID
    node = click["points"][0].get("id")
    if not node:
        return current
    shown = current if "/" not in current else parent_of(current)
    # clic en la barra superior (el nivel que se está viendo) o de nuevo en el país elegido: sube un nivel
    return parent_of(node) if node in (shown, current) and node != ROOT_ID else node


@app.callback(Output("market-tree", "figure"), Output("border-bars", "figure"),
              Output("borders-title", "children"), Output("markets-cards", "children"),
              Input("market-node", "data"), Input("mk-years", "value"), Input("mk-vias", "value"))
def update_markets(node, years, vias):
    period = str(years[0]) if years[0] == years[1] else f"{years[0]}-{years[1]}"
    title = f"Puntos de ingreso de visitantes de {node_name(node)}, {period}"
    if not vias:
        msg = "Seleccione al menos una vía de ingreso para ver este gráfico."
        return empty_figure(msg, height=460), empty_figure(msg, height=460), title, []
    sub = visitors(df, years, vias)
    chosen = select_node(sub, node)
    total = sub["Viajero"].sum()
    by_market = sub.groupby("País")["Viajero"].sum().sort_values(ascending=False)
    by_border = chosen.groupby("Frontera")["Viajero"].sum().sort_values(ascending=False)
    cards = [
        card("Visitantes extranjeros", f"{total / 1e6:.2f} M" if total >= 1e5 else f"{total:,.0f}",
             f"{period} · vías elegidas"),
        card("Mercado principal", by_market.index[0] if total else "—",
             f"{by_market.iloc[0] / total * 100:.0f} % de los visitantes" if total else ""),
        card("Tres mayores mercados", f"{by_market.head(3).sum() / total * 100:.0f} %" if total else "—",
             "del total: mide la dependencia de pocos países"),
        card("Ingreso principal de la selección", by_border.index[0][3:] if len(by_border) else "—",
             f"{by_border.iloc[0] / by_border.sum() * 100:.0f} % de {node_name(node)}" if len(by_border) else ""),
    ]
    return (market_treemap(market_tree(sub), node), border_bars(border_ranking(chosen), node_name(node)),
            title, cards)


@app.callback(Output("season-year", "data"),
              Input("season-heatmap", "clickData"), Input("season-boxes", "clickData"),
              State("season-year", "data"))
def pick_season_year(heat_click, box_click, current):
    click = heat_click if callback_context.triggered_id == "season-heatmap" else box_click
    if not click or not click["points"]:
        return current
    point = click["points"][0]
    year = point.get("y") if callback_context.triggered_id == "season-heatmap" else point.get("customdata")
    return int(year) if year is not None else current


@app.callback(Output("season-heatmap", "figure"), Output("season-boxes", "figure"),
              Output("profile-title", "children"), Output("profile-note", "children"),
              Output("season-cards", "children"),
              Input("ss-vias", "value"), Input("ss-measure", "value"), Input("ss-years", "value"),
              Input("ss-exclude", "value"), Input("season-year", "data"))
def update_season(vias, measure, years, exclude, year):
    title = f"Perfil estacional: ¿cómo se compara {year} con el patrón típico?"
    if not vias:
        msg = "Seleccione al menos una vía de ingreso para ver este gráfico."
        return empty_figure(msg, height=420), empty_figure(msg, height=420), title, "", []
    m = seasonal_matrix(df, years, vias, measure)
    profile_years = m.drop(index=PANDEMIC, errors="ignore") if exclude else m
    highlight = m.loc[year] if year in m.index else None
    if highlight is None:
        note = f"{year} está fuera del rango de años elegido; elija otro año en el calendario."
    elif highlight.isna().all():
        note = f"{year} no tiene un año completo de datos, por eso no aparece en el índice estacional."
    else:
        note = "Se excluyen 2020-2021 de las cajas (no de la línea del año elegido)." if exclude else ""
    # las tarjetas siempre usan el índice, que es comparable entre años
    idx = seasonal_matrix(df, years, vias, "idx")
    idx = idx.drop(index=PANDEMIC, errors="ignore") if exclude else idx
    typical = idx.median().dropna()
    cards = []
    if not typical.empty:
        peak, low = typical.idxmax(), typical.idxmin()
        n_years = int(idx.notna().all(axis=1).sum())
        cards = [
            card("Mes más fuerte (típico)", MONTHS[peak - 1], f"índice {typical[peak]:.0f}: "
                 f"{typical[peak] - 100:+.0f} % frente a un mes promedio"),
            card("Mes más débil (típico)", MONTHS[low - 1], f"índice {typical[low]:.0f}: "
                 f"{typical[low] - 100:+.0f} % frente a un mes promedio"),
            card("Pico frente a valle", f"{(typical[peak] / typical[low] - 1) * 100:+.0f} %",
                 "más visitantes en el mes fuerte que en el débil"),
            card("Años usados", str(n_years), "años completos del periodo elegido"),
        ]
    return (season_heatmap(m, measure, year), season_boxes(seasonal_profile(profile_years), highlight, measure, year),
            title, note, cards)


@app.callback(Output("forecast-lines", "figure"),
              Input("serie", "value"), Input("model-filter", "value"))
def update_forecast(serie, models):
    return forecast_lines(preds, serie, models)


def range_from_relayout(relayout):
    """Periodo visible de V4 según su zoom o su barra de rango; None si muestra todo."""
    if not relayout or relayout.get("xaxis.autorange"):
        return None
    if "xaxis.range[0]" in relayout:
        return [relayout["xaxis.range[0]"], relayout["xaxis.range[1]"]]
    if "xaxis.range" in relayout:
        return list(relayout["xaxis.range"])
    return "sin cambio"


@app.callback(Output("forecast-window", "data"),
              Input("forecast-lines", "relayoutData"), Input("serie", "value"),
              State("forecast-window", "data"))
def update_window(relayout, serie, current):
    # cambiar de serie redibuja V4 completo, así que el periodo vuelve a ser todo
    if callback_context.triggered_id == "serie":
        return None
    window = range_from_relayout(relayout)
    return current if window == "sin cambio" else window


@app.callback(Output("error-by-month", "figure"), Output("metrics-table", "data"),
              Output("metrics-table", "columns"), Output("window-label", "children"),
              Input("serie", "value"), Input("model-filter", "value"), Input("forecast-window", "data"))
def update_errors(serie, models, window):
    start, end = (pd.Timestamp(window[0]), pd.Timestamp(window[1])) if window else (None, None)
    err = test_errors(preds, serie, models, start, end)
    cols = [{"name": c, "id": c} for c in ["Modelo", "MAE", "RMSE", "MAPE", "Meses"]]
    if err.empty:
        label = "Periodo analizado: sin meses de evaluación en la selección."
        return error_by_month(err, models), [], cols, label
    ini, fin = err["Fecha"].min(), err["Fecha"].max()
    label = (f"Periodo analizado: {MONTHS[ini.month - 1].lower()} {ini.year} a "
             f"{MONTHS[fin.month - 1].lower()} {fin.year} ({err['Fecha'].nunique()} meses de evaluación)")
    table = window_metrics(err).sort_values("MAE")
    table = table.assign(MAE=table["MAE"].map("{:,.0f}".format), RMSE=table["RMSE"].map("{:,.0f}".format),
                         MAPE=table["MAPE"].map("{:.1f} %".format))
    return error_by_month(errors_by_month(err), models), table.to_dict("records"), cols, label


@app.callback(Output("ant-data", "data"), Input("tabs", "value"))
def load_antigua(tab):
    # se relee la versión vigente al abrir la pestaña: una publicación o restauración se ve sin reiniciar
    return load_current() if tab == "antigua" else no_update


@app.callback(Output("ant-cards", "children"), Output("ant-lines", "figure"),
              Output("ant-validation", "children"), Output("ant-warning", "children"),
              Input("ant-data", "data"), Input("ant-window", "value"))
def update_antigua(data, window):
    if not data:
        cards = [card("Estimaciones no disponibles", "—",
                      "todavía no hay una versión aprobada del cálculo")]
        note = ("Las estimaciones de enero y febrero de 2026 se muestran solo cuando una versión supera los "
                "controles de calidad y la validación. Mientras no exista una, no se presentan cifras.")
        return cards, empty_figure("Estimaciones no disponibles", height=420), note, ANT_LIMITS
    obs, est = frames(data, window)
    meta = data["meta"]
    ev = meta.get("evaluation") or {}
    cand = ev.get("candidate") or {}
    mape, mae = cand.get("MAPE"), cand.get("MAE")
    months = ", ".join(month_label(m) for m in ev.get("months", []))
    cards = [card(f"{month_label(r['periodo']).capitalize()} · estimación", f"{r['valor']:,.0f}",
                  "visitantes únicos, sin medición directa") for r in data["estimates"]]
    if mae is not None:
        cards.append(card("Margen de error típico", f"± {mape:.1f} %" if mape is not None else f"± {mae:,.0f}",
                          f"≈ {mae:,.0f} visitantes por mes en la prueba"))
    cards.append(card("Actualizado", date_label(meta.get("published_at") or meta.get("generated")),
                      f"versión del cálculo {meta.get('procedure_version')}"))
    note = (f"Cómo leer el margen: se ocultaron {months}, meses que sí tienen medición, y se estimaron solo con "
            f"los meses anteriores, igual que enero y febrero. En promedio la estimación se alejó "
            f"{mae:,.0f} visitantes ({mape:.1f} %) de lo medido." if mae is not None and mape is not None else "")
    fig = antigua_lines(obs, est) if not obs.empty or not est.empty else empty_figure("Sin datos en este periodo")
    return cards, fig, note, ANT_LIMITS


if __name__ == "__main__":
    app.run(debug=False)
