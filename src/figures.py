import pandas as pd
import plotly.graph_objects as go

from src.data import MONTHS, monthly_by_via, top_markets
from src.theme import (BAND, FADED_OPACITY, HIGHLIGHT_OPACITY, MODEL_COLORS, MODEL_DASH,
                       MUTED, NEUTRAL, VIA_COLORS, base_layout, empty_figure)

NO_VIA = "Seleccione al menos una vía de ingreso para ver este gráfico."


def yearly_bars(yearly: pd.DataFrame, selected: int, vias: list[str], years: list[int]):
    data = yearly[yearly["Vía"].isin(vias) & yearly["Año"].between(*years)]
    if data.empty:
        return empty_figure(NO_VIA)
    fig = go.Figure()
    for via in vias:
        d = data[data["Vía"] == via]
        opacity = [HIGHLIGHT_OPACITY if y == selected else FADED_OPACITY for y in d["Año"]]
        fig.add_bar(x=d["Año"], y=d["Viajero"], name=via, marker_color=VIA_COLORS[via],
                    marker_opacity=opacity, customdata=d["Año"],
                    hovertemplate="%{x} · " + via + ": %{y:,.0f}<extra></extra>")
    if years[0] <= 2021 and years[1] >= 2020:
        fig.add_vrect(x0=2019.5, x1=2021.5, fillcolor=BAND, layer="below", line_width=0,
                      annotation_text="COVID-19", annotation_position="top left",
                      annotation_font_color=MUTED)
    if years[1] == 2026:
        fig.add_annotation(x=2026, y=0, yshift=-28, text="ene-jun", showarrow=False,
                           font=dict(size=11, color=MUTED))
    fig.update_layout(barmode="stack", clickmode="event", legend_traceorder="normal")
    fig.update_xaxes(dtick=1, tickangle=-45)
    return base_layout(fig, height=380)


def monthly_lines(df: pd.DataFrame, year: int, vias: list[str]):
    data = monthly_by_via(df, year)
    data = data[data["Vía"].isin(vias)]
    if data.empty:
        return empty_figure(NO_VIA if not vias else f"No hay registros para {', '.join(vias)} en {year}.")
    fig = go.Figure()
    for via in vias:
        d = data[data["Vía"] == via]
        if not d.empty:
            fig.add_scatter(x=d["MesNombre"], y=d["Viajero"], name=via, mode="lines+markers",
                            line=dict(color=VIA_COLORS[via], width=2.5),
                            hovertemplate="%{x} " + str(year) + " · " + via + ": %{y:,.0f}<extra></extra>")
    fig.update_xaxes(categoryorder="array", categoryarray=MONTHS)
    return base_layout(fig, height=320)


def market_bars(df: pd.DataFrame, year: int, vias: list[str]):
    data = top_markets(df[df["Vía"].isin(vias)], year)
    if data.empty:
        return empty_figure(NO_VIA if not vias else f"No hay registros en {year} para la selección.")
    data = data.sort_values("Viajero")
    share = data["Viajero"] / df[(df["Año"] == year) & df["Vía"].isin(vias)]["Viajero"].sum() * 100
    fig = go.Figure(go.Bar(x=data["Viajero"], y=data["Mercado"], orientation="h",
                           marker_color=NEUTRAL, customdata=share,
                           hovertemplate="%{y}: %{x:,.0f} (%{customdata:.1f} %)<extra></extra>"))
    fig.update_xaxes(gridcolor="#E3E7ED", tickformat="~s")
    fig = base_layout(fig, height=320)
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)", automargin=True)
    fig.update_layout(margin_l=10)
    return fig


def forecast_lines(preds: pd.DataFrame, serie: str, models: list[str]):
    data = preds[preds["Serie"] == serie]
    obs = data[data["Modelo"] == "Observado"]
    test_start = obs[obs["Tramo"] == "test"]["Fecha"].min()
    fig = go.Figure()
    fig.add_vrect(x0=test_start, x1=obs["Fecha"].max(), fillcolor=BAND, layer="below", line_width=0,
                  annotation_text="evaluación: datos no vistos",
                  annotation_position="top left", annotation_font_color=MUTED)
    for model in ["Observado"] + models:
        d = data[data["Modelo"] == model]
        label = "Observado" if model == "Observado" else f"{model} (estimado)"
        fig.add_scatter(x=d["Fecha"], y=d["Valor"], name=label, mode="lines",
                        line=dict(color=MODEL_COLORS[model], dash=MODEL_DASH[model],
                                  width=2 if model == "Observado" else 2.5),
                        hovertemplate="%{x|%b %Y}: %{y:,.0f}<extra>" + label + "</extra>")
    fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.06),
                     rangeselector=dict(x=1, xanchor="right", y=1.12, buttons=[dict(count=5, label="5 años", step="year", stepmode="backward"),
                                                 dict(step="all", label="Todo")]))
    fig = base_layout(fig, height=460)
    # conserva el zoom al prender o apagar modelos; cambiar de serie lo reinicia
    fig.update_layout(margin_t=70, legend=dict(y=1.12), uirevision=serie)
    return fig


MODEL_PATTERN = {"ARIMA(1,1,1)": "", "Holt-Winters": "/", "Seasonal Naive": "."}


def error_by_month(by_month: pd.DataFrame, models: list[str]):
    """V9: error medio de cada modelo por mes del año, en el periodo que muestra V4."""
    if not models:
        return empty_figure("Seleccione al menos un modelo para comparar sus errores.", height=380)
    if by_month.empty:
        return empty_figure("El periodo elegido arriba no incluye meses de evaluación.<br>"
                            "Acerque el gráfico de arriba a 2021-2026 o pulse «Todo».", height=380)
    fig = go.Figure()
    for model in models:
        d = by_month[by_month["Modelo"] == model].set_index("Mes").reindex(range(1, 13))
        lado = ["subestimó" if s > 0 else "sobrestimó" for s in d["Sesgo"].fillna(0)]
        fig.add_bar(
            x=MONTHS, y=d["MAE"], name=model,
            marker=dict(color=MODEL_COLORS[model], pattern_shape=MODEL_PATTERN[model],
                        pattern_fgcolor="white"),
            customdata=list(zip(d["Sesgo"].abs().fillna(0), lado, d["Meses"].fillna(0))),
            hovertemplate=("%{x}: error medio de %{y:,.0f} visitantes<br>"
                           "en promedio %{customdata[1]} por %{customdata[0]:,.0f}<br>"
                           "%{customdata[2]:.0f} meses en el periodo<extra>" + model + "</extra>"),
        )
    fig = base_layout(fig, height=380)
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.05)
    fig.update_yaxes(title_text="error medio (visitantes)", title_font_size=13)
    return fig
