# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · Estime o efeito da campanha
# MAGIC 
# MAGIC A pergunta é: **quantas conversões teríamos sem a campanha?** O Google TFP CausalImpact estima esse contrafactual e o compara com o observado.
# MAGIC 
# MAGIC O estudo mantém 84 dias de pré-período e começa com 14 dias de pós. Os controles representam séries não atingidas pela campanha no cenário sintético. O resultado traz incerteza; não é aprovação automática de uma decisão de negócio.
# MAGIC 
# MAGIC A primeira execução instala as dependências e reinicia o Python. Depois, as células seguintes continuam com uma sessão limpa.
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

demo.setup()
resultado = demo.analyze()
display(pd.DataFrame([resultado["summary"]]))
print("Evidência MLflow:", resultado["runtime"]["mlflow_run_id"])
print("Snapshot:", resultado["runtime"]["snapshot_id"])

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
# MAGIC ## O que observar
# MAGIC 
# MAGIC * **Efeito diário**: diferença entre observado e contrafactual.
# MAGIC * **Efeito acumulado**: soma dos efeitos desde a intervenção.
# MAGIC * **Faixa de 95%**: incerteza da estimativa; vem das trajetórias posteriores do modelo.
# MAGIC 
# MAGIC A resposta observada no pós fica fora da verossimilhança de ajuste. Os controles pós são usados no contrafactual e no prior de regressão padrão desta versão. Controles contaminados ou relações instáveis prejudicam a interpretação causal.
# MAGIC 
# MAGIC O cálculo é uma análise retrospectiva. Cada novo corte gera uma análise versionada no MLflow; não há endpoint de previsão em tempo real nem promoção automática de campanha.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Continue por aqui
# MAGIC 
# MAGIC O guia [Integração Databricks](https://github.com/EasyBigDataBR/mba_mlops/blob/main/docs/INTEGRACAO_DATABRICKS.md) explica Git, Drive/Volume e parâmetros.
# MAGIC O [roteiro da demonstração](https://github.com/EasyBigDataBR/mba_mlops/blob/main/docs/DEMONSTRACAO.md) mostra a ordem dos arquivos.
# MAGIC 
# MAGIC Referências oficiais: [Google TFP CausalImpact](https://github.com/google/tfp-causalimpact) · [Git em Jobs](https://docs.databricks.com/aws/en/jobs/git) · [Limites da Free Edition](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations).
