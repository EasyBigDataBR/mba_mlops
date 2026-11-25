# Demonstração: uma campanha, seis execuções

Você vai acompanhar o mesmo estudo enquanto novos arquivos chegam. A pergunta permanece: **qual foi o efeito da campanha nas conversões?** A cada ciclo, confira também se os dados e o resultado são rastreáveis.

## Preparação única

Conecte a branch `main`, execute `00_Configurar` e escolha a pasta de entrada. Coloque apenas os arquivos `01` a `05`. Os arquivos de distribuição em `data_demo/` não são ingeridos automaticamente.

Para conhecer as etapas, faça a primeira execução com `01 → 02 → 03`. Depois, execute `05_Criar_Job` com os mesmos parâmetros. Os ciclos seguintes podem ser executados no Job com **Run now**. Você também pode usar `04_Orquestrar` diretamente; ele executa o mesmo código.

Guarde estes valores da primeira execução: `demo_id`, `snapshot_id`, `analysis_id` e `mlflow_run_id`. Eles ligam arquivos, dados, código e resultado.

## Ciclo 1 · Crie a primeira referência

**Entregue:** `01_base_pre_01.csv`, `02_base_pre_02.csv`, `03_base_pre_03.csv`, `04_base_pre_04.csv` e `05_base_pos_01.csv`, juntos.

São 84 dias de pré e 14 dias de pós. O corte é 03/11/2026. Observe o gráfico da série tratada, o contrafactual e sua faixa de incerteza. O MLflow registra configuração, dependências, hashes e a série completa.

**Para explorar:** como você demonstraria que o resultado usa exatamente esses arquivos?

Repita sem acrescentar nada. O snapshot permanece igual e o modelo é reutilizado quando código, dependências e configuração também são iguais. As tentativas ficam registradas, mas não surgem novos dados ou uma nova análise por causa de um clique repetido.

## Ciclo 2 · Atualize com dados novos

**Acrescente:** `06_append_pos_02.csv`.

A série passa a 105 dias, com corte em 10/11/2026. O pré e a intervenção permanecem fixos. Compare a média e a incerteza com o ciclo anterior; o acumulado também cresce porque há mais dias observados.

**Para explorar:** o que mudou na entrada, na configuração e no resultado?

## Ciclo 3 · Mostre uma falha de qualidade

**Acrescente:** `07_append_pos_03_invalido.csv`.

O controle `control_a` está vazio em 14/11/2026. A validação rejeita o arquivo inteiro. **A run deve terminar com erro**: isso é o comportamento esperado. Não há imputação nem publicação parcial dos seis dias sem erro.

Abra `03_Painel_e_Validacao`: o resultado anterior continua disponível, identificado como `PREVIOUS_VALID_RESULT`. A última tentativa aparece bloqueada; o corte aceito continua 10/11/2026. Consulte `ci_demo_ingestion_control` para mostrar a coluna, data e motivo.

**Para explorar:** por que um gráfico antigo, sozinho, poderia esconder a falha atual?

## Ciclo 4 · Recupere com uma correção explícita

**Acrescente:** `08_correction_pos_03.csv`. Mantenha o `07` na pasta.

O manifesto declara que a nova entrega corrige aquele período. Só um `08` válido pode substituir o `07`. O histórico mantém o erro original e identifica quem o corrigiu. A série aceita passa a 112 dias, com corte em 17/11/2026.

**Para explorar:** como diferenciar uma recuperação auditável de apagar um erro do histórico?

## Ciclo 5 · Observe a mudança no efeito

**Acrescente:** `09_append_pos_04_efeito_atenuado.csv`.

O corte chega a 24/11/2026, com 119 dias. No gerador sintético, o efeito da última semana cai de +35 para +8 conversões/dia. O modelo não recebe essa verdade como variável; ela está no manifesto apenas para conferir a demonstração.

