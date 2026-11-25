# Dez entregas sintéticas de campanha

Envie **01–05 juntos** à pasta de entrada. Depois, acrescente **06, 07, 08, 09 e 10**, um por execução. Mantenha os anteriores na pasta. Não renomeie, abra e salve ou converta os CSVs: os hashes validam os bytes originais.

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
