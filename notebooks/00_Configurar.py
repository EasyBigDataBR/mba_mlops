# Databricks notebook source
# MAGIC %md
# MAGIC # 00 · Prepare o case
# MAGIC 
# MAGIC Vamos acompanhar uma campanha do começo ao fim. Você entrega arquivos; o Databricks valida os dados, estima o efeito com CausalImpact e guarda as evidências.
# MAGIC 
# MAGIC **Todos os dados são sintéticos.** O catálogo é `mba`, o schema é `mlops_causalimpact` e as tabelas deste exemplo começam com `ci_demo_`.
# MAGIC 
# MAGIC Execute a próxima célula para criar os widgets. Confira os valores no topo; se mudar algum deles, execute a célula novamente. Use a mesma configuração nos demais notebooks e no Job.
# MAGIC 
# MAGIC * `volume`: envie os CSVs à subpasta indicada em `source_path`.
# MAGIC * `drive`: informe a URL privada da pasta e uma conexão Unity Catalog já autorizada. Confira a preparação no guia.
# MAGIC 
# MAGIC Comece enviando **somente os arquivos 01 a 05**, sem renomeá-los. Os demais entram um por vez.

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

# MAGIC %md
# MAGIC ## Crie os objetos do exemplo
# MAGIC 
# MAGIC Esta célula cria as tabelas `ci_demo_*` e, no modo Volume, a subpasta de entrada. O catálogo precisa existir e você precisa das permissões necessárias. Nenhum CSV é copiado automaticamente: você controla quando cada entrega aparece.

# COMMAND ----------

print(json.dumps(demo.setup(create_input_dir=True), ensure_ascii=False, indent=2))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Sua primeira execução
# MAGIC 
# MAGIC 1. Coloque os cinco CSVs iniciais na pasta de entrada.
# MAGIC 2. Abra **01_Ingerir_Atualizacoes** e depois **02_Executar_CausalImpact**.
# MAGIC 3. Confira **03_Painel_e_Validacao**.
# MAGIC 4. Crie o Job com **05_Criar_Job**. Ele executará **04_Orquestrar** a cada clique em **Run now**.
# MAGIC 
# MAGIC O código em `data_demo/` é a distribuição dos arquivos. O pipeline lê apenas a fonte configurada; estar no Git não significa que o CSV já entrou na demonstração.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Continue por aqui
# MAGIC 
# MAGIC O guia [Integração Databricks](https://github.com/EasyBigDataBR/mba_mlops/blob/main/docs/INTEGRACAO_DATABRICKS.md) explica Git, Drive/Volume e parâmetros.
# MAGIC O [roteiro da demonstração](https://github.com/EasyBigDataBR/mba_mlops/blob/main/docs/DEMONSTRACAO.md) mostra a ordem dos arquivos.
# MAGIC 
# MAGIC Referências oficiais: [Google TFP CausalImpact](https://github.com/google/tfp-causalimpact) · [Git em Jobs](https://docs.databricks.com/aws/en/jobs/git) · [Limites da Free Edition](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations).
