# Databricks notebook source
# MAGIC %md
# MAGIC # 05 · Crie seu Job manual
# MAGIC 
# MAGIC Execute este notebook uma vez depois de conferir os parâmetros. Ele cria **MBA_MLOPS_CAUSALIMPACT_MANUAL** com uma tarefa que busca `04_Orquestrar.py` na branch `main` do GitHub.
# MAGIC 
# MAGIC Se o Job deste exemplo já existir com a identificação esperada, a configuração será atualizada. Jobs de outras atividades não são alterados. Nenhuma execução começa nesta célula: você controla as demonstrações pelo botão **Run now**.
# MAGIC 
# MAGIC O SDK usa a autenticação do notebook. Se a conta não permitir a API, use a rota de criação pela interface descrita no guia.

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

from databricks.sdk import WorkspaceClient

settings = json.loads((ROOT / "jobs" / "job_template.json").read_text())
settings["tags"] = {"mba_mlops_demo": "causalimpact_demo_v1"}
for param in settings["parameters"]:
    param["default"] = str(config[param["name"]])

workspace = WorkspaceClient()
matches = list(workspace.jobs.list(name=settings["name"]))
if len(matches) > 1:
    raise RuntimeError("Há mais de um Job com esse nome. Confira os IDs na interface antes de continuar.")
if matches:
    job_id = matches[0].job_id
    previous = workspace.jobs.get(job_id=job_id)
    if (previous.settings.tags or {}).get("mba_mlops_demo") != "causalimpact_demo_v1":
        raise RuntimeError("Já existe um Job com esse nome e sem a identificação do demonstrador. Ele não foi alterado.")
    workspace.api_client.do("POST", "/api/2.2/jobs/reset", body={"job_id": job_id, "new_settings": settings})
    action = "CONFIGURAÇÃO ATUALIZADA"
else:
    created = workspace.api_client.do("POST", "/api/2.2/jobs/create", body=settings)
    job_id = created["job_id"]
    action = "JOB CRIADO"

print(action, "| job_id =", job_id)
print(workspace.config.host.rstrip("/") + "/#job/" + str(job_id))
print("Nenhuma run iniciada. Confira Serverless/Standard e a credencial Git; depois clique em Run now.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Antes de cada demonstração
# MAGIC 
# MAGIC 1. Acrescente somente o próximo CSV na pasta configurada.
# MAGIC 2. Abra este Job e clique em **Run now**.
# MAGIC 3. Leia o status da tarefa e abra as saídas do notebook.
# MAGIC 4. Confira o histórico pelo notebook 03 ou pelas consultas SQL.
# MAGIC 
# MAGIC O Job com fonte Git resolve `main` a cada run. Para congelar uma versão, substitua `git_branch` por `git_commit` no template, usando um SHA real do repositório. Não configure os dois campos juntos.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Continue por aqui
# MAGIC 
# MAGIC O guia [Integração Databricks](https://github.com/EasyBigDataBR/mba_mlops/blob/main/docs/INTEGRACAO_DATABRICKS.md) explica Git, Drive/Volume e parâmetros.
# MAGIC O [roteiro da demonstração](https://github.com/EasyBigDataBR/mba_mlops/blob/main/docs/DEMONSTRACAO.md) mostra a ordem dos arquivos.
# MAGIC 
# MAGIC Referências oficiais: [Google TFP CausalImpact](https://github.com/google/tfp-causalimpact) · [Git em Jobs](https://docs.databricks.com/aws/en/jobs/git) · [Limites da Free Edition](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations).
