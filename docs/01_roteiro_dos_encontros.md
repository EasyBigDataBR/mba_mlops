# Roteiro editorial proposto
## CausalImpact no Databricks Free Edition

**Proposta editorial pendente de conferência e aprovação contra as fontes reais do projeto.** São **80 slides**, divididos em **cinco encontros com 14 slides de conteúdo e dois encerramentos institucionais**. Não existem apresentações revisadas nesta etapa. Este roteiro não comprova implementação ou execução no workspace.

Em cada apresentação, as posições **15 e 16** recebem, integralmente e nessa ordem, os **slides 22 e 23 do modelo FGV IDE**. Esses números identificam os slides do modelo original. Novos conteúdos entram antes deles.

A história acompanha a mesma campanha: **dados diários, contrafactual, análise rastreável, atualização manual e painel**. **Em cada encontro, conferimos o corte; ele avança se houver novos dias completos.** Depois de conferidos no projeto real, o período pré, a data da intervenção e os controles permanecem fixos.

### Base confirmada e pontos a conferir

Os seguintes nomes aparecem na captura do workspace:

- `bronze_campanha`
- `bronze_ingestion_control`
- `silver_campanha_daily`
- `feature_bh_counterfact`
- `gold_causal_daily`
- `gold_mlops_status`

O roteiro trata esses nomes como **objetos a inspecionar**. Suas colunas, regras, relacionamentos e conteúdo ainda precisam ser lidos. O objeto `bh_counterfactual_model` também precisa ter **tipo, implementação e uso confirmados**. O nome truncado `gold_campaign_m...` não entra na proposta.

A métrica da campanha, sua unidade, as datas e os controles serão obtidos do projeto real. **Nenhum conjunto de dados, resultado numérico ou nome novo de tabela está pressuposto.** As referências ao MLflow e aos Jobs descrevem o conteúdo proposto, sem afirmar que já estão implementados neste projeto.

A orientação metodológica considera controles não afetados pela intervenção e uma relação plausivelmente estável entre as séries. O projeto CausalImpact de autoria Google fornece a referência do método e da implementação. **O ambiente de execução proposto para a disciplina é o Databricks Free Edition.** A autoria de uma biblioteca não implica o uso de outra plataforma de nuvem.

---

## Encontro 1 — A campanha e os dados

**Objetivo:** entender a pergunta do estudo, localizar os objetos existentes e conferir a base do primeiro corte.

**Entrega:** pergunta definida, desenho inicial conferido, corte registrado e mapa dos objetos baseado na leitura do projeto.

