# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Receba e confira os arquivos
# MAGIC 
# MAGIC Cada arquivo tem nome, conteúdo e hash conhecidos. Vamos checar tipos, datas, valores ausentes, duplicações e correções declaradas antes de aceitar um novo corte.
# MAGIC 
# MAGIC O arquivo **07 contém um erro proposital**. Sua execução deve falhar sem publicar uma nova análise. Depois, adicione o **08** e execute novamente; a correção libera o ciclo e a rejeição anterior continua no histórico.

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

demo.setup()
ingestao = demo.ingest()
print(json.dumps({k: v for k, v in ingestao.items() if k != "events"}, ensure_ascii=False, indent=2))
display(pd.DataFrame(ingestao["events"]))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Leia o resultado
# MAGIC 
# MAGIC **READY**: um snapshot novo foi aceito. **REUSED**: os mesmos dados já estavam aceitos.
# MAGIC 
# MAGIC **BLOCKED/INCOMPLETE**: corrija a entrada antes de seguir. A tabela `ci_demo_ingestion_control` explica o motivo. A bronze preserva os bytes recebidos, inclusive os rejeitados; a silver só recebe um snapshot aprovado.
# MAGIC 
# MAGIC Com `as_of` vazio, o corte vem dos dias completos presentes nos arquivos. Mantenha os arquivos anteriores na pasta e acrescente a próxima entrega.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Continue por aqui
# MAGIC 
# MAGIC O guia [Integração Databricks](https://github.com/EasyBigDataBR/mba_mlops/blob/main/docs/INTEGRACAO_DATABRICKS.md) explica Git, Drive/Volume e parâmetros.
# MAGIC O [roteiro da demonstração](https://github.com/EasyBigDataBR/mba_mlops/blob/main/docs/DEMONSTRACAO.md) mostra a ordem dos arquivos.
# MAGIC 
# MAGIC Referências oficiais: [Google TFP CausalImpact](https://github.com/google/tfp-causalimpact) · [Git em Jobs](https://docs.databricks.com/aws/en/jobs/git) · [Limites da Free Edition](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations).
