-- Consultas somente leitura. Parâmetro string :demo_id = campanha_demo_v1.
-- Execute cada consulta separadamente no SQL Editor ou em uma célula SQL.

-- Q01: últimas tentativas; não confundir erro atual com resultado antigo.
SELECT recorded_at AS tentativa_utc, stage AS etapa, status, message,
       snapshot_id, analysis_id, attempt_id
FROM mba.mlops_causalimpact.ci_demo_executions
WHERE demo_id = :demo_id
ORDER BY recorded_at DESC
LIMIT 30;

-- Q02: histórico de análises concluídas. Intervalos de 95%, dados sintéticos.
SELECT committed_at AS publicado_utc, as_of AS corte, row_count AS dias,
       post_days AS dias_pos, average_effect AS efeito_medio,
       average_effect_lower AS medio_inferior, average_effect_upper AS medio_superior,
       cumulative_effect AS efeito_acumulado,
       cumulative_effect_lower AS acumulado_inferior,
       cumulative_effect_upper AS acumulado_superior,
       relative_effect * 100 AS efeito_relativo_pct,
       mlflow_run_id, snapshot_id, analysis_id, code_sha256
FROM mba.mlops_causalimpact.ci_demo_analysis
WHERE demo_id = :demo_id
ORDER BY committed_at;

-- Q03: série do último resultado concluído/reutilizado.
-- Mostre Q01 ao lado desta série para revelar tentativas com erro.
WITH chosen AS (
  SELECT analysis_id
  FROM mba.mlops_causalimpact.ci_demo_executions
  WHERE demo_id = :demo_id AND stage = 'ANALYSIS'
    AND status IN ('SUCCESS', 'NO_CHANGE')
  ORDER BY recorded_at DESC LIMIT 1
)
SELECT e.date, e.period, e.observed, e.counterfactual,
       e.counterfactual_lower, e.counterfactual_upper,
       e.effect, e.effect_lower, e.effect_upper,
       e.cumulative_effect, e.cumulative_effect_lower, e.cumulative_effect_upper
FROM mba.mlops_causalimpact.ci_demo_effects e
JOIN chosen c ON e.analysis_id = c.analysis_id
WHERE e.demo_id = :demo_id
ORDER BY e.date;

-- Q04: SUPERSEDED conserva o erro de validação original.
SELECT recorded_at AS registrado_utc, filename, status, validation_status,
       row_count, errors_json, superseded_by, sha256, attempt_id
FROM mba.mlops_causalimpact.ci_demo_ingestion_control
WHERE demo_id = :demo_id
ORDER BY recorded_at DESC, filename;

-- Q05: mesma data máxima pode ter conteúdos diferentes.
SELECT committed_at AS aceito_utc, as_of AS corte, row_count AS dias,
       snapshot_id, source_mode, files_json, manifest_sha256
FROM mba.mlops_causalimpact.ci_demo_snapshots
WHERE demo_id = :demo_id
ORDER BY committed_at;

-- Q06: revisões do dia corrigido pela entrega10.
SELECT s.committed_at AS snapshot_utc, s.as_of AS corte,
       d.date, d.treated, d.control_a, d.control_b,
       d.source_file, d.source_revision, d.snapshot_id
FROM mba.mlops_causalimpact.ci_demo_silver d
JOIN mba.mlops_causalimpact.ci_demo_snapshots s
  ON d.demo_id = s.demo_id AND d.snapshot_id = s.snapshot_id
WHERE d.demo_id = :demo_id AND d.date = DATE '2026-10-26'
ORDER BY s.committed_at;

-- Q07: integridade física dos snapshots com marcador de commit.
SELECT s.snapshot_id, s.row_count AS dias_declarados,
       COUNT(d.date) AS linhas_persistidas,
       COUNT(DISTINCT d.date) AS datas_distintas,
       CASE WHEN COUNT(d.date) = s.row_count
              AND COUNT(DISTINCT d.date) = s.row_count
            THEN 'OK' ELSE 'REVISAR' END AS integridade
FROM mba.mlops_causalimpact.ci_demo_snapshots s
LEFT JOIN mba.mlops_causalimpact.ci_demo_silver d
  ON d.demo_id = s.demo_id AND d.snapshot_id = s.snapshot_id
WHERE s.demo_id = :demo_id
GROUP BY s.snapshot_id, s.row_count;

-- Documentação oficial:
-- https://docs.databricks.com/aws/en/sql/user/queries/query-parameters
-- https://docs.databricks.com/aws/en/dashboards/
-- https://github.com/google/tfp-causalimpact