| Slide | Título | Frase curta para o aluno | Visual proposto | URL oficial | Continuidade |
|---|---|---|---|---|---|
| 1 | Uma campanha, cinco encontros | Você vai ligar os dados de cada corte à análise de impacto da campanha. | Jornada com os cinco encontros, sem resultados numéricos. | [MLOps][mlops] | Começar pela pergunta da campanha. |
| 2 | A pergunta da campanha | Vamos comparar o observado com o que teria acontecido sem a ação. | Duas trajetórias conceituais, com a intervenção marcada. | [CausalImpact][causalimpact] | Identificar quais dados podem sustentar a comparação. |
| 3 | Os objetos do workspace | Localize os seis objetos confirmados e confira sua estrutura. | Inventário visual dos seis nomes, sem desenhar dependências ainda desconhecidas. | [Tabelas Delta][delta] | Examinar o significado das linhas e colunas. |
| 4 | Uma linha e sua data | Confira o que cada linha representa, sua data e sua unidade. | Recorte da estrutura real da tabela, após a auditoria. | [SQL][sql] | Verificar se os dados cobrem o período necessário. |
| 5 | Dados completos para o corte | Procure dias ausentes, duplicatas e valores incompatíveis com a métrica. | Calendário diário com exemplos de verificações, sem preencher dados fictícios. | [Tabelas Delta][delta] | Relacionar qualidade de dados e operação. |
| 6 | DevOps: colaboração na entrega | Código e operação precisam acompanhar a mesma mudança. | **Diagrama infinito DevOps preservado**, com elementos editáveis. | [MLOps][mlops] | Observar como essa colaboração se aplica aos dados. |
| 7 | DataOps: dados utilizáveis | Cada atualização precisa chegar com formato, qualidade e origem conhecidos. | **Diagrama infinito DataOps preservado**, com elementos editáveis. | [MLOps][mlops] | Conectar os dados à análise baseada em modelo. |
| 8 | MLOps: análise em operação | O resultado precisa ser repetível, rastreável e acompanhado. | **Diagrama infinito MLOps preservado**, com elementos editáveis. | [MLOps][mlops] | Localizar essas responsabilidades no projeto. |
| 9 | O fluxo que vamos conferir | O código deve explicar como a entrada chega às séries e aos resultados. | Fluxo proposto: entrada, preparação, análise e saída. Relações reais só após leitura do código. | [Notebooks][notebooks] | Definir o corte da execução. |
| 10 | O corte do encontro | Use o último dia completo no fuso America/Sao_Paulo e registre a data. | Relógio e calendário, com campo para o corte efetivamente conferido. | [SQL][sql] | Separar o corte variável do desenho fixo. |
| 11 | O que fica fixo no estudo | Após conferir o desenho, preserve o pré, a intervenção e os controles. | Linha do tempo sem datas inventadas; o pós termina no corte do encontro. | [Guia do método][design] | Conferir a atualização da base. |
| 12 | Leitura da base do corte | Compare o corte atual com o anterior e identifique se há dias completos acrescentados. | Saída real de uma consulta de cobertura, preparada após acesso ao projeto. | [Histórico Delta][history] | Registrar a evidência da atualização ou da manutenção do corte. |
| 13 | Entrega do primeiro encontro | Você leva a pergunta, o corte e o mapa conferido dos objetos. | Quadro simples com os três itens e espaço para os identificadores reais. | [MLOps][mlops] | Preparar a leitura do contrafactual. |
| 14 | Referências e próximo passo | As hipóteses do estudo orientam a leitura do contrafactual. | Três links: método, implementação Python e dados Delta. | [Guia][design], [Python][causalimpact], [Delta][delta] | Encontro 2: estimar e interpretar o efeito. |
| 15 | Contato | Texto original do modelo. | **Slide 22 original do modelo FGV IDE.** | [FGV IDE][fgvide] e [leitura de continuidade][causalimpact] | Seguir para o encerramento institucional. |
| 16 | FGV IDE | Texto original do modelo. | **Slide 23 original do modelo FGV IDE.** | [FGV IDE][fgvide] e [leitura de continuidade][mlops] | Retomar o mesmo estudo no próximo encontro. |

**Notas importantes deste encontro:** o corte deve considerar o dia completo no fuso do estudo. A atualização não deve deslocar automaticamente o início do pré ou a intervenção. A origem dos dados precisa estar explícita depois da inspeção, inclusive se algum objeto contiver dados de demonstração.

---

## Encontro 2 — Contrafactual e efeito

**Objetivo:** entender a comparação causal e interpretar o resultado com suas hipóteses e incertezas.

**Entrega:** análise do corte identificada, acompanhada de trajetórias, efeitos, intervalos e diagnóstico do período pré.

