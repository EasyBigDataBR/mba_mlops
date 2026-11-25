# MBA — MLOps com CausalImpact no Databricks Free

Uma história em cinco encontros: **entender quanto uma campanha alterou o resultado, atualizar a análise com novos dados e conseguir explicar de onde cada resultado veio**.

Toda a execução didática acontece no **Databricks Free Edition**, no projeto existente `mba.mlops_causalimpact`. O GitHub guarda código e documentação. A referência ao Google identifica a origem do CausalImpact.

## Estado desta revisão — 25/11/2026

Esta branch contém a preparação editorial e o inventário para integrar o projeto existente. O repositório estava vazio quando a revisão começou.

| Entrega | Estado |
|---|---|
| Roteiro dos cinco encontros | Proposta editorial neste repositório |
| Política de atualização por encontro | Especificada; depende do contrato real dos dados |
| Notebook de inventário | Preparado para leitura de metadados; ainda não executado no workspace |
| Código original do workspace | Aguardando importação |
| Implementação de `bh_counterfactual_model` | Ainda não inspecionada |
| Alterações e execução no Databricks | Não realizadas nesta revisão |
| Cinco PPTX/PDF FGV IDE e apresentações online | Ainda não revisados para este case |
| Resultados numéricos do novo case | Não produzidos nem validados nesta revisão |

## A história dos encontros

| Encontro | Sua pergunta | O que você faz no mesmo projeto | O que leva para o próximo encontro |
|---|---|---|---|
| 1 — Entender e organizar | O que queremos medir? | Conhece a campanha, a série diária e o fluxo de dados | Pergunta, métrica, intervenção e contrato dos dados |
| 2 — Construir o contrafactual | O que teria acontecido sem a campanha? | Examina o pré, os controles e a primeira análise CausalImpact | Análise com corte identificado e incerteza |
| 3 — Rastrear e comparar | Consigo explicar e reproduzir este resultado? | Atualiza o corte e relaciona dados, código, ambiente e análise | Histórico comparável de análises |
| 4 — Operar com segurança | Consigo repetir o processo sem improvisar? | Atualiza a base e executa o fluxo por um Job manual | Execução observável e procedimento de recuperação |
| 5 — Monitorar e decidir | O que mudou e o que a evidência permite concluir? | Atualiza a análise e lê o painel de qualidade, efeito e incerteza | Conclusão com limites e próxima ação |

As datas dos encontros não foram informadas. Elas não são preenchidas com datas de outros cursos.

## Onde começar

- [Roteiro editorial dos cinco encontros](docs/01_roteiro_dos_encontros.md).
- [Atualização da base e das análises](docs/02_atualizacao_por_encontro.md).
- [Integração com o workspace existente](docs/03_integracao_workspace.md).
- [Notebook de inventário de metadados](notebooks/00_Inventario_CausalImpact.py).
- [Contexto conhecido do projeto](config/projeto.json).
- [Referências oficiais](docs/04_referencias_oficiais.md).

O inventário lê metadados; não é o notebook de treino nem substitui a exportação dos notebooks originais.

## Critérios para a revisão dos slides

Os cinco decks devem seguir o padrão FGV IDE, com linguagem curta e dirigida ao aluno. O primeiro encontro mantém as representações em infinito de DevOps, DataOps e MLOps. Cada slide recebe URLs oficiais e uma transição para o próximo nas notas. Os slides 22 e 23 do modelo FGV fornecido encerram cada deck.

Gráficos de resultados só entram após uma execução identificada. O texto deve distinguir dado real, dado sintético e ilustração conceitual.
