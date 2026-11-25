"""Motor científico de CausalImpact, sem I/O, Spark, MLflow ou serviços cloud.

Usa a distribuição ``tfp-causalimpact`` publicada pelo projeto Google. Não
implementa um substituto do algoritmo. O chamador controla ingestão, corte,
idempotência, persistência, origem dos dados e permissões.
"""
from __future__ import annotations

import hashlib
import json
import math
import platform
import time
from datetime import date, timedelta
from importlib import metadata
from typing import Any, Mapping

import numpy as np
import pandas as pd

CONTRACT_VERSION = "causal-model-v1"
INPUT_COLUMNS = ["date", "treated", "control_a", "control_b"]
ENGINE_DISTRIBUTION = "tfp-causalimpact"
ENGINE_VERSION = "0.2.0"
ENGINE_REPOSITORY = "https://github.com/google/tfp-causalimpact"
TESTED_REQUIREMENTS = {
    "tfp-causalimpact": "0.2.0",
    "tensorflow": "2.18.1",
    "tensorflow-probability": "0.25.0",
    "tf-keras": "2.18.0",
    "numpy": "1.26.4",
    "pandas": "2.2.3",
    "scipy": "1.14.1",
    "altair": "5.5.0",
}
DEFAULTS = {
    "alpha": 0.05,
    "seed": [42, 2026],
    "num_results": 300,
    "num_warmup_steps": 100,
    "weekly_seasonality": True,
    "prior_level_sd": 0.01,
    "run_placebo": False,
    "placebo_days": 14,
    "placebo_num_results": 300,
    "placebo_num_warmup_steps": 100,
}


class DataContractError(ValueError):
    """Entrada ou configuração inadequada para o estudo definido."""


class CausalAnalysisError(RuntimeError):
    """Dependência incorreta ou resultado científico inválido."""


def _hash_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _iso_date(value: Any, name: str) -> date:
    if not isinstance(value, str) or len(value) != 10:
        raise DataContractError(f"{name} deve ser uma data ISO YYYY-MM-DD.")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise DataContractError(f"{name} contém data inválida.") from error
    if parsed.isoformat() != value:
        raise DataContractError(f"{name} deve usar YYYY-MM-DD.")
    return parsed


def normalize_config(config: Mapping[str, Any]) -> dict[str, Any]:
    """Configuração explícita; o motor não escolhe datas olhando o efeito."""
    if not isinstance(config, Mapping):
        raise DataContractError("config deve ser um objeto/dicionário.")
    required = {"pre_start", "intervention_date", "as_of"}
    unknown = set(config) - required - set(DEFAULTS)
    if required - set(config):
        raise DataContractError(f"Configuração incompleta: {sorted(required - set(config))}.")
    if unknown:
        raise DataContractError(f"Parâmetros desconhecidos: {sorted(unknown)}.")
    out = {**DEFAULTS, **dict(config)}
    start = _iso_date(out["pre_start"], "pre_start")
    intervention = _iso_date(out["intervention_date"], "intervention_date")
    end = _iso_date(out["as_of"], "as_of")
    if (intervention - start).days != 84:
        raise DataContractError("Este estudo exige exatamente 84 dias de pré-período.")
    if end < intervention or (end - intervention).days + 1 < 14:
        raise DataContractError("O primeiro corte exige pelo menos 14 dias de pós-período.")
    if (end - start).days + 1 > 730:
        raise DataContractError("Corte acima de 730 dias: reveja explicitamente o estudo antes de executar.")
    for name in ("num_results", "placebo_num_results"):
        if isinstance(out[name], bool) or not isinstance(out[name], int) or not 100 <= out[name] <= 5000:
            raise DataContractError(f"{name} deve ser inteiro entre 100 e 5000.")
    for name in ("num_warmup_steps", "placebo_num_warmup_steps"):
        if isinstance(out[name], bool) or not isinstance(out[name], int) or not 1 <= out[name] <= 2000:
            raise DataContractError(f"{name} deve ser inteiro entre 1 e 2000.")
    if not isinstance(out["placebo_days"], int) or isinstance(out["placebo_days"], bool) or not 7 <= out["placebo_days"] <= 28:
        raise DataContractError("placebo_days deve ser inteiro entre 7 e 28.")
    for name in ("weekly_seasonality", "run_placebo"):
        if not isinstance(out[name], bool):
            raise DataContractError(f"{name} deve ser booleano.")
    for name in ("alpha", "prior_level_sd"):
        if isinstance(out[name], bool) or not isinstance(out[name], (int, float)) or not math.isfinite(out[name]):
            raise DataContractError(f"{name} deve ser numérico e finito.")
        out[name] = float(out[name])
    if not 0 < out["alpha"] < 1 or not 0 < out["prior_level_sd"] <= 1:
        raise DataContractError("alpha deve estar em (0,1) e prior_level_sd em (0,1].")
    seed = out["seed"]
    if isinstance(seed, int) and not isinstance(seed, bool):
        seed = [0, seed]
    if not isinstance(seed, (tuple, list)) or len(seed) != 2 or any(
        isinstance(x, bool) or not isinstance(x, int) or not 0 <= x < 2**31 for x in seed
    ):
        raise DataContractError("seed deve conter dois inteiros não negativos menores que 2**31.")
    out["seed"] = list(seed)
    return out