| Slide | Título | Frase curta para o aluno | Visual proposto | URL oficial | Continuidade |
|---|---|---|---|---|---|
| 1 | Contrafactual da campanha | Neste corte, vamos estudar o cenário sem a campanha. | Linha do tempo do mesmo estudo e destaque para o corte atual. | [CausalImpact][causalimpact] | Retomar a base do corte conferido. |
| 2 | Base e corte do encontro | Confira a base e avance o corte apenas se houver novos dias completos. | Comparação de cobertura entre os cortes reais, mantendo o desenho definido. | [Histórico Delta][history] | Separar variação observada e efeito da campanha. |
| 3 | Antes e depois | Uma mudança após a campanha pode incluir sazonalidade e outros acontecimentos. | Série conceitual com tendência comum e intervenção identificada. | [Artigo do método][paper] | Examinar o papel dos controles. |
| 4 | Controles do estudo | Os controles precisam ajudar a explicar a série e ficar fora do efeito da ação. | Série tratada e controles, com indicação de exposição a conferir. | [Guia do método][design] | Entender quais dados entram no ajuste. |
| 5 | Pré e pós no ajuste | Confira que o ajuste usa o resultado do pré e mantém o resultado do pós mascarado. | Matriz temporal destacando resultado e controles em cada período. | [Exemplo oficial][quickstart] | Auditar a implementação usada pelo projeto. |
| 6 | O objeto a auditar | Confirme o tipo, o código e o uso de bh_counterfactual_model. | Ficha do objeto com campos a preencher após inspeção. | [Notebooks][notebooks] | Examinar o ajuste realizado antes da campanha. |
| 7 | Ajuste antes da campanha | Observe se o modelo acompanha a série no período pré. | Gráfico do ajuste real no pré, sem valores até a execução verificada. | [Exemplo oficial][quickstart] | Investigar a capacidade de comparação fora do ajuste. |
| 8 | Validação dentro do pré | Um período reservado e um placebo ajudam a investigar diferenças aparentes. | Linha do tempo com uma divisão de diagnóstico, definida a partir do desenho real. | [Guia do método][design] | Ler observado e contrafactual no pós. |
| 9 | Observado e contrafactual | Compare as trajetórias e a faixa de incerteza após a intervenção. | Gráfico observed_counterfactual, preenchido apenas com saída verificada. | [Exemplo oficial][quickstart] | Examinar a diferença em cada dia. |
| 10 | Efeito por dia | O efeito diário é a diferença entre observado e contrafactual. | Gráfico point_effect, com linha de zero e intervalo. | [Artigo do método][paper] | Ver a soma dessas diferenças. |
| 11 | Efeito acumulado | O acumulado reúne as diferenças ao longo do pós desse corte. | Gráfico cumulative_effect, com intervalo calculado pelo método. | [Exemplo oficial][quickstart] | Interpretar o resultado sem perder a incerteza. |
| 12 | Incerteza e hipóteses | O intervalo e a cauda posterior dependem do modelo e das suposições adotadas. | Estimativa, faixa e quadro curto de hipóteses. | [Artigo do método][paper] | Preparar uma conclusão cuidadosa. |
| 13 | Entrega do segundo encontro | Guarde o corte, as estimativas, os intervalos e os diagnósticos. | Quadro de evidências com referências reais à execução. | [MLflow][tracking] | Ligar o resultado aos dados e ao código. |
| 14 | Referências e próximo passo | Uma análise ganha contexto quando podemos recuperar suas escolhas. | Links para método, exemplo Python e rastreamento. | [Guia][design], [Exemplo][quickstart], [MLflow][tracking] | Encontro 3: rastreabilidade da análise. |
| 15 | Contato | Texto original do modelo. | **Slide 22 original do modelo FGV IDE.** | [FGV IDE][fgvide] e [leitura de continuidade][causalimpact] | Seguir para o encerramento institucional. |
| 16 | FGV IDE | Texto original do modelo. | **Slide 23 original do modelo FGV IDE.** | [FGV IDE][fgvide] e [leitura de continuidade][mlops] | Recuperar esta análise no próximo encontro. |

**Notas importantes deste encontro:** controles do pós podem compor o contrafactual quando continuam válidos. O resultado tratado do pós precisa ficar fora do ajuste. Placebo e ajuste no pré não comprovam as hipóteses causais. A cauda posterior não deve ser apresentada como a probabilidade de a campanha funcionar. O intervalo do acumulado deve vir do cálculo posterior apropriado, sem somar mecanicamente limites diários. Os nomes dos três gráficos são rótulos editoriais, não nomes de colunas ou artefatos confirmados no projeto.

---

## Encontro 3 — Rastreabilidade da análise

**Objetivo:** localizar o resultado e explicar quais dados, escolhas e código o produziram.

**Entrega:** análise recuperável, com seu corte, configuração, referências aos dados e evidências de execução.

