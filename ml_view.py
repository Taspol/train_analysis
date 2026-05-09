"""Streamlit ML Forecast tab — pre-trip (TTM) + live ETA refinement."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from ml import live_eta, pretrip
import live_view
import srt_socket


def _format_band(p05: float, p50: float, p95: float) -> str:
    return f"**{p50:.0f} min** &nbsp; (90% CI: {p05:.0f} → {p95:.0f})"


def _render_pretrip() -> None:
    st.markdown("#### Pre-trip ETA forecast")
    st.caption(
        "IBM Tiny Time Mixer (TTM) zero-shot forecast on the daily per-station delay matrix. "
        "Confidence interval comes from walk-forward validation residuals."
    )

    stations = pretrip.stations()
    last_date = pretrip._load_matrix().index.max().date()

    col1, col2 = st.columns(2)
    with col1:
        target_date = st.date_input(
            "Travel date",
            min_value=last_date + timedelta(days=1),
            max_value=last_date + timedelta(days=pretrip.HORIZON),
            value=last_date + timedelta(days=1),
        )
    with col2:
        station_name = st.selectbox(
            "Station",
            options=stations,
            index=min(len(stations) - 1, 18),
        )

    if not station_name:
        return
    station_idx = stations.index(station_name)

    try:
        result = pretrip.predict(pd.Timestamp(target_date), station_idx)
    except FileNotFoundError:
        st.error(
            "ML artifacts missing. Run `python3 -m ml.train` once to generate "
            "`data/delay_matrix.parquet`, `ttm_residuals.npy`, and `live_eta_model.pkl`."
        )
        return
    except Exception as e:
        st.error(f"Forecast failed: {e}")
        return

    st.markdown(
        f"""
        <div style="background:#ffffff;padding:1.5rem;border-radius:1rem;
                   border:1px solid #e2e8f0;margin-top:1rem;">
            <div style="color:#64748b;font-size:0.85rem;text-transform:uppercase;
                        letter-spacing:0.1em;">Predicted arr_delay</div>
            <div style="font-size:2rem;font-weight:700;color:#0f172a;margin-top:0.5rem;">
                {result.p50:.0f} min
            </div>
            <div style="color:#475569;margin-top:0.25rem;">
                90% CI: <strong>{result.p05:.0f} → {result.p95:.0f}</strong> min
                &nbsp;·&nbsp; {result.station_name} on {result.target_date.date()}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.checkbox("Show forecast for all stations on this date"):
        days_ahead = (pd.Timestamp(target_date) - pretrip._load_matrix().index.max()).days
        forecast = pretrip.forecast_next_days(days=days_ahead)[days_ahead - 1]
        df = pd.DataFrame({"Station": stations, "Predicted Delay (min)": forecast.round(1)})
        st.dataframe(df, use_container_width=True, hide_index=True)

    metrics = pretrip.load_metrics()
    if metrics:
        with st.expander("Model accuracy"):
            ov = metrics["overall"]
            st.markdown(
                f"**Walk-forward validation** &nbsp;·&nbsp; "
                f"context={metrics['context_length']}d, horizon={metrics['prediction_horizon']}d, "
                f"val window={metrics['val_days']}d"
            )
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("TTM MAE (min)", f"{ov['ttm_mae_min']:.2f}",
                       f"-{ov['persistence_mae_min'] - ov['ttm_mae_min']:.2f} vs persistence",
                       delta_color="inverse")
            mc2.metric("TTM RMSE (min)", f"{ov['ttm_rmse_min']:.2f}",
                       f"-{ov['persistence_rmse_min'] - ov['ttm_rmse_min']:.2f} vs persistence",
                       delta_color="inverse")
            mc3.metric("Improvement", f"{ov['improvement_pct']:.1f}%",
                       "TTM beats baseline")

            per_stn_df = pd.DataFrame(metrics["per_station"]).rename(
                columns={
                    "idx": "Station #",
                    "station_name": "Station",
                    "ttm_mae": "TTM MAE (min)",
                    "baseline_mae": "Persistence MAE (min)",
                    "improvement_pct": "Δ vs baseline (%)",
                }
            ).round(2)
            st.markdown("**Per-station MAE**")
            st.dataframe(per_stn_df, use_container_width=True, hide_index=True)


