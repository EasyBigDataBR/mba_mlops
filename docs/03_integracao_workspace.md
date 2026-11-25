# Integrar o projeto existente

## Ponto de partida

O usuário indicou o catálogo/schema `mba.mlops_causalimpact` e autorizou os ajustes necessários. O GitHub estava vazio. O conteúdo dos notebooks, os contratos das tabelas, o Job e a implementação do modelo ainda precisam ser lidos.

A imagem mostra sete tabelas, mas uma tem o nome truncado. A revisão não completa esse nome por suposição. A função e o modelo chamados `bh_counterfactual_model` também precisam ser inspecionados: o nome não informa qual biblioteca foi usada.

## Primeiro insumo: código original

No Databricks:

1. Abra **Workspace** e localize a pasta do projeto indicada na conversa.
2. Clique com o botão direito na pasta.
3. Escolha **Download as → Zip - Source (notebook + files only)**.
4. Anexe o ZIP à conversa de revisão, ou importe o código-fonte revisado para este repositório.

Esse formato reúne notebooks e arquivos e exclui as saídas das células. Para conferir as dependências serverless, inclua também a configuração do ambiente, quando ela não fizer parte da exportação.

Não é preciso reenviar a base completa para iniciar a revisão do código.

Documentação: https://docs.databricks.com/aws/en/notebooks/notebook-export-import

## Inventário opcional de metadados

O notebook `notebooks/00_Inventario_CausalImpact.py` pode ser importado no Databricks para obter nomes completos, colunas e tipos. Ele não instala dependências, não executa modelos e não altera os objetos do projeto.

A saída é um relatório JSON. Se uma consulta de metadados não estiver disponível, o relatório deve registrar a limitação; ela não prova que o objeto está ausente.

O inventário é complementar. Para corrigir o modelo, continuamos precisando do código original.

## Ordem de integração

1. Identificar notebooks, arquivos de suporte, ambiente e tarefas existentes.
2. Confirmar os nomes completos e contratos das sete tabelas.
3. Ler a implementação de `bh_counterfactual_model`, incluindo a distribuição instalada e o tratamento pré/pós.
4. Confirmar campanha, métrica, controles, data da intervenção e origem real ou sintética dos dados.
5. Mapear a sequência existente para os cinco encontros.
6. Ajustar o corte por encontro, a completude e a preservação do histórico.
7. Validar uma execução curta com dados do projeto, registrando as evidências.
8. Validar a repetição manual por Job e o painel.
9. Produzir os gráficos a partir dessas execuções identificadas.
10. Atualizar e conferir os cinco decks FGV IDE, suas versões PPTX/PDF e seus links online.

## Critérios técnicos de aceitação

- O fluxo usa o schema existente e seus contratos confirmados.
- A análise usa a implementação acordada do CausalImpact; uma regressão ou outro estimador não é apresentado como equivalente.
- O pós não é usado como desfecho de treinamento do contrafactual.
- Controles, intervenção e pré não mudam silenciosamente entre encontros.
- Dados futuros, lacunas e ingestão incompleta são identificados.
- Uma repetição não duplica ingestão nem apaga a evidência anterior.
- Resultado, código, dados, parâmetros e ambiente podem ser relacionados.
- A recuperação de uma análise anterior é demonstrada sem prometer recursos que não foram testados.
- Os estados “preparado”, “executado” e “validado” são distintos.
- A função e o modelo existentes só recebem mudanças após a leitura de sua implementação e de seus consumidores.

## Preparação dos slides

Os decks finais terão exemplos e capturas do fluxo confirmado. A proposta editorial está no roteiro; ela não é evidência de que uma célula ou um Job já tenha sido executado.

Preservar os dois encerramentos originais do modelo FGV IDE. Incluir URLs oficiais e continuidade nas notas de todos os slides. Usar uma linguagem dirigida a quem está aprendendo.
