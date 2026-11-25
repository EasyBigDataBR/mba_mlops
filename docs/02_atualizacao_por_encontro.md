# A mesma campanha, com a evidência atualizada

Em cada encontro, vamos perguntar: **o que aprendemos com os dias novos que chegaram?**

Este documento define o comportamento desejado. A implementação será ajustada ao código e às colunas existentes, depois de sua inspeção.

## O que fica fixo e o que muda

| Elemento | Regra |
|---|---|
| Pergunta e métrica | Mantêm a mesma definição |
| Grupo tratado e controles | Mantêm a definição aprovada antes da leitura do efeito |
| Data da intervenção | Continua sendo a data real da campanha |
| Período anterior à campanha | Mantém o início e o fim definidos no desenho |
| Data de corte do período posterior | Avança conforme chegam dias completos |
| Dados utilizados | Ganham uma identificação de snapshot |
| Análise | Ganha identificação própria, ligada aos dados e ao código |
| Resultado anterior | Continua disponível para comparação |

Não deslocamos a campanha no calendário para que ela pareça recente. Se a base for histórica, usamos cortes históricos explícitos. Se for sintética, identificamos a simulação e garantimos que acrescentar dias não altere silenciosamente o passado.

## Como o arquivo chega à análise

Os resultados observados das campanhas serão recebidos na pasta do Drive definida para o curso. Para a primeira versão do curso, o arquivo é baixado e enviado ao volume `mba.mlops_causalimpact.landing`. O notebook existente será ajustado para validar e processar o lote, depois da inspeção de seu código.

Um arquivo de atualização contém observações da campanha e dos controles necessários. Contrafactuais e efeitos calculados pelo modelo são saídas da análise; não devem voltar como observações de entrada.

O detalhe de nome, revisão, checksum e completude está no [contrato dos arquivos](05_arquivos_drive.md).

## Como escolher o corte

1. Calcule o último dia completo no fuso `America/Sao_Paulo`.
2. Leia no controle de ingestão quais dias e séries foram carregados por completo.
3. Compare o corte solicitado com o último dia completo dos dados.
4. Se houver atraso ou lacuna, registre a situação e interrompa a análise daquele corte.
5. Para uma retomada histórica, informe explicitamente um corte disponível e registre esse corte na análise.

O maior valor da coluna de data não prova completude. Precisamos conferir também frequência, chaves, séries esperadas e registros faltantes.

A interface pode exibir separadamente `corte_solicitado` e `corte_utilizado`. Os nomes efetivos dessas colunas serão mapeados aos objetos do projeto.

## O que acontece em cada encontro

| Encontro | Atualização e execução | Evidência esperada |
|---|---|---|
| 1 | Examinar a ingestão e o corte disponível; validar o desenho | Contrato de dados e calendário da campanha |
| 2 | Ingerir os dias disponíveis, validar e produzir a primeira análise | Observado, contrafactual, efeito e intervalos |
| 3 | Repetir o fluxo com novo corte e registrar a rastreabilidade | Relação entre corte, snapshot, código e análise |
| 4 | Executar manualmente o fluxo validado pelo Job | Identificação da execução, verificações e estado final |
| 5 | Atualizar novamente e consultar o painel | Qualidade, efeito acumulado, incerteza e decisão |

Se dois encontros usarem exatamente o mesmo corte e os mesmos dados, o curso explica a reutilização ou a repetição identificada. Não é necessário inventar dias novos.

## O que precisa acompanhar cada análise

- Identificação da campanha e da versão do desenho.
- Datas do pré, intervenção e corte posterior.
- Identificação dos dados, versões Delta ou snapshot persistido.
- Métrica, controles, frequência, fuso e verificações de qualidade.
- Commit do código, distribuição e versão do CausalImpact, dependências e parâmetros.
- Run MLflow ou referência equivalente já usada no projeto.
- Resultado e intervalos produzidos pelo próprio método.
- Estado da revisão e motivo de eventual bloqueio.

Uma correção tardia nos dados gera uma nova versão identificada. A execução deve permitir comparar a revisão com a versão anterior.

## Como ler o resultado

O contrafactual é a estimativa do que ocorreria sem a campanha. A diferença entre o observado e essa estimativa é o efeito estimado, condicionado ao modelo e à validade dos controles.

A análise exige controles que não tenham sido afetados pela campanha e uma relação suficientemente estável entre eles e a série tratada. Essas hipóteses precisam de avaliação do contexto; testes de dados não as provam.

O intervalo acumulado deve vir das trajetórias posteriores calculadas pelo modelo. Não some os limites inferiores e superiores de intervalos diários.

Uma análise inconclusiva pode ser tecnicamente válida. O processo não deve liberar apenas resultados positivos ou estatisticamente favoráveis. Para comparar encontros, informe o horizonte de cada corte: um efeito acumulado pode crescer simplesmente porque cobre mais dias.

## Fontes oficiais

- https://github.com/google/tfp-causalimpact
- https://google.github.io/CausalImpact/CausalImpact.html
- https://github.com/google/tfp-causalimpact/blob/main/docs/quickstart.ipynb
- https://docs.databricks.com/aws/en/tables/history
- https://mlflow.org/docs/latest/ml/tracking/