def prepare_inputs(df: pd.DataFrame, config: Mapping[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Valida o snapshot completo e retorna uma cópia ordenada, indexada pela data.

    Não agrega duplicatas, não preenche faltantes e não corta linhas silenciosamente.
    Metadados adicionais no DataFrame não são usados como controles.
    """
    cfg = normalize_config(config)
    if not isinstance(df, pd.DataFrame) or df.empty or not df.columns.is_unique:
        raise DataContractError("Esperado DataFrame não vazio e com nomes de colunas únicos.")
    if set(INPUT_COLUMNS) - set(df.columns):
        raise DataContractError(f"Colunas ausentes: {sorted(set(INPUT_COLUMNS) - set(df.columns))}.")
    data = df[INPUT_COLUMNS].copy(deep=True)
    try:
        parsed = pd.to_datetime(data["date"], errors="raise")
    except (ValueError, TypeError) as error:
        raise DataContractError("date contém valor inválido.") from error
    if parsed.isna().any() or not hasattr(parsed, "dt") or parsed.dt.tz is not None:
        raise DataContractError("date exige datas diárias não nulas, sem timezone ou horário.")
    if not parsed.eq(parsed.dt.normalize()).all():
        raise DataContractError("Agregue e feche o dia na origem; date não pode conter horário.")
    data["date"] = parsed
    if data["date"].duplicated().any():
        raise DataContractError("Há mais de uma observação por date; resolva revisões antes do ajuste.")
    data = data.sort_values("date").set_index("date")
    expected = pd.date_range(cfg["pre_start"], cfg["as_of"], freq="D", name="date")
    if not data.index.equals(expected):
        missing = expected.difference(data.index)
        extra = data.index.difference(expected)
        raise DataContractError(
            f"Calendário não corresponde ao corte: {len(missing)} dias ausentes e "
            f"{len(extra)} dias fora de [pre_start, as_of]. Não há imputação automática."
        )
    for column in INPUT_COLUMNS[1:]:
        if pd.api.types.is_bool_dtype(data[column]):
            raise DataContractError(f"{column} deve conter contagens inteiras, não booleanos.")
        try:
            values = pd.to_numeric(data[column], errors="raise").to_numpy(dtype=float)
        except (TypeError, ValueError) as error:
            raise DataContractError(f"{column} contém valor não numérico.") from error
        if not np.isfinite(values).all() or (values < 0).any() or not np.equal(values, np.floor(values)).all():
            raise DataContractError(f"{column} exige contagens inteiras, não negativas e finitas.")
        if (values > 2**53 - 1).any():
            raise DataContractError(f"{column} excede o intervalo inteiro exato de float64.")
        data[column] = values
    pre = data.loc[data.index < pd.Timestamp(cfg["intervention_date"])]
    for column in INPUT_COLUMNS[1:]:
        if float(pre[column].std(ddof=0)) == 0:
            raise DataContractError(f"{column} não varia no pré; o modelo padronizado não é adequado.")
    return data, cfg


def _data_hash(data: pd.DataFrame) -> str:
    rows = [[index.date().isoformat(), *[int(value) for value in row]]
            for index, row in zip(data.index, data[INPUT_COLUMNS[1:]].to_numpy())]
    return _hash_json({"columns": INPUT_COLUMNS, "rows": rows})


def dependency_versions() -> dict[str, str]:
    versions = {"python": platform.python_version()}
    for name in TESTED_REQUIREMENTS:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = "NOT_INSTALLED"
    return versions


def _load_engine():
    versions = dependency_versions()
    if versions[ENGINE_DISTRIBUTION] != ENGINE_VERSION:
        raise CausalAnalysisError(f"Instale {ENGINE_DISTRIBUTION}=={ENGINE_VERSION} no Environment.")
    for conflict in ("tfcausalimpact", "pycausalimpact", "causalimpact"):
        try:
            metadata.version(conflict)
        except metadata.PackageNotFoundError:
            continue
        raise CausalAnalysisError(f"Distribuição {conflict} conflita no módulo causalimpact. Use somente tfp-causalimpact.")
    try:
        import causalimpact
        import tensorflow as tf
    except (ImportError, AttributeError) as error:
        raise CausalAnalysisError("Não foi possível importar a stack TensorFlow/TFP. Confira as versões fixadas.") from error
    if not callable(getattr(causalimpact, "fit_causalimpact", None)):
        raise CausalAnalysisError("Módulo causalimpact incorreto: API Google fit_causalimpact ausente.")
    return causalimpact, tf, versions


def _fit(data, start, intervention, end, cfg, engine, tf, placebo=False):
    """Chama a API pública real. A resposta pós é mascarada pelo pacote Google."""
    samples = cfg["placebo_num_results"] if placebo else cfg["num_results"]
    warmup = cfg["placebo_num_warmup_steps"] if placebo else cfg["num_warmup_steps"]
    seasons = [engine.Seasons(num_seasons=7)] if cfg["weekly_seasonality"] else []
    with tf.device("/CPU:0"):
        return engine.fit_causalimpact(
            data,
            pre_period=(pd.Timestamp(start), pd.Timestamp(intervention) - pd.Timedelta(days=1)),
            post_period=(pd.Timestamp(intervention), pd.Timestamp(end)),
            alpha=cfg["alpha"],
            seed=tuple(cfg["seed"]),
            data_options=engine.DataOptions(outcome_column="treated", dtype=tf.float64),
            model_options=engine.ModelOptions(prior_level_sd=cfg["prior_level_sd"], seasons=seasons),
            inference_options=engine.InferenceOptions(num_results=samples, num_warmup_steps=warmup),
        )


def _number(value):
    number = float(value)
    return number if math.isfinite(number) else None


def _summary(impact) -> dict[str, float]:
    avg, cum = impact.summary.loc["average"], impact.summary.loc["cumulative"]
    result = {
        "actual_average": _number(avg["actual"]),
        "actual_cumulative": _number(cum["actual"]),
        "predicted_average": _number(avg["predicted"]),
        "predicted_average_lower": _number(avg["predicted_lower"]),
        "predicted_average_upper": _number(avg["predicted_upper"]),
        "predicted_cumulative": _number(cum["predicted"]),
        "predicted_cumulative_lower": _number(cum["predicted_lower"]),
        "predicted_cumulative_upper": _number(cum["predicted_upper"]),
        "average_effect": _number(avg["abs_effect"]),
        "average_effect_lower": _number(avg["abs_effect_lower"]),
        "average_effect_upper": _number(avg["abs_effect_upper"]),
        "cumulative_effect": _number(cum["abs_effect"]),
        "cumulative_effect_lower": _number(cum["abs_effect_lower"]),
        "cumulative_effect_upper": _number(cum["abs_effect_upper"]),
        "relative_effect": _number(avg["rel_effect"]),
        "relative_effect_lower": _number(avg["rel_effect_lower"]),
        "relative_effect_upper": _number(avg["rel_effect_upper"]),
        "posterior_tail_probability": _number(avg["p_value"]),
    }
    if any(value is None for value in result.values()):
        raise CausalAnalysisError("Resumo causal contém valores não finitos.")
    if not 0 <= result["posterior_tail_probability"] <= 1:
        raise CausalAnalysisError("Probabilidade de cauda posterior fora de [0,1].")
    for stem in ("predicted_average", "predicted_cumulative", "average_effect", "cumulative_effect", "relative_effect"):
        if result[stem + "_lower"] > result[stem + "_upper"]:
            raise CausalAnalysisError("Intervalo posterior invertido.")
    return result


def _series(impact, data, intervention):
    mapping = {
        "observed": "observed", "counterfactual": "posterior_mean",
        "counterfactual_lower": "posterior_lower", "counterfactual_upper": "posterior_upper",
        "effect": "point_effects_mean", "effect_lower": "point_effects_lower", "effect_upper": "point_effects_upper",
        "cumulative_effect": "cumulative_effects_mean", "cumulative_effect_lower": "cumulative_effects_lower",
        "cumulative_effect_upper": "cumulative_effects_upper",
    }
    if not impact.series.index.equals(data.index):
        raise CausalAnalysisError("Índice do resultado não corresponde ao snapshot de entrada.")
    rows = []
    for index, item in impact.series.iterrows():
        is_post = index >= pd.Timestamp(intervention)
        record = {"date": index.date().isoformat(), "period": "POST" if is_post else "PRE"}
        record.update({target: _number(item[source]) for target, source in mapping.items()})
        # O acumulado causal começa na intervenção, não no pré.
        if not is_post:
            for name in ("cumulative_effect", "cumulative_effect_lower", "cumulative_effect_upper"):
                record[name] = None
        if is_post and any(record[name] is None for name in mapping):
            raise CausalAnalysisError("Série pós contém valores não finitos.")
        rows.append(record)
    return rows


def _placebo_diagnostics(data, cfg, engine, tf):
    pre_end = date.fromisoformat(cfg["intervention_date"]) - timedelta(days=1)
    pseudo_intervention = pre_end - timedelta(days=cfg["placebo_days"] - 1)
    pre_only = data.loc[:pd.Timestamp(pre_end)].copy()
    started = time.perf_counter()
    impact = _fit(pre_only, cfg["pre_start"], pseudo_intervention, pre_end, cfg, engine, tf, placebo=True)
    summary = _summary(impact)
    holdout = impact.series.loc[pd.Timestamp(pseudo_intervention):pd.Timestamp(pre_end)]
    residual = holdout["observed"] - holdout["posterior_mean"]
    coverage = ((holdout["observed"] >= holdout["posterior_lower"]) &
                (holdout["observed"] <= holdout["posterior_upper"])).mean()
    return {
        "status": "EXECUTED", "pre_start": cfg["pre_start"],
        "pre_end": (pseudo_intervention - timedelta(days=1)).isoformat(),
        "pseudo_intervention_date": pseudo_intervention.isoformat(), "as_of": pre_end.isoformat(),
        "training_days": len(pre_only) - cfg["placebo_days"], "holdout_days": cfg["placebo_days"],
        "holdout_mae": float(residual.abs().mean()), "holdout_rmse": float(np.sqrt(np.mean(residual**2))),
        "pointwise_interval_coverage": float(coverage),
        "zero_inside_cumulative_interval": bool(summary["cumulative_effect_lower"] <= 0 <= summary["cumulative_effect_upper"]),
        "summary": summary, "duration_seconds": time.perf_counter() - started,
        "interpretation": "Diagnóstico pré-intervenção; não prova ausência de confundimento ou validade causal.",
    }


def run_causal_analysis(df: pd.DataFrame, config: Mapping[str, Any]) -> dict[str, Any]:
    """Estima efeito com Google TFP CausalImpact e devolve apenas tipos JSON.

    O pré mantém 84 dias e datas fixas. y pós não entra na verossimilhança de
    ajuste. Controles pós participam do contrafactual e do prior de regressão
    padrão da versão 0.2.0: não se afirma que todo cálculo usa somente o pré.
    Resultados não são aprovação automática da campanha ou evidência cloud.
    """
    started = time.perf_counter()
    data, cfg = prepare_inputs(df, config)
    engine, tf, versions = _load_engine()
    fit_started = time.perf_counter()
    impact = _fit(data, cfg["pre_start"], cfg["intervention_date"], cfg["as_of"], cfg, engine, tf)
    fit_seconds = time.perf_counter() - fit_started
    summary = _summary(impact)
    rows = _series(impact, data, cfg["intervention_date"])
    pre_mask = data.index < pd.Timestamp(cfg["intervention_date"])
    pre_residual = impact.series.loc[pre_mask, "observed"] - impact.series.loc[pre_mask, "posterior_mean"]
    warnings = [
        "Dados observacionais exigem controles não afetados e relação estável; o modelo não verifica essas hipóteses sozinho.",
        "O prior de regressão padrão do pacote Google0.2.0 usa controles pré e pós; a resposta pós é mascarada no ajuste.",
        "posterior_tail_probability não é a probabilidade literal de causalidade nem um critério de aprovação comercial.",
        "A configuração didática de amostragem não equivale a um diagnóstico completo de convergência MCMC.",
    ]
    differences = {name: {"tested": wanted, "installed": versions[name]}
                   for name, wanted in TESTED_REQUIREMENTS.items() if versions[name] != wanted}
    if differences:
        warnings.append("Há dependências diferentes da combinação testada; compare resultados e valide o ambiente explicitamente.")
    placebo = (_placebo_diagnostics(data, cfg, engine, tf) if cfg["run_placebo"]
               else {"status": "NOT_RUN", "reason": "run_placebo=False; execução curta é o padrão."})
    if placebo.get("status") == "EXECUTED" and not placebo["zero_inside_cumulative_interval"]:
        warnings.append("O intervalo do placebo exclui zero: investigar o ajuste e os controles antes de interpretar causalidade.")
    input_hash = _data_hash(data)
    pre_hash = _data_hash(data.loc[pre_mask])
    analysis_config = {key: value for key, value in cfg.items() if key != "as_of"}
    analysis_config.update({"dtype": "float64", "contract_version": CONTRACT_VERSION, "dependencies": versions})
    analysis_config_hash = _hash_json(analysis_config)
    result = {
        "contract_version": CONTRACT_VERSION,
        "engine": {"distribution": ENGINE_DISTRIBUTION, "version": versions[ENGINE_DISTRIBUTION],
                   "repository": ENGINE_REPOSITORY, "api": "causalimpact.fit_causalimpact", "device": "CPU", "dtype": "float64"},
        "dependencies": versions, "dependency_differences_from_tested": differences,
        "config": cfg, "input_sha256": input_hash, "pre_sha256": pre_hash,
        "analysis_config_hash": analysis_config_hash,
        "analysis_key": _hash_json({"input_sha256": input_hash, "analysis_config_hash": analysis_config_hash, "as_of": cfg["as_of"]}),
        "counts": {"rows": len(data), "pre_days": int(pre_mask.sum()), "post_days": int((~pre_mask).sum())},
        "interval_level": 1 - cfg["alpha"], "summary": summary, "series": rows,
        "diagnostics": {"pre_in_sample_mae": float(pre_residual.abs().mean()),
                        "pre_in_sample_mae_is_holdout": False,
                        "controls_pre_correlation": float(data.loc[pre_mask, ["control_a", "control_b"]].corr().iloc[0, 1]),
                        "placebo": placebo, "warnings": warnings},
        "timing": {"main_fit_seconds": fit_seconds, "total_seconds": time.perf_counter() - started},
        "events": [{"event": "INPUT_VALIDATED", "rows": len(data)},
                   {"event": "GOOGLE_CAUSALIMPACT_EXECUTED", "as_of": cfg["as_of"]},
                   {"event": "PLACEBO_" + placebo["status"]}],
        "interpretation": {"relative_effect_unit": "fraction", "cumulative_interval_source": "Google posterior predictive trajectories",
                           "observed_post_used_to_fit_likelihood": False,
                           "causal_validity_automatically_approved": False,
                           "business_success_automatically_approved": False},
    }
    json.dumps(result, allow_nan=False)
    return result
