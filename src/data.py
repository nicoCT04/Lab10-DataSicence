from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "raw" / "Base_Migracion_2009-2026jun.xlsx"
CACHE_PATH = ROOT / "outputs" / "arrivals.parquet"

VIAS = ["Aérea", "Terrestre", "Marítima"]
MONTHS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def load_raw(path=DATA_PATH) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="Datos")
    df["Fecha"] = pd.to_datetime(dict(year=df["Año"], month=df["Mes cod"], day=1))
    return df


def load_arrivals() -> pd.DataFrame:
    """Turista + Excursionista: definición estable de todo el período (Lab 1)."""
    if CACHE_PATH.exists():
        return pd.read_parquet(CACHE_PATH)
    df = load_raw()
    df = df[df["Tipo de Viajero"].isin(["Turista", "Excursionista"])]
    cols = ["Fecha", "Año", "Mes cod", "Vía", "Frontera", "País",
            "Región dos", "Agrupación Residencia", "Tipo de Viajero", "Viajero"]
    df = df[cols].rename(columns={"Mes cod": "Mes", "Región dos": "Región",
                                  "Agrupación Residencia": "Mercado",
                                  "Tipo de Viajero": "Tipo"})
    CACHE_PATH.parent.mkdir(exist_ok=True)
    df.to_parquet(CACHE_PATH, index=False)
    return df


def yearly_by_via(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby(["Año", "Vía"], as_index=False)["Viajero"].sum()


def monthly_by_via(df: pd.DataFrame, year: int) -> pd.DataFrame:
    out = df[df["Año"] == year].groupby(["Mes", "Vía"], as_index=False)["Viajero"].sum()
    out["MesNombre"] = out["Mes"].map(lambda m: MONTHS[m - 1])
    return out


def top_markets(df: pd.DataFrame, year: int, n: int = 10) -> pd.DataFrame:
    sub = df[(df["Año"] == year) & (df["Mercado"] != "Guatemala")]
    return sub.groupby("Mercado", as_index=False)["Viajero"].sum().nlargest(n, "Viajero")


ROOT_ID = "Todas las regiones"
OTHERS = "Otros países"


def visitors(df: pd.DataFrame, years: list[int], vias: list[str]) -> pd.DataFrame:
    """Visitantes extranjeros del periodo y las vías elegidas (sin guatemaltecos residentes fuera)."""
    sub = df[df["Año"].between(*years) & df["Vía"].isin(vias) & (df["País"] != "Guatemala")]
    return sub.assign(Región=sub["Región"].replace("0", "Sin región"))


def market_tree(sub: pd.DataFrame, per_region: int = 10) -> pd.DataFrame:
    """Jerarquía región -> país para el treemap; los países pequeños de cada región se agrupan."""
    g = sub.groupby(["Región", "País"], as_index=False)["Viajero"].sum()
    g = g[g["Viajero"] > 0].sort_values("Viajero", ascending=False)
    g["rank"] = g.groupby("Región").cumcount()
    g.loc[g["rank"] >= per_region, "País"] = OTHERS
    g = g.groupby(["Región", "País"], as_index=False)["Viajero"].sum()
    g["id"] = g["Región"] + "/" + g["País"]
    return g


def parent_of(node: str) -> str:
    return node.rsplit("/", 1)[0] if "/" in node else ROOT_ID


def select_node(sub: pd.DataFrame, node: str) -> pd.DataFrame:
    """Filas de la región o del país elegidos en el treemap."""
    if node == ROOT_ID:
        return sub
    region, _, country = node.partition("/")
    out = sub[sub["Región"] == region]
    if country and country != OTHERS:
        out = out[out["País"] == country]
    elif country == OTHERS:
        top = out.groupby("País")["Viajero"].sum().nlargest(10).index
        out = out[~out["País"].isin(top)]
    return out


def border_ranking(sub: pd.DataFrame) -> pd.DataFrame:
    g = sub.groupby(["Frontera", "Vía"], as_index=False)["Viajero"].sum()
    g = g[g["Viajero"] > 0]
    g["Punto"] = g["Frontera"].str.replace(r"^\d+\s*", "", regex=True)
    return g.sort_values("Viajero")


if __name__ == "__main__":
    arr = load_arrivals()
    print(arr.shape, arr["Fecha"].min().date(), arr["Fecha"].max().date())
    print(yearly_by_via(arr).pivot(index="Año", columns="Vía", values="Viajero").tail())
