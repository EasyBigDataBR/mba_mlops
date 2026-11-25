# CausalImpact no Databricks · demonstração de MLOps

**Notebooks executáveis, dez arquivos de campanha e um Job manual.** Todo o processamento acontece no Databricks Free. O GitHub guarda o código; a pasta do Drive ou um Volume recebe os CSVs; Delta e MLflow guardam dados, análises e evidências.

O modelo é a implementação Python do projeto Google: [`tfp-causalimpact==0.2.0`](https://github.com/google/tfp-causalimpact), API `causalimpact.fit_causalimpact`. Os dados são **sintéticos**, com um grupo tratado e dois controles. Este repositório é o projeto demonstrativo. As apresentações conceituais do curso ficam nos materiais PPTX/PDF.

## Comece por aqui

1. Crie um **Git folder** no Databricks com `https://github.com/EasyBigDataBR/mba_mlops.git` e selecione **main**.
2. Abra [00_Configurar](notebooks/00_Configurar.py), execute a célula de configuração e confira os widgets. O destino é `mba.mlops_causalimpact`; as novas tabelas começam com `ci_demo_`.
3. Escolha a fonte. **Volume:** use `/Volumes/mba/mlops_causalimpact/landing/causalimpact_demo`. **Drive:** informe a URL privada da pasta e uma conexão Unity Catalog autorizada, conforme o [guia de integração](docs/INTEGRACAO_DATABRICKS.md). A disponibilidade da conexão depende do workspace; não é necessário tornar a pasta pública.
4. Coloque **somente os cinco primeiros CSVs** de [data_demo](data_demo/) na pasta de entrada. Preserve nomes e bytes. Não converta em planilhas nem use “Salvar como CSV” no Excel.
5. Execute [01_Ingerir_Atualizacoes](notebooks/01_Ingerir_Atualizacoes.py), [02_Executar_CausalImpact](notebooks/02_Executar_CausalImpact.py) e [03_Painel_e_Validacao](notebooks/03_Painel_e_Validacao.py). Confira os mesmos parâmetros nos notebooks. Antes do Run All em `02`/`04`, selecione **Standard versão 4 (Python 3.12)** no Environment; eles instalam as dependências na própria sessão. O template do Job já fixa essa base.
6. Abra [05_Criar_Job](notebooks/05_Criar_Job.py), confira os parâmetros da fonte e execute. Ele cria o Job manual que chama [04_Orquestrar](notebooks/04_Orquestrar.py). Não inicia uma run.
7. Acrescente o arquivo **06** e clique em **Run now**. Continue com **07, 08, 09 e 10**, sempre um arquivo novo por execução. O erro no ciclo do `07` é esperado; ele faz parte da demonstração.

Os `.py` em `notebooks/` têm o cabeçalho e os separadores nativos do Databricks: abrem como notebooks dentro do Git folder. Não importe apenas um arquivo isolado, pois eles usam os módulos em `src/`.

## A sequência dos arquivos

| Ciclo | Novos arquivos | Dias aceitos | Corte aceito | Demonstração |
| --- | --- | ---: | --- | --- |
| 1 | 01–05 juntos | 98 | 03/11/2026 | Carga inicial, contrafactual e primeira evidência MLflow. |
| 2 | 06 | 105 | 10/11/2026 | Novos dados e análise atualizada. |
| 3 | 07 | **105 preservados** | **10/11/2026 preservado** | Controle ausente: ciclo bloqueado, resultado anterior preservado. |
| 4 | 08 | 112 | 17/11/2026 | Correção do arquivo rejeitado e recuperação do fluxo. |
| 5 | 09 | 119 | 24/11/2026 | Efeito sintético mais fraco na última semana. |
| 6 | 10 | 119 | 24/11/2026 | Correção de um dia antigo, novo hash, sem duplicar a data. |

As datas foram ancoradas no último dia completo de **24/11/2026**, em `America/Sao_Paulo`. O pré é fixo: **29/07 a 20/10/2026**; a intervenção começa em **21/10/2026**. `as_of` vazio acompanha o último dia completo disponível nos arquivos, e não o relógio da aula. As entregas são congeladas para que cada execução seja comparável.

Mantenha os arquivos anteriores na fonte. O `max_files_per_run=10` limita o **total de CSVs presentes**; não o diminua para 1 quando for acrescentar só um arquivo. Repetir os mesmos dados, código, configuração e dependências reutiliza a análise já publicada.

## Notebooks e apoio

| Arquivo | Finalidade |
| --- | --- |
| [00_Configurar.py](notebooks/00_Configurar.py) | Preparar os objetos exclusivos do exemplo e conferir parâmetros. |
| [01_Ingerir_Atualizacoes.py](notebooks/01_Ingerir_Atualizacoes.py) | Ler arquivos, validar contrato, registrar rejeições e aceitar snapshot. |
| [02_Executar_CausalImpact.py](notebooks/02_Executar_CausalImpact.py) | Executar o modelo Google e registrar parâmetros, métricas e artefatos. |
| [03_Painel_e_Validacao.py](notebooks/03_Painel_e_Validacao.py) | Consultar resultados, gráficos, histórico e integridade. |
| [04_Orquestrar.py](notebooks/04_Orquestrar.py) | Executar o ciclo completo na mesma tarefa. |
| [05_Criar_Job.py](notebooks/05_Criar_Job.py) | Criar/atualizar somente o Job identificado deste demonstrador. |
| [jobs/job_template.json](jobs/job_template.json) | Definição de uma tarefa, Git `main`, Serverless Standard e execução manual. |
| [sql/painel.sql](sql/painel.sql) | Consultas para explorar o histórico ou montar um dashboard. |
| [docs/DEMONSTRACAO.md](docs/DEMONSTRACAO.md) | Roteiro de cada entrega, interpretação e recuperação. |
| [docs/INTEGRACAO_DATABRICKS.md](docs/INTEGRACAO_DATABRICKS.md) | Git, dependências, Volume/Drive, permissões e Job. |

O Job chama módulos Python na mesma sessão. Não há agenda, endpoint de serving ou cluster clássico. Os limites da conta Free continuam valendo.

## O que fica salvo

Tudo usa o prefixo **`ci_demo_`** dentro de `mba.mlops_causalimpact`. As tabelas e o modelo existentes do seu outro projeto não são reutilizados nem substituídos.

| Tabela | Evidência |
| --- | --- |
| `ci_demo_bronze` | Arquivo original recebido, hash e horário. |
| `ci_demo_ingestion_control` | Aceitação, rejeição e substituição por correção, preservando os erros. |
| `ci_demo_silver` | Linhas de cada snapshot aceito, com origem e revisão. |
| `ci_demo_snapshots` | Marcador de commit do snapshot, corte e hashes dos arquivos. |
| `ci_demo_effects` | Contrafactual, efeito diário, acumulado e intervalos por análise. |
| `ci_demo_analysis` | Marcador de análise completa, configuração, métricas, versões e run MLflow. |
| `ci_demo_executions` | Tentativas, etapas, status e mensagens. |

Não há limpeza automática. As escritas são isoladas pelo `demo_id`. Execute um ciclo por vez; não rode o notebook manualmente ao mesmo tempo que o Job. Para repetir a história do zero, use outro `demo_id` e outra pasta de entrada vazia, mantendo o histórico anterior.

## O que foi realmente testado

O motor Google executou **localmente em CPU** nos cinco estados válidos. O contrato bloqueou a entrega 07 antes do ajuste. A correção 10 manteve os 119 dias e aumentou o efeito acumulado em exatamente 12 conversões, com o mesmo contrafactual.

| Estado | Efeito médio estimado/dia | Intervalo de 95% | Efeito acumulado |
| --- | ---: | --- | ---: |
| 01–05 | 33,55 | [28,75; 38,61] | 469,68 |
| +06 | 34,26 | [29,82; 38,80] | 719,40 |
| +08 | 34,77 | [31,08; 38,89] | 973,52 |
| +09 | 29,16 | [25,11; 33,06] | 1.020,58 |
| +10 | 29,50 | [25,45; 33,40] | 1.032,58 |

Fonte: [resultados locais reproduzíveis](validation/local_results.json). São dados sintéticos, não resultados de uma campanha real. O [relatório do motor](validation/README_MODELO.md) inclui placebo, versões e comandos.

**Ainda não validado nesta entrega:** instalação na sua sessão serverless, conexão privada do Drive, escritas Delta, execução do Job e registro MLflow no seu workspace. O projeto está preparado para você integrar e executar; os resultados locais não são apresentados como uma run cloud.

### Reproduzir a parte científica fora do Databricks

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -p 'test_*.py'
python scripts/run_model_sequence.py
```

Essa execução local não emula Spark, Delta, Unity Catalog ou Jobs.

## Interprete com o contexto do estudo

O estudo depende de controles não afetados pela intervenção e de uma relação estável. A resposta pós-intervenção é mascarada na verossimilhança do ajuste; os controles pós participam do contrafactual e do prior de regressão padrão do pacote. O intervalo acumulado vem das trajetórias posteriores do Google: não é a soma dos limites dos intervalos diários.

O conjunto de 300 amostras e 100 warmup é uma configuração demonstrativa. Não representa diagnóstico completo de convergência. Um efeito diferente de zero não aprova automaticamente a validade causal nem uma decisão comercial. O placebo ajuda a examinar o pré, mas não prova ausência de confundimento.

## Documentação oficial

- [Google TFP CausalImpact: código, instalação e hipóteses](https://github.com/google/tfp-causalimpact)
- [Databricks: Git folders](https://docs.databricks.com/aws/en/repos/git-operations-with-repos)
- [Databricks: notebooks em formato fonte](https://docs.databricks.com/aws/en/notebooks/notebook-export-import)
- [Databricks: Git em Jobs](https://docs.databricks.com/aws/en/jobs/git)
- [Databricks: dependências serverless](https://docs.databricks.com/aws/en/compute/serverless/dependencies)
- [Databricks: arquivos em volumes](https://docs.databricks.com/aws/en/volumes/volume-files)
- [Databricks: leitura do Drive](https://docs.databricks.com/aws/en/ingestion/google-drive)
- [Databricks: MLflow Tracking](https://docs.databricks.com/aws/en/mlflow/tracking)
- [Databricks Free: limites](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations)

Os links Databricks contêm `/aws/` porque essa é a documentação do workspace hospedado nessa nuvem. O demonstrador não exige criar nem executar recursos na console AWS.
