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
# MAGIC * `drive` é a fonte principal: preencha `source_path` com a URL privada de **01_Entrada_Databricks** e `drive_connection` com o nome da conexão Unity Catalog autorizada.
# MAGIC * Os campos privados começam vazios. Na primeira tentativa, a mensagem de configuração pede que você os preencha; depois execute a célula novamente.
# MAGIC * Mantenha **02_Reserva_Proximas_Execucoes** ao lado da Entrada. Não use a URL da pasta que contém as duas: a leitura do Drive inclui subpastas.
# MAGIC * `volume` é uma alternativa explícita. Nesse modo, informe uma subpasta como `/Volumes/mba/mlops_causalimpact/landing/causalimpact_demo`.
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
# MAGIC ## Confira a leitura do Drive antes de criar objetos
# MAGIC
# MAGIC Esta verificação lê a pasta configurada, confere nomes, tamanhos, hashes e o contrato dos CSVs. **Não cria tabelas, não publica snapshots e não executa CausalImpact.**
# MAGIC
# MAGIC No início, você deve ver **cinco arquivos**, **98 dias** e corte em **03/11/2026**. Se aparecerem dez arquivos antes da primeira aula, confira a URL: o Job deve ler somente a Entrada.
# MAGIC
# MAGIC Se a conexão falhar, confira OAuth, permissões e suporte do workspace. A fonte não será trocada automaticamente para Volume. No modo Drive, você não precisa copiar os arquivos para `/Volumes`.

# COMMAND ----------

import hashlib
from src.data_pipeline import plan_snapshot
from src.databricks_runtime import DataGateError

if config["source_mode"] == "drive":
    source_files, source_origins = demo.read_source_bytes()
    expected_files = {item["filename"]: item for item in demo.manifest["files"]}
    file_checks = []
    for name, payload in sorted(source_files.items()):
        actual_sha = hashlib.sha256(payload).hexdigest()
        expected = expected_files.get(name, {})
        file_checks.append({"filename": name, "bytes": len(payload),
                            "sha256": actual_sha,
                            "manifest_hash_ok": actual_sha == expected.get("sha256"),
                            "source_path": source_origins[name]})
    if not file_checks:
        raise DataGateError("A Entrada está vazia. Coloque os cinco CSVs iniciais e repita esta célula.")
    display(pd.DataFrame(file_checks))
    if not all(item["manifest_hash_ok"] for item in file_checks):
        raise DataGateError("Há arquivo desconhecido ou bytes diferentes do manifesto. Confira os CSVs originais antes de continuar.")
    preview = plan_snapshot(source_files, demo.manifest)
    print(json.dumps({"check": "DRIVE_READ_ONLY", "files": len(file_checks),
                      "status": preview["status"], "as_of": preview.get("as_of"),
                      "summary": preview["summary"]}, ensure_ascii=False, indent=2))
    if preview["status"] != "READY":
        raise DataGateError("A leitura funcionou, mas o contrato da entrada não está READY. Confira a sequência dos arquivos; o 07 é inválido de propósito.")
    print("LEITURA E CONTRATO APROVADOS. Nenhuma tabela, snapshot ou análise foi gravada nesta verificação.")
else:
    print("Modo Volume selecionado explicitamente. Prepare a pasta abaixo, envie os CSVs e confira a leitura no notebook 01.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Crie os objetos do exemplo
# MAGIC
# MAGIC Esta célula cria as tabelas `ci_demo_*` e, somente no modo Volume, a subpasta de entrada. No modo Drive, os arquivos recebidos serão guardados em `ci_demo_bronze`, com seus hashes, durante a ingestão. O catálogo precisa existir e você precisa das permissões necessárias.

# COMMAND ----------

print(json.dumps(demo.setup(create_input_dir=True), ensure_ascii=False, indent=2))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Sua primeira execução
# MAGIC
# MAGIC 1. Confira os cinco CSVs iniciais em **01_Entrada_Databricks**.
# MAGIC 2. Abra **01_Ingerir_Atualizacoes** e depois **02_Executar_CausalImpact**.
# MAGIC 3. Confira **03_Painel_e_Validacao**.
# MAGIC 4. Crie o Job com **05_Criar_Job**. Ele executará **04_Orquestrar** a cada clique em **Run now**.
# MAGIC 5. Nos próximos ciclos, mova um CSV da Reserva para a Entrada e clique em **Run now**. Não altere os parâmetros do Job para cada arquivo.
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