| Slide | Título | Frase curta para o aluno | Visual proposto | URL oficial | Continuidade |
|---|---|---|---|---|---|
| 1 | Uma análise rastreável | Você deve conseguir explicar de onde veio cada resultado. | Caminho entre dados, configuração, execução e saída. | [MLflow][tracking] | Retomar o corte deste encontro. |
| 2 | A análise do corte atual | Confira qual análise corresponde à base e se há novos dias completos disponíveis. | Cortes e suas respectivas referências, quando existirem. | [Histórico Delta][history] | Identificar o conjunto usado no cálculo. |
| 3 | Os dados usados | Registre uma referência que permita recuperar o conjunto analisado. | Snapshot ou referência persistida, conforme o mecanismo real do projeto. | [Histórico Delta][history] | Recuperar as escolhas do estudo. |
| 4 | Configuração do estudo | Pré, intervenção, controles, código e ambiente precisam acompanhar a análise. | Ficha de configuração com valores reais após a auditoria. | [MLflow][tracking] | Ver como essas informações aparecem na execução. |
| 5 | Uma run no MLflow | Uma run reúne parâmetros, resultados e artefatos de uma execução. | Visão ilustrativa das três áreas, sem simular uma run existente. | [MLflow][tracking] | Distinguir os tipos de evidência. |
| 6 | Parâmetros, métricas e artefatos | Cada tipo de registro responde a uma pergunta diferente. | Tabela curta: escolhas, resultados e arquivos de apoio. | [MLflow][tracking] | Conferir a identidade dos dados. |
| 7 | Hash e dados preservados | O hash ajuda a conferir o conteúdo, mas a reprodução também precisa dos dados. | Identificador ligado a um conjunto preservado. | [Histórico Delta][history] | Comparar análises com contextos conhecidos. |
| 8 | Versões comparáveis | Mudanças no corte ou na configuração precisam aparecer no contexto do resultado. | Dois registros lado a lado, sem efeitos numéricos inventados. | [MLflow][tracking] | Investigar o comportamento de uma repetição. |
| 9 | Repetição do mesmo corte | Verifique se repetir a execução evita dados e resultados duplicados. | Fluxo com decisão entre reutilizar e produzir uma nova saída. | [Tabelas Delta][delta] | Conferir a origem dos números persistidos. |
| 10 | Origem de um número | Confira se gold_causal_daily liga seus números ao corte e à origem. | Mapa dos campos reais da tabela, construído após a inspeção. | [Tabelas Delta][delta] | Examinar o controle de entrada. |
| 11 | Controle de ingestão | Inspecione bronze_ingestion_control e confirme sua regra de atualização. | Registro real da ingestão e suas chaves, quando disponíveis. | [Tabelas Delta][delta] | Conferir se as evidências podem ser recuperadas. |
| 12 | Evidência recuperável | Abra os dados e artefatos referidos pela análise que você escolheu. | Demonstração guiada com referências reais. | [MLflow][tracking] | Consolidar a entrega do encontro. |
| 13 | Entrega do terceiro encontro | Explique um resultado usando seu corte, seus dados e sua configuração. | Roteiro visual de uma explicação curta. | [MLOps][mlops] | Preparar a repetição operacional. |
| 14 | Referências e próximo passo | O próximo passo é repetir a atualização preservando esse contexto. | Links para rastreamento, histórico e Jobs. | [MLflow][tracking], [Histórico][history], [Jobs][jobs] | Encontro 4: atualização manual. |
| 15 | Contato | Texto original do modelo. | **Slide 22 original do modelo FGV IDE.** | [FGV IDE][fgvide] e [leitura de continuidade][tracking] | Seguir para o encerramento institucional. |
| 16 | FGV IDE | Texto original do modelo. | **Slide 23 original do modelo FGV IDE.** | [FGV IDE][fgvide] e [leitura de continuidade][mlops] | Levar a configuração conferida para a operação. |

**Notas importantes deste encontro:** o roteiro não pressupõe que o projeto já registre tudo no MLflow. A auditoria deve distinguir o que existe do que precisa ser acrescentado. O histórico Delta depende de retenção e não equivale a uma cópia permanente dos dados.

---

## Encontro 4 — Atualização manual

**Objetivo:** conferir e executar uma atualização controlada quando houver novos dias completos, preservando o desenho do estudo.

**Entrega:** uma execução manual identificada, acompanhada de verificações sobre entrada, saída e repetição.