Observe a semana final e o efeito médio. O acumulado ainda pode aumentar enquanto a média diminui. Essa mudança não significa automaticamente “drift do modelo”: os dados simulam uma mudança real no efeito da campanha. Qualidade do dado, estabilidade dos controles e mudança de negócio são hipóteses diferentes.

**Para explorar:** qual evidência você buscaria antes de treinar outra configuração?

## Ciclo 6 · Corrija um dia antigo

**Acrescente:** `10_correction_dia_anterior.csv`.

A contagem de `treated` em 26/10/2026 muda de 176 para 188. A nova revisão substitui essa linha completa. Ela não soma a contagem antiga, não duplica o dia e não elimina as demais linhas do arquivo `05`.

O corte continua 24/11/2026 e a série continua com 119 dias. O hash muda e uma nova análise é registrada. No ensaio local com a mesma seed, o contrafactual ficou igual e o efeito acumulado aumentou em 12, exatamente a correção da contagem.

**Para explorar:** por que somente o número de linhas ou a data máxima não identificam uma versão dos dados?

## Como ler o painel

| Indicador | Significado |
| --- | --- |
| `CONSISTENT` | Última ingestão e análise correspondente estão alinhadas; integridade passou. Não é aprovação causal/comercial. |
| `PREVIOUS_VALID_RESULT` | Há tentativa bloqueada, análise com erro ou atualização sem análise; o resultado mostrado é o válido preservado. |
| `NO_ANALYSIS` | Ainda não há análise concluída para esse `demo_id`. |
| `INCONSISTENT` | A conferência dos efeitos persistidos falhou; investigar antes de interpretar. |

O notebook 03 contém três gráficos: observado versus contrafactual, efeito diário e efeito acumulado. As consultas em `sql/painel.sql` permitem montar visualizações no próprio Databricks. Elas não criam nem publicam automaticamente um dashboard.

## Cortes, revisões e repetição

`as_of` vazio usa o último dia completo dos arquivos aceitos. Uma data explícita recorta o **snapshot atual**, incluindo correções já recebidas. Isso não recupera automaticamente uma revisão histórica: para conferir a versão exata de um resultado antigo, consulte seu `snapshot_id`, os arquivos registrados e a run MLflow.

Os arquivos são imutáveis por nome e hash. Não abra e salve o mesmo CSV de novo: isso pode alterar os bytes e será detectado. Para repetir a história do zero, crie outra pasta de entrada e outro `demo_id`, enviando novamente só os cinco primeiros arquivos. Nenhuma limpeza destrutiva é necessária.

## Quando algo diferente falhar

| Sintoma | Próximo passo |
| --- | --- |
| Pacote não instala | Confira quotas, acesso de saída e Environment. Use `requirements.txt`; não instale PySpark. |
| Drive não abre | Confira conexão UC, OAuth, permissões e suporte do ambiente. Se necessário, escolha explicitamente `volume` e envie os mesmos bytes. |
| Sem acesso às tabelas/volume | Confira `USE CATALOG`, `USE SCHEMA` e permissões de criação/leitura/escrita da identidade do Job. |
| Arquivo desconhecido/hash divergente | Compare com `data_demo/manifest.json`; restaure os bytes originais. |
| `07` bloqueou | Comportamento esperado. Acrescente `08` e rode novamente. |
| MLflow falhou | Confira `experiment_path` e permissão. A análise não recebe marcador de publicação até sua evidência ser registrada. |
| Quota Free esgotada | Aguarde a renovação da quota e retome. O projeto não pede upgrade para pago. |

## Fontes oficiais

- [Google TFP CausalImpact](https://github.com/google/tfp-causalimpact)
- [MLflow Tracking](https://docs.databricks.com/aws/en/mlflow/tracking)
- [Git em Jobs](https://docs.databricks.com/aws/en/jobs/git)
- [Ingestão do Drive](https://docs.databricks.com/aws/en/ingestion/google-drive)
- [Limites da Free Edition](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations)
