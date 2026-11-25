# Git, notebooks e Job manual no Databricks Free

Use a branch `main` do repositório [`EasyBigDataBR/mba_mlops`](https://github.com/EasyBigDataBR/mba_mlops) e execute o case no Databricks Free. Os arquivos de entrada podem vir de um volume ou de uma conexão autorizada com o Drive. O código fica no Git; dados aceitos, auditoria e resultados ficam no Databricks.

Este guia e o [template do Job](../jobs/job_template.json) foram conferidos com a documentação oficial em **25/11/2026**. A aceitação do Job, o acesso ao Drive e a execução completa nesta conta Free ainda precisam ser verificados no workspace. Validação local da biblioteca não comprova execução no Databricks.

## 1. Como os notebooks se encaixam

| Notebook | Quando usar |
| --- | --- |
| `00_Configurar.py` | Conferir ambiente, parâmetros e acesso aos objetos do case. |
| `01_Ingerir_Atualizacoes.py` | Entender e executar a leitura dos arquivos e as validações da entrada. |
| `02_Executar_CausalImpact.py` | Estimar o contrafactual para o corte aceito. |
| `03_Painel_e_Validacao.py` | Conferir resultados, qualidade e rastreabilidade. |
| `04_Orquestrar.py` | Executar o ciclo completo pelo Job manual. |
| `05_Criar_Job.py` | Opcional: criar a definição do Job, sem iniciar uma execução. |

O Job tem **uma tarefa**, apontando para `04_Orquestrar.py`. Ela chama funções dos módulos em `src/` e mantém ingestão, análise e validação na mesma sessão. A falha de uma etapa deve interromper o ciclo e ficar registrada, sem publicar análise parcial.

Essa escolha evita preparar três ambientes de tarefa para um exercício pequeno. Não é uma promessa de tempo ou consumo fixos. Uma cadeia de três tarefas continua sendo uma opção futura se precisarmos de ambientes, permissões ou retomadas independentes. `dbutils.notebook.run()` não é usado pelo orquestrador: cada chamada cria um Job efêmero e pode acrescentar inicializações. [Orquestração e módulos][orchestration]

## 2. Primeiro, conecte o Git folder

1. No Databricks, abra **Workspace**, escolha sua pasta e selecione **Create → Git folder**.
2. Informe `https://github.com/EasyBigDataBR/mba_mlops.git`, provedor **GitHub**, e um nome para a pasta.
3. Configure a credencial Git pela interface se for solicitada. Não coloque credenciais em notebooks ou parâmetros.
4. Selecione **main**. Antes de começar uma aula, abra o diálogo Git e use **Pull**.
5. Abra `notebooks/00_Configurar.py`. Confira a configuração antes de executar as etapas do case.

Não é necessário habilitar o Git CLI em preview. O Git folder é uma cópia de trabalho: atualizar `main` no GitHub não atualiza essa cópia sem o **Pull**. Faça a atualização antes de iniciar a sessão, pois ela pode limpar o estado do notebook. [Operações de Git folder][git-folder]

## 3. Prepare as dependências no notebook de entrada

Antes do primeiro **Run All** interativo em `02` ou `04`, selecione **Serverless**, CPU e memória padrão. No painel **Environment**, escolha **Standard versão 4** — em **More**, se necessário — e aplique. Essa versão documenta **Python 3.12.3**, pandas 2.2.3 e MLflow Skinny 2.22.0, com suporte previsto até **13/08/2028**. O ambiente ainda precisa estar disponível nesta conta Free. [Environment 4][environment-four] · [Versões e suporte][environment-versions]

O template do Job fixa `environment_version="4"` no ambiente `causalimpact_py312`, referenciado pela tarefa. Assim, o Job não depende do ambiente padrão que seria resolvido na ausência de `environment_key` e metadados no notebook. A versão do ambiente seleciona o Python; `%pip` não muda a versão do interpretador.

Os notebooks `02_Executar_CausalImpact.py` e `04_Orquestrar.py` preparam suas dependências com `%pip` e versões fixadas. As páginas oficiais de bibliotecas e de tarefa Notebook confirmam `%pip` em notebooks serverless e em Jobs. Mantenha instalação e `dbutils.library.restartPython()` antes de criar variáveis, importar módulos ou executar etapas; o reinício apaga o estado Python. Ter executado `00_Configurar.py` interativamente não instala bibliotecas na sessão futura do Job. Não instale PySpark. [Bibliotecas do notebook][pip] · [Tarefa Notebook][notebook-task] · [Reinício do Python][restart]

O **Environment do notebook** também permite configurar dependências e habilitar **Include in source file exports**, persistindo a configuração no `.py` com metadados PEP 723. É uma alternativa documentada; confira a exportação real antes de substituir as células `%pip` por ela.

O ambiente do Job fixa somente a base, sem duplicar a lista científica instalada pelas células `%pip`. Aplicar alterações pelo painel **Environment** também reinicia o processo Python. Confira a versão efetiva antes da análise. [Environment serverless][environment]

A combinação TensorFlow/TFP/Keras precisa permanecer compatível. TensorFlow 2.18.1 publica wheels para Python 3.12 em Linux x86-64 e ARM64. O TFP 0.25 documenta a família TensorFlow 2.18 e requer Keras 2 por meio de `tf-keras`. O ensaio local não reproduz todo o ambiente Databricks: o primeiro ciclo ainda deve confirmar instalação, imports e integração Spark/MLflow. [TensorFlow 2.18.1][tensorflow] · [Notas do TFP 0.25][tfp]

## 4. Parâmetros do ciclo

Os parâmetros do template estão no nível do Job e chegam automaticamente aos widgets da tarefa. Use **Run now with different parameters** para mudar apenas uma execução. [Parâmetros de Job][parameters]

| Parâmetro | Valor inicial | Uso |
| --- | --- | --- |
| `catalog` | `mba` | Catálogo dos objetos do case. |
| `schema` | `mlops_causalimpact` | Schema do case. |
| `source_mode` | `volume` | `volume` ou `drive`. |
| `source_path` | `/Volumes/mba/mlops_causalimpact/landing/causalimpact_demo` | Caminho absoluto da pasta de entrada; no modo Drive, URL informada somente na configuração privada. |
| `drive_connection` | vazio | Nome da conexão Unity Catalog autorizada, somente para Drive. |
| `as_of` | vazio | Último dia completo presente na fonte validada; uma data ISO `AAAA-MM-DD` limita o corte do snapshot atual. |
| `num_results` | `300` | Número de amostras posteriores da análise; não é limite de arquivos. |
| `demo_id` | `campanha_demo_v1` | Identidade da demonstração. |
| `max_files_per_run` | `10` | Limite de segurança para a seleção de arquivos; não funciona como cursor de entregas. |
| `experiment_path` | `/Shared/MBA_CausalImpact_Demo` | Experimento MLflow do workspace, criado se ainda não existir e houver permissão. |

Com `as_of` vazio, o corte é o último dia completo **presente na fonte validada**, observado o calendário em `America/Sao_Paulo`; não significa automaticamente ontem. Confira o **corte efetivo** dos dados aceitos: mudar o calendário não cria observações nem autoriza preencher lacunas. Depois da conferência inicial, mantenha pré-período, data de intervenção e controles fixos. Uma correção pode mudar o snapshot sem aumentar o corte.

Informar uma data em `as_of` faz um **recorte temporal do snapshot atual**. Isso não recupera automaticamente os bytes de uma análise antiga: se o arquivo `10` corrigiu um dia anterior, o novo recorte contém essa correção. Para reproduzir a entrada e a configuração históricas, use o snapshot e os hashes originais, o commit, os parâmetros, a seed e as versões do ambiente daquela análise.

### Volume: caminho inicial do exercício

O volume `landing` precisa existir, com uma subpasta `causalimpact_demo`. A identidade que executa o Job deve conseguir ler os arquivos e gravar os resultados nas tabelas do case. Para o volume, confira `USE CATALOG`, `USE SCHEMA` e `READ VOLUME`; enviar arquivos também exige `WRITE VOLUME`. Criar um volume gerenciado exige `CREATE VOLUME` no schema. [Permissões de volumes][volume]

### Drive: fonte opcional, com conexão e OAuth conferidos

Use `source_mode=drive` com uma **conexão Unity Catalog já autorizada** para a pasta ou prepare uma seguindo o [guia oficial de OAuth para SQL/Spark][drive]. Esse caminho exige conta com permissão para criar um projeto Google Cloud, habilitar a Drive API, configurar consentimento OAuth, credenciais de cliente e o callback do workspace; depois, crie a conexão no Databricks com escopo de leitura `drive.readonly`. O projeto serve à autorização da fonte; o processamento do case continua no Databricks.

Confirme `USE CONNECTION` para a identidade do Job no acesso standard, acesso à pasta e suporte à integração, cujo requisito documentado é Runtime 17.3 ou superior. Fixar o Python pelo Environment 4 não comprova que o conector esteja habilitado. A disponibilidade no Free e a leitura desta pasta ainda não foram verificadas. O conector gerenciado tem configuração própria; não presuma que seu OAuth substitua a preparação exigida pela rota SQL/Spark.

O leitor usa `binaryFile` para conferir o hash dos bytes originais antes de interpretar o CSV e registrar a entrada bronze. Se o conector ou o formato não forem aceitos pela conta, a etapa deve falhar explicitamente, sem trocar de fonte nem de formato em silêncio.

Informe URL e nome da conexão apenas nos parâmetros privados do Job. Não publique IDs, tokens ou segredos no Git. Se a conexão não estiver disponível no Free, baixe os CSVs autorizados, envie os mesmos bytes ao volume e selecione `source_mode=volume`; preserve nomes e hashes. Essa mudança é explícita e mantém a origem versionada sem exigir um pipeline adicional. [Ingestão do Drive][drive]

## 5. Crie um Job manual: escolha uma rota

### Rota A — Git folder e fonte WORKSPACE

É a rota inicial para conferir o ambiente pela interface:

1. Abra **Jobs & Pipelines → Create → Job** e adicione uma tarefa **Notebook**.
2. Escolha fonte **Workspace** e navegue até o notebook `04_Orquestrar` no Git folder. Use o seletor, sem inventar o caminho interno a partir do nome `.py` do Git.
3. Selecione **Serverless**. Em **Environment and Libraries**, configure um **Jobs Environment** com **Standard versão 4**; se a interface usar o seletor antigo, escolha **Environment version 4**. Alternativamente, use **Notebook Environment** somente após conferir que o notebook já está em Standard versão 4. Inclua os parâmetros da tabela anterior.
4. Mantenha execução manual, concorrência máxima `1`, fila desativada e tentativas adicionais `0`. Desative **Enable serverless auto-optimization**, que pode incluir novas tentativas.
5. Se disponível, desligue **Performance optimized** para usar **Standard**. Ele prioriza menor consumo de DBUs, com inicialização potencialmente mais demorada.
6. Salve o Job. Faça **Pull** no Git folder antes de executar uma versão nova do código.

### Rota B — Git remoto e template JSON

O arquivo [jobs/job_template.json](../jobs/job_template.json) é um corpo de criação para **Jobs API 2.2**. Ele configura a mesma tarefa, com fonte `GIT`, GitHub e branch `main`. O path é **`notebooks/04_Orquestrar.py`**, relativo ao repositório, com `.py` e sem `/` ou `./` no início. [Tarefa Notebook][notebook-task]

Na interface, escolha fonte **Git provider**, configure o repositório e a referência e use esse path. Para reproduzir uma versão, troque `git_branch` por `git_commit` com um SHA real revisado; não mantenha os dois campos. Cada run resolve um snapshot do código e mostra o SHA usado nos detalhes. O Pull do Git folder não controla essa rota. [Git em Jobs][git-jobs]

Se já usa a CLI autenticada, criar somente a definição é suficiente:

```bash
databricks jobs create --json @jobs/job_template.json
```

Esse comando não inicia o processamento. Não repita a criação para atualizar um Job existente: anote o ID retornado e edite aquela definição. O template não contém agenda, gatilho, cluster clássico ou destinatários. O timeout deve ser definido após medir uma execução representativa. [Criar e gerenciar Jobs][automate] · [Contrato da API][jobs-api]

O notebook opcional `05_Criar_Job.py` cria somente a definição. Se encontrar um Job com o mesmo nome e a tag `mba_mlops_demo=causalimpact_demo_v1`, reutiliza seu ID sem executar ou redefinir a configuração. Nesse caso, confira também o ambiente do Job existente: uma mudança no template Git não altera automaticamente a definição já criada.

As duas rotas dependem das permissões e dos recursos disponíveis na conta. **Standard** e o ambiente selecionado devem ser conferidos na interface; não altere a conta para um plano pago para seguir este exercício. [Jobs serverless][serverless]

## 6. Entregue os 10 CSVs em ciclos

Os arquivos de `data_demo/` são **sintéticos**. O [manifesto](../data_demo/manifest.json) fixa datas, seed, ordem, hashes e correções. Para uma demonstração nova, use o procedimento do gerador; não regenere o passado apenas porque o dia atual mudou.

| Ciclo | Arquivos novos | O que conferir |
| --- | --- | --- |
| 1 | `01` a `05`, juntos | Carga inicial completa antes da análise. |
| 2 | `06` | Extensão válida da série. |
| 3 | `07` | Rejeição deliberada por controle ausente; nenhuma nova análise válida. |
| 4 | `08` | Correção explícita do arquivo `07`; rejeição anterior preservada no histórico. |
| 5 | `09` | Novos dias aceitos; comparar resultados e intervalos. |
| 6 | `10` | Correção de um dia antigo; snapshot muda, corte não recua. |

Mantenha os arquivos anteriores na origem. Depois dos cinco iniciais, acrescente um arquivo por vez; não é preciso mudar o limite `10` entre ciclos. Repetir o mesmo nome com o mesmo hash deve ser um no-op. Uma correção chega como arquivo novo e substitui a linha da mesma `date`, sem somar as contagens antigas. A rejeição de `07` não deve impedir o processamento posterior de `08`.

## 7. Confira a evidência antes de avançar

Em cada ciclo, confira versão do código, arquivos selecionados e seus hashes, corte solicitado e efetivo, status da ingestão, identidade da análise e resultado da validação. Em caso de rejeição, o último resultado válido deve continuar distinguível da tentativa que falhou.

Configure um **experimento MLflow do workspace** explicitamente antes de registrar runs. O notebook temporário de um Job com Git remoto não é um lugar confiável para manter um experimento do próprio notebook. O código chama `mlflow.set_experiment()` com `experiment_path`, cujo padrão é `/Shared/MBA_CausalImpact_Demo`; a identidade do Job precisa ter acesso a ele e permissão para criá-lo se necessário. Grave saídas persistentes em tabelas ou volumes; tarefas de Git remoto não podem gravar nos arquivos do workspace. [Tarefa Notebook][notebook-task] · [Git em Jobs][git-jobs]

No Free, use execução manual, uma tarefa por vez e os arquivos pequenos do exercício. A edição é gratuita, mas está sujeita a cotas de uso; oferece apenas serverless, limita tarefas simultâneas e restringe acesso de saída à internet. Uma quota esgotada pode suspender o compute até sua renovação. Não há garantia de duração ou disponibilidade da sessão. [Limites da Free Edition][free]

## Documentação oficial

[orchestration]: https://docs.databricks.com/aws/en/notebooks/notebook-workflows
[git-folder]: https://docs.databricks.com/aws/en/repos/git-operations-with-repos
[environment]: https://docs.databricks.com/aws/en/compute/serverless/dependencies
[environment-four]: https://docs.databricks.com/aws/en/release-notes/serverless/environment-version/four
[environment-versions]: https://docs.databricks.com/aws/en/release-notes/serverless/environment-version
[pip]: https://docs.databricks.com/aws/en/libraries/notebooks-python-libraries
[restart]: https://docs.databricks.com/aws/en/libraries/restart-python-process
[tfp]: https://github.com/tensorflow/probability/releases/tag/v0.25.0
[tensorflow]: https://pypi.org/project/tensorflow/2.18.1/
[parameters]: https://docs.databricks.com/aws/en/jobs/job-parameters
[volume]: https://docs.databricks.com/aws/en/volumes/privileges
[drive]: https://docs.databricks.com/aws/en/ingestion/google-drive
[notebook-task]: https://docs.databricks.com/aws/en/jobs/tasks/notebook
[git-jobs]: https://docs.databricks.com/aws/en/jobs/git
[automate]: https://docs.databricks.com/aws/en/jobs/automate
[jobs-api]: https://docs.databricks.com/api/jobs/v2/create-job
[serverless]: https://docs.databricks.com/aws/en/jobs/run-serverless-jobs
[free]: https://docs.databricks.com/aws/en/getting-started/free-edition-limitations

- [Orquestração e módulos][orchestration]
- [Git folder][git-folder] e [Git em Jobs][git-jobs]
- [Ambientes serverless][environment], [bibliotecas][pip] e [restart][restart]
- [Environment 4][environment-four] e [versões e suporte][environment-versions]
- [TensorFlow 2.18.1][tensorflow] e [TFP 0.25: compatibilidade][tfp]
- [Parâmetros de Job][parameters] e [tarefa Notebook][notebook-task]
- [Volumes][volume] e [Drive como fonte][drive]
- [Automação][automate], [Jobs API][jobs-api] e [Jobs serverless][serverless]
- [Limites da Free Edition][free]
