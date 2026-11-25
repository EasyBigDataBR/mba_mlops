# Databricks notebook source
# MAGIC %md
# MAGIC # 03 · Veja o que mudou
# MAGIC 
# MAGIC Confira o último resultado válido, o histórico das análises e a última tentativa de processamento.
# MAGIC 
# MAGIC Se a entrega atual falhar, **o gráfico anterior continua disponível**, acompanhado do alerta `PREVIOUS_VALID_RESULT`. Isso mostra um resultado preservado, não uma atualização bem-sucedida.
# MAGIC 
# MAGIC Este notebook só consulta as tabelas. Ele não treina, ingere ou agenda nada.

# COMMAND ----------

from pathlib import Path
import sys
import json
import pandas as pd

ROOT = next((p for p in (Path.cwd(), *Path.cwd().parents)
             if (p / "src" / "databricks_runtime.py").is_file()
             and (p / "data_demo" / "manifest.json").is_file()), None)
if ROOT is None:
    raise RuntimeError("Abra este notebook dentro do Git folder completo, ou use o Job com fonte Git. Não importe somente o .py isolado.")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.databricks_runtime import DemoRuntime, read_widgets, plot_effects
config = read_widgets(dbutils)
demo = DemoRuntime(spark, dbutils, config, ROOT)
print("Case sintético |", config["catalog"] + "." + config["schema"], "|", config["demo_id"])
print("Fonte:", config["source_mode"], "| Corte:", config["as_of"] or "último dia completo presente nos arquivos")

# COMMAND ----------

painel = demo.panel()
print("Situação:", painel["status"])
print("Última tentativa:", json.dumps(painel["latest_attempt"], ensure_ascii=False, default=str))
if painel["summary"]:
    display(pd.DataFrame([painel["summary"]]))
    display(pd.DataFrame(painel["checks"]))
    display(painel["history"])
    display(plot_effects(painel["effects"], demo.manifest["intervention_date"]))
else:
    print("Ainda não há análise publicada. Execute 01 e 02, ou o orquestrador 04.")

# COMMAND ----------

display(demo.frame("executions").orderBy("recorded_at", ascending=False))
display(demo.frame("ingestion_control").orderBy("recorded_at", ascending=False))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Compare os ciclos
# MAGIC 
# MAGIC Observe corte, hash dos dados, efeito médio, intervalo e efeito acumulado. Um acumulado maior também pode refletir mais dias observados. Compare a média e os intervalos antes de concluir que a campanha melhorou.
# MAGIC 
# MAGIC Na entrega 10, o número de dias e o corte permanecem iguais; muda uma contagem de um dia antigo. O snapshot e a análise mudam, sem duplicar o dia.
# MAGIC 
# MAGIC Para montar um dashboard SQL no Databricks, use as consultas em [sql/painel.sql](https://github.com/EasyBigDataBR/mba_mlops/blob/main/sql/painel.sql).

# COMMAND ----------

# MAGIC %md
# MAGIC ## Continue por aqui
# MAGIC 
# MAGIC O guia [Integração Databricks](https://github.com/EasyBigDataBR/mba_mlops/blob/main/docs/INTEGRACAO_DATABRICKS.md) explica Git, Drive/Volume e parâmetros.
# MAGIC O [roteiro da demonstração](https://github.com/EasyBigDataBR/mba_mlops/blob/main/docs/DEMONSTRACAO.md) mostra a ordem dos arquivos.
# MAGIC 
# MAGIC Referências oficiais: [Google TFP CausalImpact](https://github.com/google/tfp-causalimpact) · [Git em Jobs](https://docs.databricks.com/aws/en/jobs/git) · [Limites da Free Edition](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations).