| Slide | Título | Frase curta para o aluno | Visual proposto | URL oficial | Continuidade |
|---|---|---|---|---|---|
| 1 | Atualização manual | Vamos repetir a análise com contexto preservado e novos dias, quando disponíveis. | Fluxo curto da conferência do corte ao resultado. | [Jobs][jobs] | Conferir a base que será usada. |
| 2 | O corte desta execução | Confira a data de corte e a cobertura da base antes de executar. | Calendário e resultado real da consulta de cobertura. | [SQL][sql] | Localizar o notebook responsável pela operação. |
| 3 | A tarefa do notebook | Identifique o notebook auditado que prepara os dados e atualiza a análise. | Entrada, processamento e saída, com nomes preenchidos após a leitura do código. | [Notebooks][notebooks] | Separar novos dados de mudanças no desenho. |
| 4 | Novos dias, mesmo desenho | O pós cresce enquanto o pré, a intervenção e os controles permanecem fixos. | Linha do tempo com extensão apenas do período posterior. | [Guia do método][design] | Conferir os efeitos de uma repetição. |
| 5 | Atualização sem duplicatas | As chaves e as regras de escrita precisam permitir uma repetição segura. | Chaves de escrita e decisão de atualização, conforme a implementação real. | [Tabelas Delta][delta] | Definir a execução manual. |
| 6 | Configuração do Job | Comece com execução manual e uma execução por vez. | Formulário conceitual de Job, sem nome ou ID inventado. | [Configuração de Jobs][jobs] | Conferir o ambiente da tarefa. |
| 7 | Ambiente Python da tarefa | Confira as versões e dependências usadas pelo notebook e pelo Job. | Ficha real de Python, TensorFlow, TensorFlow Probability e tf-keras. | [Ambiente serverless][environment], [Compatibilidade TFP][tfp] | Preparar a primeira execução. |
| 8 | Primeira execução manual | Use Run now depois de conferir o notebook, os parâmetros e o destino. | Sequência curta de telas reais, capturadas após acesso autorizado. | [Jobs serverless][jobserverless] | Acompanhar a saída da tarefa. |
| 9 | Status e qualidade da saída | Uma run concluída também precisa entregar dados completos e coerentes. | Status da tarefa ao lado das verificações de saída. | [Monitoramento de Jobs][jobruns] | Distinguir causas de falha. |
| 10 | Falha de dados ou de serviço | Uma entrada inválida pede correção; uma interrupção pode permitir nova tentativa. | Árvore de decisão com os dois caminhos. | [Monitoramento de Jobs][jobruns] | Conferir o registro das tentativas. |
| 11 | O estado registrado | Inspecione gold_mlops_status e confirme o significado de cada estado. | Campos reais da tabela e relação com a execução, após auditoria. | [Tabelas Delta][delta] | Comparar duas execuções do mesmo corte. |
| 12 | Segunda execução do corte | Compare volumes, chaves e resultados para verificar o comportamento da repetição. | Comparação antes e depois, com evidências reais. | [Jobs][jobs], [Delta][delta] | Consolidar os identificadores da operação. |
| 13 | Entrega do quarto encontro | Guarde o corte, a referência da execução e as verificações da saída. | Quadro curto com os identificadores efetivamente disponíveis. | [Monitoramento de Jobs][jobruns] | Usar essas referências no painel. |
| 14 | Referências e próximo passo | O painel deve mostrar o resultado junto com o contexto da execução. | Links para Jobs, acompanhamento e painéis. | [Jobs][jobs], [Execuções][jobruns], [Painéis][dashboards] | Encontro 5: painel e diagnóstico. |
| 15 | Contato | Texto original do modelo. | **Slide 22 original do modelo FGV IDE.** | [FGV IDE][fgvide] e [leitura de continuidade][jobs] | Seguir para o encerramento institucional. |
| 16 | FGV IDE | Texto original do modelo. | **Slide 23 original do modelo FGV IDE.** | [FGV IDE][fgvide] e [leitura de continuidade][mlops] | Retomar a execução conferida no encontro final. |

