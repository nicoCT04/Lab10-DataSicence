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


if __name__ == "__main__":
    arr = load_arrivals()
    print(arr.shape, arr["Fecha"].min().date(), arr["Fecha"].max().date())
    print(yearly_by_via(arr).pivot(index="Año", columns="Vía", values="Viajero").tail())
