import pandas as pd
import plotly.graph_objects as go

from src.data import MONTHS, ROOT_ID, monthly_by_via, parent_of, top_markets
from src.theme import (BAND, ESTIMATE, FADED_OPACITY, HIGHLIGHT_OPACITY, INK, MODEL_COLORS, MODEL_DASH,
                       MUTED, NEUTRAL, NEUTRAL_LIGHT, SEQUENTIAL, VIA_COLORS, base_layout, empty_figure)

NO_VIA = "Seleccione al menos una vía de ingreso para ver este gráfico."


def yearly_bars(yearly: pd.DataFrame, selected: int, vias: list[str], years: list[int]):
    data = yearly[yearly["Vía"].isin(vias) & yearly["Año"].between(*years)]
    if data.empty:
        return empty_figure(NO_VIA if not vias else
                            "No hay registros para las vías y años elegidos.<br>"
                            "Pruebe otra vía o amplíe el rango de años.")
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
                     rangeselector=dict(x=1, xanchor="right", y=1.02, buttons=[dict(count=5, label="5 años", step="year", stepmode="backward"),
                                                 dict(step="all", label="Todo")]))
    fig = base_layout(fig, height=460)
    # conserva el zoom al prender o apagar modelos; cambiar de serie lo reinicia
    fig.update_layout(margin_t=110, legend=dict(y=1.22), uirevision=serie)
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


def market_treemap(tree: pd.DataFrame, node: str):
    """V5: región -> país. El área es el número de visitantes; el color solo distingue el nivel
    y resalta el país elegido, que se muestra dentro de su región."""
    if tree.empty:
        return empty_figure("No hay visitantes extranjeros para las vías y años elegidos.", height=460)
    regions = tree.groupby("Región", as_index=False)["Viajero"].sum()
    ids = [ROOT_ID] + regions["Región"].tolist() + tree["id"].tolist()
    labels = [ROOT_ID] + regions["Región"].tolist() + tree["País"].tolist()
    parents = [""] + [ROOT_ID] * len(regions) + tree["Región"].tolist()
    values = [regions["Viajero"].sum()] + regions["Viajero"].tolist() + tree["Viajero"].tolist()
    level = node if "/" not in node else parent_of(node)
    picked = (tree["id"] == node).tolist()
    colors = ["white"] + [NEUTRAL] * len(regions) + [NEUTRAL if p else NEUTRAL_LIGHT for p in picked]
    fig = go.Figure(go.Treemap(
        ids=ids, labels=labels, parents=parents, values=values, branchvalues="total",
        level=level if level in ids else ROOT_ID, maxdepth=2,
        marker=dict(colors=colors, line=dict(color="white", width=2)),
        textfont=dict(color=[INK] + ["white"] * len(regions) + ["white" if p else INK for p in picked]),
        texttemplate="<b>%{label}</b><br>%{value:,.0f}<br>%{percentRoot:.1%}",
        hovertemplate="<b>%{label}</b><br>%{value:,.0f} visitantes<br>"
                      "%{percentParent:.1%} de %{parent}<extra></extra>",
        pathbar=dict(visible=True, thickness=24), tiling=dict(pad=2),
    ))
    fig = base_layout(fig, height=460)
    fig.update_layout(margin=dict(l=4, r=4, t=30, b=4), uirevision=level)
    return fig


def border_bars(borders: pd.DataFrame, who: str):
    """V6: puntos de ingreso de los visitantes elegidos en V5, coloreados por su vía."""
    if borders.empty:
        return empty_figure(f"No hay ingresos registrados de {who}<br>para las vías y años elegidos.",
                            height=460)
    total = borders["Viajero"].sum()
    fig = go.Figure()
    for via, color in VIA_COLORS.items():
        d = borders[borders["Vía"] == via]
        if d.empty:
            continue
        fig.add_bar(x=d["Viajero"], y=d["Punto"], orientation="h", name=via, marker_color=color,
                    customdata=d["Viajero"] / total * 100,
                    hovertemplate="%{y} (" + via + "): %{x:,.0f} visitantes<br>"
                                  "%{customdata:.1f} % del total de " + who + "<extra></extra>")
    order = borders.groupby("Punto")["Viajero"].sum().sort_values().index.tolist()
    fig.update_yaxes(categoryorder="array", categoryarray=order)
    fig.update_xaxes(gridcolor="#E3E7ED", tickformat="~s")
    fig = base_layout(fig, height=max(300, 120 + 26 * len(order)))
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)", automargin=True)
    fig.update_layout(barmode="stack", margin_l=10, bargap=0.3, legend_traceorder="normal")
    return fig


MEASURE_TEXT = {"abs": "visitantes", "idx": "índice (100 = mes promedio del año)"}