**Notas importantes deste encontro:** o nome do Job, o notebook e seus parâmetros vêm do projeto auditado. O tempo limite só deve ser definido após medir uma execução representativa. O conjunto TensorFlow 2.18, TensorFlow Probability 0.25 e tf-keras merece avaliação de compatibilidade, mas não constitui ambiente testado deste projeto. A versão 0.25 do TFP documenta o pareamento com TensorFlow 2.18 e o uso de Keras 2 por tf-keras. Consulte a fonte oficial de compatibilidade antes de escolher versões.

---

## Encontro 5 — Painel e diagnóstico

**Objetivo:** acompanhar a campanha por corte, interpretar mudanças e responder a problemas sem perder o contexto causal.

**Entrega:** leitura do painel sustentada por dados, execução e hipóteses do estudo.

| Slide | Título | Frase curta para o aluno | Visual proposto | URL oficial | Continuidade |
|---|---|---|---|---|---|
| 1 | Painel da campanha | O painel reúne resultado, atualização e qualidade da análise. | Esboço de painel com espaço para dados reais. | [Painéis][dashboards] | Conferir o corte mostrado. |
| 2 | O corte que o painel mostra | Confira até que dia os dados e a análise estão completos. | Data de corte ligada à execução e às tabelas de origem. | [SQL][sql] | Organizar as perguntas do painel. |
| 3 | Três leituras do painel | Observe atualização dos dados, efeito estimado e qualidade da execução. | Três áreas de leitura com uma pergunta em cada uma. | [Painéis][dashboards] | Localizar a fonte de cada indicador. |
| 4 | A fonte de cada indicador | Confirme quais campos de gold_causal_daily e gold_mlops_status sustentam a leitura. | Mapa entre campos reais e indicadores. | [SQL][sql] | Ler as trajetórias da campanha. |
| 5 | Observado e contrafactual | Veja quando as trajetórias se aproximam ou se afastam. | Gráfico real com intervenção, corte e intervalo identificados. | [Exemplo oficial][quickstart] | Examinar a diferença diária. |
| 6 | Efeito diário e incerteza | Leia cada diferença junto com sua faixa e com o contexto do dia. | Gráfico real do efeito diário, com zero marcado. | [Exemplo oficial][quickstart] | Examinar o resultado do período completo. |
| 7 | Efeito acumulado do corte | O horizonte analisado faz parte do significado do acumulado. | Gráfico real do efeito acumulado e seu intervalo. | [Artigo do método][paper] | Comparar cortes sem misturar horizontes. |
| 8 | Comparação entre cortes | Compare também o período comum quando os cortes têm durações diferentes. | Dois cortes sobrepostos, com a janela compartilhada destacada. | [Guia do método][design] | Investigar mudanças nos controles. |
| 9 | Controles que mudaram | Procure exposição à campanha e alterações na relação entre as séries. | Série de controle com eventos reais anotados após investigação. | [Guia do método][design] | Separar problemas do desenho e da entrada. |
| 10 | Dados atrasados ou corrigidos | Uma revisão da entrada precisa aparecer no contexto da análise. | Fluxo entre correção, dados identificados e novo resultado. | [Histórico Delta][history] | Definir uma resposta a incidentes. |
| 11 | Resposta a um incidente | Preserve a evidência, investigue a causa e confira a nova saída. | Fluxo de contenção, investigação, correção e conferência. | [Monitoramento de Jobs][jobruns] | Comunicar o efeito com seus limites. |
| 12 | A conclusão do estudo | Explique o efeito, a incerteza e as hipóteses que sustentam sua leitura. | Quadro curto de conclusão com referências ao corte e ao desenho. | [Artigo do método][paper] | Preparar a entrega final. |
| 13 | Entrega do quinto encontro | Apresente uma análise completa, dos dados à interpretação do painel. | Caminho final com links reais para dados, execução e resultado. | [MLOps][mlops], [MLflow][tracking] | Definir a próxima conferência do mesmo estudo. |
| 14 | Referências e continuidade | O próximo encontro confere o corte e avança apenas com novos dias completos. | Links para método, rastreamento e painéis. | [Guia][design], [MLflow][tracking], [Painéis][dashboards] | Continuar o acompanhamento com novas evidências e desenho preservado. |
| 15 | Contato | Texto original do modelo. | **Slide 22 original do modelo FGV IDE.** | [FGV IDE][fgvide] e [leitura de continuidade][causalimpact] | Seguir para o encerramento institucional. |
| 16 | FGV IDE | Texto original do modelo. | **Slide 23 original do modelo FGV IDE.** | [FGV IDE][fgvide] e [leitura de continuidade][mlops] | Preservar as evidências e revisar o estudo quando necessário. |

