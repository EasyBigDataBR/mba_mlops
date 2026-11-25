# Validação científica local

Este diretório contém resultados **executados localmente, em CPU**, com os CSVs
sintéticos do repositório e o pacote real `tfp-causalimpact==0.2.0`, do projeto
[google/tfp-causalimpact](https://github.com/google/tfp-causalimpact).
Não são saídas de Spark, de Jobs ou de uma conta Databricks.

## Reproduzir

Use Python 3.12 e as dependências científicas fixadas pelo projeto. Na raiz do
repositório, execute:

```bash
python -m unittest discover -s tests -p test_causal_model.py -v
python tests/run_causal_validation.py --case initial
python tests/run_causal_validation.py --case final
python scripts/run_model_sequence.py
```

O primeiro comando cobre 15 testes de contrato: calendário completo, datas
únicas, contagens válidas, metadados fora das features, imutabilidade da entrada,
pré de 84 dias, rejeição do arquivo 07 e correção tardia sem alterar o pré.

O segundo executa o ajuste inicial, um placebo dentro do pré e uma perturbação
controlada da resposta pós. Ao acrescentar 17 conversões em cada um dos 14 dias
pós, o contrafactual permaneceu idêntico e o efeito acumulado aumentou 238.
Isso verifica o mascaramento de `treated` pós na execução real; não demonstra
que os controles sejam causalmente adequados em uma campanha real.

O terceiro confere o corte final. O quarto integra o **mesmo core de ingestão
usado pelo runtime**, `src.data_pipeline.plan_snapshot`, ao motor científico.
Acumula os bytes das entregas, chama o core em cada um dos seis ciclos e só
ajusta quando o resultado efetivo é `READY`. Não resolve revisões por um
`drop_duplicates` paralelo nem usa `publish_new_analysis` do manifest para
decidir o gate.

Esse caminho produz os cinco estados válidos: 98, 105, 112, 119 e 119 linhas.
No ciclo do CSV 07, o core retorna `BLOCKED`, preserva o snapshot de 105 linhas
e o motor não é chamado. Quando chega o CSV 08, o core registra a supersessão
do 07, mantendo seu erro original no histórico. A correção do CSV 10 substitui
a observação anterior: acrescenta 12 ao efeito acumulado, conserva o número
de dias e o contrafactual.

Os scripts substituem apenas seus arquivos de evidência em `validation/`.
Não escrevem no Databricks nem no MLflow. O core verifica os bytes contra os
hashes do `manifest.json`. A sequência também compara o hash canônico de cada
snapshot com o resultado do core e com a referência do manifest, inclusive
no ciclo bloqueado. `instructor_truth` não é fornecido ao modelo.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `local_results.json` | Cinco estados válidos, seis estados do core, hashes canônicos e bloqueio local do lote inválido. |
| `sequence/run_01.json` a `run_06.json`, exceto `run_03.json` | Eventos e resumo do core, séries e resumo completos de cada ajuste válido; o passo 03 não produz ajuste. |
| `model_initial.json` | Primeiro corte com diagnóstico placebo habilitado. |
| `model_final.json` | Corte final com a correção tardia. |
| `model_post_outcome_masking.json` | Experimento de perturbação de `treated` pós; não é um novo lote comercial. |
| `model_initial_validation.json`, `model_final_validation.json` | Identidades numéricas e verificações dos intervalos, séries e serialização. |
| `model_validation_summary.json` | Consolidação dos testes de contrato e dos ensaios inicial/final. |
| `local_environment.json` | Versões do ambiente local efetivamente usado, inclusive dependências transitivas. |

O parâmetro `run_placebo=True` pertence apenas ao ensaio inicial de diagnóstico.
A sequência usa `run_placebo=False`, como o fluxo de demonstração, para manter
uma única configuração de análise entre os cinco estados.

## Dependências científicas efetivamente usadas

| Componente | Versão local |
|---|---:|
| Python | 3.12.14 |
| tfp-causalimpact | 0.2.0 |
| tensorflow | 2.18.1 |
| tensorflow-probability | 0.25.0 |
| tf-keras | 2.18.0 |
| numpy | 1.26.4 |
| pandas | 2.2.3 |
| scipy | 1.14.1 |
| altair | 5.5.0 |

O motor seleciona CPU e `float64`, com 300 amostras retidas, 100 passos de
warmup, sazonalidade semanal, `alpha=0.05`, `prior_level_sd=0.01` e seed
`[42, 2026]`. O pacote Google e suas opções reais são chamados diretamente;
não há substituição por regressão de outro pacote. A compatibilidade de
TFP 0.25 com TensorFlow 2.18 e Keras 2 está documentada nas
[notas oficiais da versão](https://github.com/tensorflow/probability/releases/tag/v0.25.0).
O sucesso local não dispensa conferir as dependências no Environment do
notebook Databricks. Não se instala PySpark para este motor.

## Como interpretar as evidências

`summary.relative_effect` é uma **fração**: multiplique por 100 somente para
exibir porcentagem. `posterior_tail_probability` é a quantidade de cauda
calculada pelo pacote; não é probabilidade literal de causalidade nem aprovação
automática de campanha. Os intervalos de 95% são condicionados ao modelo e às
suas hipóteses.

Os limites do efeito acumulado são extraídos das trajetórias posteriores do
Google. Não são a soma dos limites diários. As verificações confirmam que o
último intervalo acumulado da série coincide com o resumo acumulado.

O pacote mascara a resposta observada pós no ajuste. Os controles pós entram
na previsão contrafactual e também no prior de regressão padrão da versão
0.2.0; por isso não se afirma que todo cálculo usa apenas o pré. Ampliar o
corte pode revisar estimativas no período comum. Cortes com 14 e 35 dias pós
têm exposições diferentes: seus acumulados não são uma comparação de mesma
janela.

O erro no pré é um diagnóstico **dentro da amostra**. O placebo reserva os
últimos 14 dias do pré como pseudo-pós e ajusta nos 70 anteriores. Ele é um
diagnóstico adicional, não uma prova de ausência de confundimento. A configuração
de amostragem é didática e não representa uma análise completa de convergência
MCMC. Novos ambientes podem produzir pequenas diferenças numéricas; compare
versões, parâmetros e tolerâncias antes de concluir que houve falha.
