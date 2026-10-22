"""Paleta única del tablero: cada color conserva su significado en todas las pestañas."""

INK = "#1E2A38"
MUTED = "#5B6675"
GRID = "#E3E7ED"
BAND = "#ECEFF3"
FONT = "Source Sans 3, Segoe UI, sans-serif"

# Okabe-Ito: segura para daltonismo
VIA_COLORS = {"Aérea": "#0072B2", "Terrestre": "#E69F00", "Marítima": "#009E73"}

# Observado = tinta; estimaciones en tonos que no se usan para vías
MODEL_COLORS = {"Observado": INK, "ARIMA(1,1,1)": "#6A3D9A",
                "Holt-Winters": "#CC79A7", "Seasonal Naive": "#8C8C8C"}
MODEL_DASH = {"Observado": "solid", "ARIMA(1,1,1)": "solid",
              "Holt-Winters": "dashdot", "Seasonal Naive": "dot"}

HIGHLIGHT_OPACITY, FADED_OPACITY = 1.0, 0.35


def base_layout(fig, title=None, height=360):
    fig.update_layout(
        title=dict(text=title, x=0, font=dict(size=16, color=INK)) if title else None,
        font=dict(family=FONT, size=13, color=INK),
        paper_bgcolor="white", plot_bgcolor="white", height=height,
        margin=dict(l=60, r=20, t=50 if title else 20, b=40),
        legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0, title=None),
        hoverlabel=dict(font_family=FONT, bgcolor="white"),
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, tickformat="~s")
    return fig


def empty_figure(message, height=360):
    import plotly.graph_objects as go
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, font=dict(size=15, color=MUTED))
    fig.update_xaxes(visible=False); fig.update_yaxes(visible=False)
    return base_layout(fig, height=height)