**Notas importantes deste encontro:** uma tabela vazia significa ausência de evidência disponível, não efeito zero. Um resultado de um corte anterior deve continuar identificado como anterior. Efeito positivo, intervalo estreito ou uma medida posterior favorável não substituem a análise das hipóteses e do contexto comercial.

---

## Orientação para as notas e para a montagem

Cada slide deverá receber nas notas:

1. Uma explicação curta do conceito ou da atividade.
2. A URL oficial indicada na respectiva linha.
3. A continuidade indicada no roteiro.
4. Quando houver resultado, a referência real ao corte, aos dados e à execução que o produziram.

Nos slides com gráficos, os valores serão extraídos de uma execução conferida. Enquanto isso, o roteiro especifica o gráfico e sua finalidade, sem simular um resultado.

**Nos dez encerramentos institucionais, acrescentar às notas a URL https://educacao-executiva.fgv.br/, a leitura de continuidade e a frase de continuidade da respectiva linha. Isso não altera o conteúdo visual dos slides 22 e 23 originais.** As leituras técnicas das notas não são fontes da fotografia, dos contatos ou do texto institucional.

Este documento é conteúdo editorial proposto. A montagem e a validação das apresentações permanecem pendentes da leitura das fontes reais, da conferência do projeto e da aprovação dos vínculos entre o roteiro e a implementação.

### Fontes oficiais usadas no roteiro

- [CausalImpact em Python][causalimpact]
- [Guia metodológico do CausalImpact][design]
- [Exemplo oficial em Python][quickstart]
- [Artigo original sobre o método][paper]
- [Compatibilidade do TensorFlow Probability 0.25][tfp]
- [MLOps no Databricks][mlops]
- [Notebooks][notebooks]
- [Tabelas Delta][delta]
- [Histórico de tabelas][history]
- [MLflow Tracking][tracking]
- [Configuração de Jobs][jobs]
- [Jobs serverless][jobserverless]
- [Monitoramento de Jobs][jobruns]
- [Ambiente serverless e dependências][environment]
- [Painéis][dashboards]
- [Referência SQL][sql]
- [Limitações da Free Edition][free]
- [FGV Educação Executiva][fgvide]

[causalimpact]: https://github.com/google/tfp-causalimpact
[design]: https://google.github.io/CausalImpact/CausalImpact.html
[quickstart]: https://github.com/google/tfp-causalimpact/blob/main/docs/quickstart.ipynb
[paper]: https://research.google/pubs/inferring-causal-impact-using-bayesian-structural-time-series-models/
[tfp]: https://github.com/tensorflow/probability/releases/tag/v0.25.0
[mlops]: https://docs.databricks.com/aws/en/machine-learning/mlops/mlops-workflow
[notebooks]: https://docs.databricks.com/aws/en/notebooks/
[delta]: https://docs.databricks.com/aws/en/delta/
[history]: https://docs.databricks.com/aws/en/tables/history
[tracking]: https://mlflow.org/docs/latest/ml/tracking/
[jobs]: https://docs.databricks.com/aws/en/jobs/configure-job
[jobserverless]: https://docs.databricks.com/aws/en/jobs/run-serverless-jobs
[jobruns]: https://docs.databricks.com/aws/en/jobs/monitor
[environment]: https://docs.databricks.com/aws/en/compute/serverless/dependencies
[dashboards]: https://docs.databricks.com/aws/en/dashboards/tutorials/create-dashboard
[sql]: https://docs.databricks.com/aws/en/sql/language-manual/
[free]: https://docs.databricks.com/aws/en/getting-started/free-edition-limitations
[fgvide]: https://educacao-executiva.fgv.br/
