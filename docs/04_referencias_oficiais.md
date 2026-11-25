# Referências oficiais

Referências de origem e documentação para a revisão. As dependências do projeto existente ainda serão inspecionadas; esta lista não é um arquivo de instalação.

| Tema | URL |
|---|---|
| CausalImpact original | https://github.com/google/CausalImpact |
| Guia conceitual | https://google.github.io/CausalImpact/CausalImpact.html |
| Implementação Python publicada pelo Google | https://github.com/google/tfp-causalimpact |
| Quickstart Python | https://github.com/google/tfp-causalimpact/blob/main/docs/quickstart.ipynb |
| Distribuição tfp-causalimpact | https://pypi.org/project/tfp-causalimpact/ |
| Publicação do método | https://research.google/pubs/inferring-causal-impact-using-bayesian-structural-time-series-models/ |
| TensorFlow Probability 0.25 | https://github.com/tensorflow/probability/releases/tag/v0.25.0 |
| Limites Databricks Free | https://docs.databricks.com/aws/en/getting-started/free-edition-limitations |
| Dependências serverless | https://docs.databricks.com/aws/en/compute/serverless/dependencies |
| Histórico Delta | https://docs.databricks.com/aws/en/tables/history |
| MLflow Tracking | https://mlflow.org/docs/latest/ml/tracking/ |
| Lakeflow Jobs | https://docs.databricks.com/aws/en/jobs/ |
| AI/BI dashboards | https://docs.databricks.com/aws/en/dashboards/ |
| Unity Catalog information_schema | https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-information-schema |
| Importar e exportar notebooks | https://docs.databricks.com/aws/en/notebooks/notebook-export-import |
| Git folders | https://docs.databricks.com/aws/en/repos/ |
| Arquivos em Unity Catalog volumes | https://docs.databricks.com/aws/en/volumes/volume-files |
| Download de arquivos via Drive API | https://developers.google.com/workspace/drive/api/guides/manage-downloads |
| Conector Google Drive no Databricks | https://docs.databricks.com/aws/en/ingestion/lakeflow-connect/google-drive |
| Ingestão incremental de CSV no conector | https://docs.databricks.com/aws/en/ingestion/lakeflow-connect/google-drive-faq |

As URLs Databricks contêm `/aws/` porque essa é a variante da documentação do workspace informado. Isso não cria uma etapa de execução em console AWS. Todo o laboratório permanece no Databricks Free.

A implementação Python Google usa a distribuição `tfp-causalimpact` e o módulo `causalimpact`. Conferir a API e a versão antes de integrar; bibliotecas com nomes semelhantes não são intercambiáveis.
