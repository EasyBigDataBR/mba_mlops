# Dez entregas sintéticas de campanha

Os CSVs desta pasta são a distribuição do demonstrador. O Job lê a pasta configurada no **Drive**, não os arquivos que estão no Git.

Na pasta do Drive, mantenha duas pastas irmãs:

| Pasta | Começa com | O que fazer |
| --- | --- | --- |
| `01_Entrada_Databricks` | **01–05 juntos**. | Use a URL privada desta pasta em `source_path`. |
| `02_Reserva_Proximas_Execucoes` | **06–10**. | Mova somente o próximo CSV para a entrada, um por demonstração. |

Depois de mover **06**, clique em **Run now** no Job. Repita com **07, 08, 09 e 10**. Não é preciso editar a orquestração a cada arquivo. Mantenha os anteriores na entrada, inclusive o `07` quando chegar sua correção `08`.

O leitor do Drive percorre subpastas: a reserva deve ficar **ao lado da entrada**, nunca dentro dela. O Job não deve apontar para a pasta que contém as duas. [Documentação oficial](https://docs.databricks.com/aws/en/ingestion/google-drive)

Não renomeie, abra e salve ou converta os CSVs: os hashes validam os bytes originais. O notebook `00` testa a leitura antes do modelo. No modo Drive, não é necessário replicar em Volume: os bytes recebidos são preservados em `ci_demo_bronze`. A alternativa por Volume está no [guia de integração](../docs/INTEGRACAO_DATABRICKS.md).

O limite `max_files_per_run=10` conta o total de CSVs na entrada. Cada execução relê e recalcula os hashes desse conjunto pequeno; os controles impedem duplicação. Não altere o limite para `1` ao acrescentar um arquivo.

Os arquivos têm cabeçalho `date,treated,control_a,control_b`, UTF-8, separador vírgula e contagens inteiras de conversões diárias. `treated` é a série atingida pela campanha; os dois controles não são atingidos no cenário sintético. A chave é `date`.

| Entrega | Período | Linhas | Papel |
| --- | --- | ---: | --- |
| 01 | 29/07–18/08/2026 | 21 | Pré, parte 1. |
| 02 | 19/08–08/09/2026 | 21 | Pré, parte 2. |
| 03 | 09/09–29/09/2026 | 21 | Pré, parte 3. |
| 04 | 30/09–20/10/2026 | 21 | Pré, parte 4. |
| 05 | 21/10–03/11/2026 | 14 | Pós inicial. |
| 06 | 04/11–10/11/2026 | 7 | Mais dias de pós. |
| 07 | 11/11–17/11/2026 | 7 | Erro deliberado: controle ausente em 14/11. |
| 08 | 11/11–17/11/2026 | 7 | Substitui o 07 com dados válidos. |
| 09 | 18/11–24/11/2026 | 7 | Semana de efeito atenuado. |
| 10 | 26/10/2026 | 1 | Corrige uma contagem antiga; não duplica a data. |

O [manifesto](manifest.json) define hashes, contrato, correções e sequência. A seção `instructor_truth` serve para conferir o gerador; nunca entra nas features do modelo. O pacote é uma amostra fechada para demonstração: um arquivo real fora desse contrato exige revisão explícita do estudo e do manifesto.

O gerador em `src/generate_demo_data.py` preserva a âncora e a seed de um manifesto existente. Para um cenário futuro com novas datas, gere em outra pasta vazia com um novo `--as-of`, mantenha o manifesto correspondente e use outro `demo_id` no Databricks. Não substitua o passado no meio da demonstração.