def season_heatmap(m: pd.DataFrame, measure: str, year: int):
    """V7: calendario año x mes. Un solo tono neutro de claro (pocas llegadas) a oscuro (muchas)."""
    if m.notna().sum().sum() == 0:
        return empty_figure("No hay datos para las vías y años elegidos." if measure == "abs" else
                            "No hay años completos en la selección para calcular el índice.", height=520)
    years = m.index.tolist()
    if measure == "abs":
        hover, colorbar, zrange = "%{x} %{y}: %{z:,.0f} visitantes<extra></extra>", dict(tickformat="~s"), {}
    else:
        # escala fija 60-140: los meses extremos de 2020 (hasta 400) no deben apagar el resto del calendario
        hover = "%{x} %{y}: índice %{z:.0f}<br>(100 = mes promedio de ese año)<extra></extra>"
        colorbar = dict(tickvals=[60, 80, 100, 120, 140], ticktext=["≤60", "80", "100", "120", "≥140"])
        zrange = dict(zmin=60, zmax=140)
    fig = go.Figure(go.Heatmap(z=m.values, x=MONTHS, y=years, colorscale=SEQUENTIAL, xgap=2, ygap=2, **zrange,
                               hovertemplate=hover, hoverongaps=False,
                               colorbar=dict(thickness=12, outlinewidth=0, title=None, **colorbar)))
    gaps = m.isna().stack()
    gaps = gaps[gaps].reset_index()
    if not gaps.empty:
        fig.add_scatter(x=[MONTHS[i - 1] for i in gaps["Mes"]], y=gaps["Año"], mode="markers",
                        marker=dict(symbol="x-thin", size=8, line=dict(width=1.5, color=MUTED)),
                        hovertemplate="%{x} %{y}: sin datos<extra></extra>", showlegend=False)
    if year in years:
        fig.add_shape(type="rect", x0=-0.5, x1=11.5, y0=year - 0.5, y1=year + 0.5,
                      line=dict(color=INK, width=2.5))
    fig = base_layout(fig, height=max(320, 90 + 24 * len(years)))
    fig.update_yaxes(range=[years[-1] + 0.5, years[0] - 0.5], dtick=1, gridcolor="rgba(0,0,0,0)", tickformat="d")
    fig.update_xaxes(side="top")
    fig.update_layout(margin=dict(l=50, r=10, t=30, b=10), clickmode="event")
    return fig


def season_boxes(long: pd.DataFrame, highlight: pd.Series | None, measure: str, year: int):
    """V8: perfil estacional. Cada caja resume un mes en todos los años; la línea es el año elegido."""
    if long.empty:
        return empty_figure("No hay años en la selección para construir el perfil." if measure == "abs" else
                            "No hay años completos en la selección para calcular el índice.", height=420)
    x = [MONTHS[i - 1] for i in long["Mes"]]
    unit = "visitantes" if measure == "abs" else "índice"
    fmt = ",.0f" if measure == "abs" else ".0f"
    fig = go.Figure(go.Box(
        x=x, y=long["Valor"], name="Años del periodo", customdata=long["Año"].tolist(),
        marker=dict(color=NEUTRAL, size=5, opacity=0.55), line=dict(color=NEUTRAL, width=1.5),
        fillcolor="rgba(74, 99, 130, 0.18)", boxpoints="all", jitter=0.35, pointpos=0, hoveron="points",
        hovertemplate="%{x} %{customdata}: %{y:" + fmt + "} " + unit + "<extra></extra>"))
    if highlight is not None and highlight.notna().any():
        fig.add_scatter(x=MONTHS, y=highlight.values, name=f"Año {year}", mode="lines+markers",
                        line=dict(color=INK, width=2.5), marker=dict(size=7),
                        hovertemplate="%{x} " + str(year) + ": %{y:" + fmt + "} " + unit + "<extra></extra>")
    if measure == "idx":
        fig.add_hline(y=100, line=dict(color=MUTED, dash="dot", width=1))
    fig.update_xaxes(categoryorder="array", categoryarray=MONTHS)
    fig = base_layout(fig, height=420)
    fig.update_yaxes(title_text=MEASURE_TEXT[measure], title_font_size=13,
                     tickformat="~s" if measure == "abs" else "d")
    fig.update_layout(clickmode="event")
    return fig


def antigua_lines(obs: pd.DataFrame, est: pd.DataFrame):
    """
    Visitantes de Antigua: observados en línea continua y estimaciones en morado discontinuo.
    Los meses sin telefonía quedan como hueco en la línea observada, nunca como cero.
    """
    fig = go.Figure()
    if not est.empty:
        fig.add_vrect(x0=est["fecha"].min() - pd.Timedelta(days=15), x1=est["fecha"].max() + pd.Timedelta(days=15),
                      fillcolor=BAND, layer="below", line_width=0, annotation_text="sin medición directa",
                      annotation_position="top left", annotation_font_color=MUTED)
    fig.add_scatter(x=obs["fecha"], y=obs["visitantes_obs"], name="Observado", mode="lines+markers",
                    connectgaps=False, line=dict(color=INK, width=2.5), marker=dict(size=7),
                    hovertemplate="%{x|%b %Y}: %{y:,.0f} visitantes<extra>Observado</extra>")
    # el tramo discontinuo une el último observado anterior y el siguiente con las estimaciones
    known = obs.dropna(subset=["visitantes_obs"])
    before = known[known["fecha"] < est["fecha"].min()].tail(1) if not est.empty else known.iloc[0:0]
    after = known[known["fecha"] > est["fecha"].max()].head(1) if not est.empty else known.iloc[0:0]
    bridge = pd.concat([before.rename(columns={"visitantes_obs": "valor"}), est,
                        after.rename(columns={"visitantes_obs": "valor"})])
    fig.add_scatter(x=bridge["fecha"], y=bridge["valor"], mode="lines", showlegend=False, hoverinfo="skip",
                    line=dict(color=ESTIMATE, width=2, dash="dash"))
    fig.add_scatter(x=est["fecha"], y=est["valor"], name="Estimación", mode="markers+text",
                    marker=dict(color=ESTIMATE, size=12, symbol="diamond"),
                    text=[f"{v / 1e6:.2f} M" for v in est["valor"]], textposition="bottom center",
                    textfont=dict(color=ESTIMATE),
                    hovertemplate="%{x|%b %Y}: %{y:,.0f} visitantes<extra>Estimación</extra>")
    fig = base_layout(fig, height=420)
    fig.update_xaxes(dtick="M1", tickformat="%b\n%Y")
    fig.update_yaxes(title="visitantes únicos del mes", rangemode="tozero")
    return fig
