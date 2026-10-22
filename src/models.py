"""Reproduce las predicciones del Lab 1 (mismo split 70/30) para el tablero. No se entrenan modelos nuevos."""
import warnings
import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from src.data import ROOT, load_arrivals

OUT = ROOT / "outputs"
SERIES = ["Total", "Aérea", "Terrestre"]


def build_series(df: pd.DataFrame) -> dict[str, pd.Series]:
    total = df.groupby("Fecha")["Viajero"].sum().asfreq("MS")
    series = {"Total": total}
    for via in ["Aérea", "Terrestre"]:
        series[via] = df[df["Vía"] == via].groupby("Fecha")["Viajero"].sum().asfreq("MS")
    return series


def split_70_30(s: pd.Series):
    cut = int(len(s) * 0.70)
    return s.iloc[:cut], s.iloc[cut:]


def arima(train, h):
    res = SARIMAX(np.log(train), order=(1, 1, 1)).fit(disp=False)
    return np.exp(res.get_forecast(h).predicted_mean.values)


def holt_winters(train, h):
    res = ExponentialSmoothing(np.log(train), trend="add", seasonal="add", seasonal_periods=12).fit()
    return np.exp(np.asarray(res.forecast(h)))


def seasonal_naive(train, h):
    last = train.iloc[-12:].values
    return np.array([last[i % 12] for i in range(h)])


MODELS = {"ARIMA(1,1,1)": arima, "Holt-Winters": holt_winters, "Seasonal Naive": seasonal_naive}


def metrics(y, p):
    err = y - p
    return dict(MAE=np.mean(np.abs(err)), RMSE=np.sqrt(np.mean(err ** 2)),
                MAPE=np.mean(np.abs(err / y)) * 100)


def run():
    warnings.filterwarnings("ignore")
    series = build_series(load_arrivals())
    preds, rows = [], []
    for name, s in series.items():
        train, test = split_70_30(s)
        preds.append(pd.DataFrame({"Serie": name, "Fecha": s.index, "Modelo": "Observado",
                                   "Valor": s.values, "Tramo": ["train"] * len(train) + ["test"] * len(test)}))
        for model, fn in MODELS.items():
            p = fn(train, len(test))
            preds.append(pd.DataFrame({"Serie": name, "Fecha": test.index, "Modelo": model,
                                       "Valor": p, "Tramo": "test"}))
            rows.append({"Serie": name, "Modelo": model, **metrics(test.values, p)})
    pd.concat(preds).to_csv(OUT / "predictions.csv", index=False)
    met = pd.DataFrame(rows)
    met.to_csv(OUT / "metrics.csv", index=False)
    return met


if __name__ == "__main__":
    print(run().round(1).to_string(index=False))
