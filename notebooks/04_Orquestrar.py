# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "4"
# ///
# MAGIC %md
# MAGIC # 04 · Execute um ciclo completo
# MAGIC 
# MAGIC Este é o notebook de entrada do Job: **ler e validar → aceitar snapshot → executar CausalImpact → registrar evidência → conferir resultado**.
# MAGIC 
# MAGIC Envie primeiro os arquivos 01 a 05. Depois, adicione um arquivo por execução. Sem arquivos novos, o resultado é reutilizado. Com o arquivo 07, a falha é parte da demonstração; adicione 08 para recuperar o fluxo.
# MAGIC 
# MAGIC Execute um ciclo por vez. O Job é manual, sem agenda, fila ou tentativas automáticas adicionais.
# MAGIC 
# MAGIC Antes de **Run All** interativo, selecione **Serverless → Environment → Standard versão 4 (Python 3.12)** e aplique. O template do Job já fixa essa versão.

# COMMAND ----------

# MAGIC %pip install tfp-causalimpact==0.2.0 tensorflow==2.18.1 tensorflow-probability==0.25.0 tf-keras==2.18.0 numpy==1.26.4 pandas==2.2.3 scipy==1.14.1 altair==5.5.0 matplotlib==3.9.4

# COMMAND ----------

dbutils.library.restartPython()

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

ciclo = demo.run_cycle()
print("CICLO CONCLUÍDO:", ciclo["panel"]["status"])
print("Corte:", ciclo["ingestion"]["as_of"])
print("Snapshot:", ciclo["ingestion"]["snapshot_id"])
print("Run MLflow:", ciclo["result"]["runtime"]["mlflow_run_id"])

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

# MAGIC %md
# MAGIC ## Continue por aqui
# MAGIC 
# MAGIC O guia [Integração Databricks](https://github.com/EasyBigDataBR/mba_mlops/blob/main/docs/INTEGRACAO_DATABRICKS.md) explica Git, Drive/Volume e parâmetros.
# MAGIC O [roteiro da demonstração](https://github.com/EasyBigDataBR/mba_mlops/blob/main/docs/DEMONSTRACAO.md) mostra a ordem dos arquivos.
# MAGIC 
# MAGIC Referências oficiais: [Google TFP CausalImpact](https://github.com/google/tfp-causalimpact) · [Git em Jobs](https://docs.databricks.com/aws/en/jobs/git) · [Limites da Free Edition](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations).