def _render_live() -> None:
    st.markdown("#### Live ETA refinement")
    st.caption(
        "Quantile gradient-boosted regression. Given the train's currently-observed station + delay, "
        "predicts the delay at every remaining station with a 90% band."
    )

    available = live_eta.available_models()
    label_map = {"gbr": "sklearn GBR (default)", "lgbm": "LightGBM (Optuna-tuned)"}
    if len(available) > 1:
        choice = st.radio(
            "Model",
            options=available,
            format_func=lambda k: label_map.get(k, k),
            horizontal=True,
            index=available.index("lgbm") if "lgbm" in available else 0,
        )
    else:
        choice = available[0] if available else "gbr"

    stations = pretrip.stations()
    n = len(stations)

    cached = live_view._load_runhash_cache()
    runhash = cached.get("runhash") if cached else None

    use_live = False
    if runhash:
        use_live = st.toggle(
            f"Pull current state from WebSocket (cached runhash: {runhash[:10]}…)",
            value=True,
        )

    cur_idx, cur_delay = None, None
    if use_live:
        try:
            stations_live = srt_socket.fetch_train_stations(runhash)
            cur_idx = live_view._resolve_current_index(stations_live)
            cur_delay = live_view._coerce_int(
                stations_live[cur_idx].get("act_arr_late")
                or stations_live[cur_idx].get("act_dep_late")
            )
            st.info(
                f"Live: at **{stations_live[cur_idx].get('stop_name','')}** "
                f"with **{cur_delay} min** delay."
            )
        except Exception as e:
            st.warning(f"Live fetch failed, falling back to manual input: {e}")
            use_live = False

    if not use_live:
        col1, col2 = st.columns(2)
        with col1:
            cur_station = st.selectbox(
                "Currently at station",
                options=stations[:-1],
                index=0,
                key="live_cur_stn",
            )
            cur_idx = stations.index(cur_station)
        with col2:
            cur_delay = st.number_input(
                "Observed delay (min)",
                value=10,
                step=5,
                key="live_cur_delay",
            )

    terminal = cur_idx is None or cur_idx >= n - 1
    if terminal:
        st.success("Train has reached the terminal station.")
    else:
        try:
            preds = live_eta.predict_remaining(
                cur_idx=cur_idx,
                cur_delay=float(cur_delay or 0),
                n_stations=n,
                today=date.today(),
                model_type=choice,
            )
        except FileNotFoundError:
            st.error("Run `python3 -m ml.train` first to build the live ETA model.")
            return

        rows = [
            {
                "Station": stations[p.target_idx],
                "Pred. Delay (min)": round(p.p50, 1),
                "Lower (5%)": round(p.p05, 1),
                "Upper (95%)": round(p.p95, 1),
            }
            for p in preds
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    comp = live_eta.load_comparison()
    if comp:
        with st.expander("Model comparison — time-based holdout (last 60 days)"):
            live = comp.get("live_eta_task", comp)
            rows = []
            for key, label in [
                ("persistence", "Persistence baseline"),
                ("sklearn_gbr", "sklearn GBR (time-split)"),
                ("lightgbm_tuned", "LightGBM raw (Optuna)"),
                ("lightgbm_conformal", "LightGBM + conformal calibration"),
            ]:
                m = live.get(key, {})
                if not m:
                    continue
                rows.append({
                    "Model": label,
                    "q50 MAE (min)": round(m.get("q50_mae", float("nan")), 3),
                    "90% CI coverage": (f"{m['ci_coverage_90']*100:.1f}%"
                                          if "ci_coverage_90" in m else "—"),
                    "CI width (min)": (round(m["ci_width_min"], 1)
                                          if "ci_width_min" in m else "—"),
                })
            st.markdown("**Live ETA refinement task** (predict tgt-station delay given cur-station delay)")
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            st.caption(
                f"Split: time-based, last {comp.get('val_days','?')} days held out "
                f"(cutoff {comp.get('cutoff_date','?')}, {comp.get('val_rows_live','?')} rows). "
                f"LightGBM raw under-covers 90% target; conformal calibration "
                f"(δ={live.get('lightgbm_conformal',{}).get('conformal_delta_min',0):.1f} min) "
                f"restores coverage."
            )

            pretrip_data = comp.get("pretrip_task", {})
            if pretrip_data:
                st.markdown("**Pre-trip task** (predict next-day delay at any station)")
                pre_rows = [
                    {"Model": "IBM TTM zero-shot",
                      "Per-station MAE (min)": round(pretrip_data.get("ttm_zero_shot_mae", 0), 3)},
                    {"Model": "LightGBM (date features only)",
                      "Per-station MAE (min)": round(pretrip_data.get("lgbm_pretrip_mae", 0), 3)},
                ]
                st.dataframe(pd.DataFrame(pre_rows), use_container_width=True, hide_index=True)
                st.caption(
                    f"TTM and LightGBM are tied on this task. TTM wins on "
                    f"{sum(1 for s in pretrip_data['per_station_mae'] if s['better']=='TTM')}/45 stations, "
                    f"LightGBM wins on "
                    f"{sum(1 for s in pretrip_data['per_station_mae'] if s['better']=='LGBM')}/45."
                )

            with st.popover("LightGBM best hyperparameters"):
                st.json(live["lightgbm_tuned"]["best_params"])


def render_ml_tab() -> None:
    st.markdown("### ML Forecast")
    sub_pretrip, sub_live = st.tabs(["Pre-trip", "Live refinement"])
    with sub_pretrip:
        _render_pretrip()
    with sub_live:
        _render_live()
