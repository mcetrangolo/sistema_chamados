# Requisitos do Sistema de Gestão de Serviços de TI

## 1. Visão Geral

Desenvolver uma plataforma web para Gestão de Serviços de TI, destinada ao registro, acompanhamento, tratamento e documentação de chamados, incidentes, requisições, ativos de TI, base de conhecimento, indicadores gerenciais e fluxos internos de atendimento.

O sistema deverá iniciar com um módulo robusto de Service Desk, mas ser desenvolvido com arquitetura modular, permitindo evolução futura para funcionalidades semelhantes a soluções ITSM, como GLPI, incluindo inventário, CMDB, catálogo de serviços, SLA, contratos, fornecedores, gestão de mudanças, problemas, projetos e integrações corporativas.

## 2. Objetivos do Sistema

### 2.1 Objetivo Geral

Centralizar e profissionalizar a gestão dos atendimentos de TI, permitindo controle operacional, rastreabilidade, transparência, geração de indicadores, melhoria contínua dos serviços e apoio à tomada de decisão.

### 2.2 Objetivos Específicos

* Registrar todos os chamados e solicitações de TI.
* Classificar demandas como incidente, requisição, dúvida, tarefa, problema ou mudança.
* Controlar prazos de atendimento por meio de SLA.
* Permitir acompanhamento pelo usuário solicitante.
* Registrar histórico completo das ações realizadas.
* Vincular chamados a usuários, setores, equipamentos, sistemas e serviços.
* Gerar relatórios técnicos e gerenciais.
* Criar base de conhecimento com soluções recorrentes.
* Estruturar inventário de ativos de TI.
* Permitir integração futura com Active Directory, e-mail, monitoramento, inventário automático e sistemas administrativos.

## 3. Problema a Ser Resolvido

A ausência de uma plataforma centralizada de atendimento gera dificuldades como:

* Falta de registro formal das demandas.
* Perda de histórico de atendimentos.
* Dificuldade para comprovar serviços executados.
* Ausência de controle de prazos e prioridades.
* Falta de indicadores de produtividade.
* Dificuldade de identificar problemas recorrentes.
* Baixa rastreabilidade sobre equipamentos afetados.
* Dificuldade de planejamento de compras, manutenção e melhorias.
* Dependência de controles manuais, mensagens informais ou planilhas.

## 4. Escopo do Sistema

### 4.1 Escopo Inicial

A primeira versão deverá contemplar:

* Gestão de usuários.
* Gestão de setores.
* Gestão de perfis e permissões.
* Abertura e acompanhamento de chamados.
* Classificação por tipo, categoria, prioridade, impacto e urgência.
* Controle de status.
* Histórico de atendimento.
* Comentários públicos e internos.
* Anexos.
* Atribuição de técnico ou equipe.
* SLA básico.
* Relatórios essenciais.
* Dashboard inicial.
* Base de conhecimento básica.
* Inventário manual de equipamentos.

### 4.2 Escopo Futuro

O sistema deverá ser preparado para evoluir para:

* Inventário automático de rede.
* Agente de coleta para estações Windows/Linux.
* Integração com Active Directory/LDAP.
* Integração com e-mail.
* Catálogo de serviços.
* Aprovações internas.
* Gestão de mudanças.
* Gestão de problemas.
* CMDB.
* Gestão de contratos, fornecedores e licenças.
* API REST.
* Webhooks.
* Integração com ferramentas de monitoramento.
* Módulo mobile ou interface responsiva avançada.
* Gestão de projetos e tarefas.

## 5. Perfis de Usuário

### 5.1 Administrador do Sistema

Usuário com acesso total à plataforma.

Permissões:

* Gerenciar usuários, grupos, setores e permissões.
* Configurar categorias, status, prioridades e tipos de chamado.
* Configurar regras de SLA.
* Configurar equipes de atendimento.
* Gerenciar parâmetros do sistema.
* Acessar todos os chamados.
* Gerar relatórios completos.
* Gerenciar base de conhecimento.
* Gerenciar inventário.
* Auditar ações realizadas no sistema.

### 5.2 Gestor de TI

Usuário responsável pelo acompanhamento gerencial da operação de TI.

Permissões:

* Visualizar indicadores gerais.
* Acompanhar produtividade dos técnicos.
* Acompanhar SLAs.
* Redistribuir chamados.
* Visualizar relatórios por setor, técnico, categoria e período.
* Aprovar mudanças ou solicitações críticas.
* Gerenciar filas de atendimento.

### 5.3 Técnico de TI

Usuário responsável pela execução dos atendimentos.

Permissões:

* Visualizar chamados atribuídos a si ou à sua equipe.
* Registrar andamento.
* Alterar status conforme fluxo permitido.
* Adicionar comentários internos.
* Solicitar informações ao usuário.
* Vincular ativos ao chamado.
* Registrar solução aplicada.
* Encerrar ou encaminhar chamados, conforme permissão.

### 5.4 Usuário Solicitante

Servidor, colaborador ou usuário final que registra demandas.

Permissões:

* Abrir chamados.
* Acompanhar seus próprios chamados.
* Adicionar comentários.
* Enviar anexos.
* Responder solicitações do técnico.
* Confirmar solução.
* Avaliar atendimento.
* Consultar artigos públicos da base de conhecimento.

### 5.5 Aprovador

Usuário responsável por aprovar determinadas solicitações.

Exemplos:

* Chefia imediata.
* Coordenador de setor.
* Gestor de contrato.
* Responsável por sistema.

Permissões:

* Receber solicitações pendentes de aprovação.
* Aprovar ou rejeitar solicitações.
* Registrar justificativa.
* Acompanhar histórico das aprovações.

## 6. Conceitos Principais

### 6.1 Chamado

Registro formal de uma demanda de TI.

### 6.2 Incidente

Interrupção ou degradação não planejada de um serviço.

Exemplos:

* Computador não liga.
* Internet fora do ar.
* Sistema indisponível.
* Impressora com erro.

### 6.3 Requisição de Serviço

Solicitação planejada de serviço, acesso, equipamento ou configuração.

Exemplos:

* Criação de usuário.
* Instalação de software.
* Solicitação de equipamento.
* Liberação de acesso.

### 6.4 Problema

Causa raiz de um ou mais incidentes recorrentes.

Exemplo:

* Quedas frequentes de rede em determinado setor.

### 6.5 Mudança

Alteração planejada na infraestrutura, sistema, rede ou serviço.

Exemplos:

* Troca de servidor.
* Atualização de sistema.
* Alteração em firewall.
* Migração de serviço.

### 6.6 Ativo de TI

Equipamento, sistema, software, licença ou recurso tecnológico controlado pelo setor de TI.

## 7. Módulo de Service Desk

### 7.1 Cadastro de Chamado

O sistema deve permitir registrar:

* Número único do chamado.
* Tipo do chamado.
* Data e hora de abertura.
* Solicitante.
* Setor.
* Telefone ou ramal.
* E-mail.
* Localização.
* Serviço afetado.
* Categoria.
* Subcategoria.
* Prioridade.
* Impacto.
* Urgência.
* Descrição detalhada.
* Anexos.
* Status.
* Técnico responsável.
* Equipe responsável.
* Prazo de SLA.
* Data de primeira resposta.
* Data de solução.
* Data de encerramento.
* Solução aplicada.
* Avaliação do usuário.

### 7.2 Tipos de Chamado

* Incidente.
* Requisição de serviço.
* Dúvida.
* Tarefa interna.
* Problema.
* Mudança.

### 7.3 Status dos Chamados

* Novo.
* Aberto.
* Em triagem.
* Em análise.
* Em atendimento.
* Aguardando usuário.
* Aguardando fornecedor.
* Aguardando aprovação.
* Agendado.
* Resolvido.
* Encerrado.
* Cancelado.
* Reaberto.

### 7.4 Prioridade

A prioridade poderá ser definida manualmente ou calculada a partir de impacto e urgência.

Prioridades:

* Baixa.
* Média.
* Alta.
* Crítica.

### 7.5 Impacto

* Individual.
* Setorial.
* Múltiplos setores.
* Institucional.
* Serviço essencial indisponível.

### 7.6 Urgência

* Baixa.
* Média.
* Alta.
* Imediata.

### 7.7 Regras de SLA

O sistema deverá permitir configurar prazos por:

* Tipo de chamado.
* Categoria.
* Prioridade.
* Setor.
* Serviço afetado.
* Horário de atendimento.
* Calendário útil.

Indicadores mínimos:

* Tempo para primeira resposta.
* Tempo para solução.
* Tempo em atendimento.
* Tempo aguardando usuário.
* Tempo aguardando fornecedor.
* Chamados dentro do SLA.
* Chamados fora do SLA.

## 8. Módulo de Catálogo de Serviços

O sistema deverá permitir cadastrar serviços oferecidos pela TI.

Exemplos:

* Criação de usuário.
* Redefinição de senha.
* Instalação de software.
* Solicitação de computador.
* Solicitação de impressora.
* Liberação de acesso a sistema.
* Criação de e-mail.
* Suporte a internet.
* Suporte a telefonia.
* Backup e restauração.

Cada serviço poderá conter:

* Nome.
* Descrição.
* Categoria.
* Prazo estimado.
* Campos obrigatórios.
* Necessidade de aprovação.
* Equipe responsável.
* SLA específico.
* Instruções ao usuário.

### 8.1 Solicitações de Novo Acesso, Rede e Wi-Fi

O catálogo deverá possuir formulários específicos para solicitações de governança de acesso, contemplando:

* Novo acesso à rede.
* Troca de senha de conta existente.
* Alteração de permissão de acesso.
* Acesso à internet Wi-Fi corporativa.

O formulário de acesso à rede deverá registrar, no mínimo:

* Nome do solicitante.
* Matrícula.
* Telefone ou ramal.
* Setor.
* E-mail.
* Cargo.
* Tipo da solicitação: novo acesso, troca de senha ou alteração de permissão.
* Usuário de rede existente, quando aplicável.
* Acesso solicitado, como pasta, sistema, perfil ou recurso de determinado departamento.
* Justificativa.
* Chefia imediata ou autorizador indicado.

O formulário de acesso à internet Wi-Fi deverá registrar, no mínimo:

* Nome do solicitante.
* Matrícula.
* E-mail.
* Setor.
* Cargo.
* Telefone.
* Tipo de equipamento.
* Fabricante.
* Modelo.
* Número de série.
* Endereço MAC.
* Justificativa.

No momento exato da solicitação, o sistema deverá apresentar o termo de ciência correspondente ao serviço solicitado. O envio somente poderá ser concluído após o usuário marcar o aceite do termo.

O aceite deverá ser armazenado com evidência auditável, incluindo:

* Versão do termo aceito.
* Texto integral do termo aceito no momento da solicitação.
* Data e hora do aceite.
* Usuário/solicitante relacionado.
* IP de origem.
* Identificação do navegador/dispositivo, quando disponível.
* Protocolo da solicitação.
* Documento PDF gerado com os dados informados e o registro do aceite.

O sistema deverá manter histórico permanente do aceite, permitindo comprovação futura de que o usuário leu e tomou ciência das responsabilidades antes da abertura ou execução do pedido.

## 9. Módulo de Base de Conhecimento

O sistema deverá permitir criar artigos, tutoriais e procedimentos.

Cada artigo deverá conter:

* Título.
* Categoria.
* Conteúdo.
* Palavras-chave.
* Público-alvo.
* Visibilidade pública ou interna.
* Autor.
* Data de criação.
* Data de atualização.
* Anexos.
* Relacionamento com chamados ou categorias.

Funcionalidades desejáveis:

* Sugestão automática de artigos ao abrir chamado.
* Registro de artigos mais acessados.
* Avaliação de utilidade do artigo.
* Controle de versão.

## 10. Módulo de Inventário de Ativos

### 10.1 Ativos Controlados

* Computadores.
* Notebooks.
* Impressoras.
* Monitores.
* Switches.
* Roteadores.
* Access points.
* Servidores.
* Nobreaks.
* Telefones IP.
* Tablets.
* Celulares institucionais.
* Softwares.
* Licenças.
* Sistemas internos.
* Links de internet.
* Contratos de TI.

### 10.2 Campos dos Ativos

* Número de patrimônio.
* Tipo de ativo.
* Fabricante.
* Modelo.
* Número de série.
* Hostname.
* IP.
* MAC address.
* Sistema operacional.
* Processador.
* Memória.
* Armazenamento.
* Setor.
* Usuário responsável.
* Localização.
* Status.
* Data de aquisição.
* Garantia.
* Fornecedor.
* Contrato vinculado.
* Histórico de manutenção.
* Chamados vinculados.

### 10.3 Descoberta de Rede

O sistema poderá futuramente realizar descoberta por:

* Nmap.
* SNMP.
* Consulta ao Active Directory.
* Agente local.
* Importação CSV.
* API de ferramentas externas.

A descoberta não deverá depender exclusivamente de ICMP/Ping.

## 11. Módulo de CMDB

O sistema deverá permitir representar itens de configuração e seus relacionamentos.

Exemplos de relacionamentos:

* Servidor hospeda sistema.
* Sistema depende de banco de dados.
* Computador pertence a usuário.
* Impressora atende determinado setor.
* Switch conecta determinado local.
* Link de internet atende unidade específica.

Finalidade:

* Apoiar análise de impacto.
* Relacionar incidentes a ativos.
* Apoiar mudanças planejadas.
* Identificar serviços críticos.

## 11.1 Módulo de Documentação Restrita de Infraestrutura

O sistema deverá possuir um módulo digital para documentação interna de infraestrutura, substituindo documentos manuais de topologia, rede, senhas, configurações e procedimentos operacionais.

Esse módulo deverá permitir registrar:

* Topologia local e lógica.
* Redes, VLANs, faixas de IP, gateways e DNS.
* Servidores, serviços, sistemas e dependências.
* Configurações relevantes de equipamentos e sistemas.
* Procedimentos de instalação, recuperação, contingência e manutenção.
* Informações restritas, como senhas, chaves, acessos e observações sensíveis.
* Anexos relacionados, como documentos antigos, diagramas, planilhas e imagens.

Por conter informações sensíveis, o acesso deverá ser limitado:

* Superusuários/administradores deverão possuir acesso total.
* O administrador deverá definir explicitamente quais usuários podem acessar cada documentação.
* Usuários não autorizados não deverão visualizar a existência nem o conteúdo dos documentos restritos.
* Apenas administradores deverão criar, editar, inativar ou anexar arquivos nesse módulo.
* O sistema deverá registrar log de visualização, criação, edição e anexos, incluindo usuário, data/hora, IP e identificação do navegador/dispositivo quando disponível.

O módulo deverá servir como repositório controlado e auditável da memória técnica da infraestrutura, reduzindo dependência de arquivos soltos e melhorando a continuidade operacional.

## 12. Módulo de Gestão de Problemas

O sistema deverá permitir registrar problemas relacionados a incidentes recorrentes.

Campos mínimos:

* Título do problema.
* Descrição.
* Incidentes relacionados.
* Serviço afetado.
* Causa provável.
* Causa raiz.
* Solução de contorno.
* Solução definitiva.
* Responsável.
* Status.
* Data de abertura.
* Data de resolução.

## 13. Módulo de Gestão de Mudanças

O sistema deverá permitir registrar mudanças planejadas.

Campos mínimos:

* Título da mudança.
* Descrição.
* Justificativa.
* Tipo da mudança.
* Risco.
* Impacto.
* Plano de execução.
* Plano de rollback.
* Janela de mudança.
* Responsável.
* Aprovador.
* Status.
* Ativos afetados.
* Serviços afetados.

Tipos de mudança:

* Normal.
* Emergencial.
* Padrão.

Status:

* Solicitada.
* Em análise.
* Aprovada.
* Rejeitada.
* Agendada.
* Em execução.
* Concluída.
* Cancelada.

## 14. Módulo de Contratos, Fornecedores e Licenças

O sistema deverá permitir controlar:

* Fornecedores.
* Contratos.
* Vigência.
* Valores.
* Objeto contratado.
* Fiscal/responsável.
* Equipamentos cobertos.
* Sistemas cobertos.
* Licenças de software.
* Quantidade adquirida.
* Quantidade em uso.
* Data de expiração.
* Alertas de vencimento.

## 15. Módulo de Relatórios e Indicadores

Relatórios mínimos:

* Chamados por período.
* Chamados por técnico.
* Chamados por setor.
* Chamados por categoria.
* Chamados por prioridade.
* Chamados por status.
* Chamados vencidos.
* Chamados dentro e fora do SLA.
* Tempo médio de atendimento.
* Tempo médio de primeira resposta.
* Demandas recorrentes.
* Ranking de categorias.
* Produtividade por técnico.
* Avaliação de satisfação.
* Ativos por setor.
* Ativos por status.
* Equipamentos com mais chamados.

Exportações:

* PDF.
* CSV.
* Excel.

## 16. Dashboard Gerencial

O painel inicial deverá apresentar:

* Total de chamados abertos.
* Total de chamados em atendimento.
* Total de chamados vencidos.
* Total de chamados resolvidos no mês.
* Chamados críticos.
* SLA cumprido.
* SLA descumprido.
* Tempo médio de atendimento.
* Categorias mais recorrentes.
* Setores com maior volume.
* Produtividade por técnico.
* Evolução mensal dos chamados.

## 17. Notificações

O sistema deverá permitir notificações por:

* E-mail.
* Painel interno.
* Futuramente WhatsApp, Telegram ou outro canal institucional.

Eventos notificáveis:

* Abertura de chamado.
* Atribuição a técnico.
* Mudança de status.
* Solicitação de informação ao usuário.
* Aprovação pendente.
* Chamado próximo do vencimento.
* Chamado vencido.
* Resolução.
* Encerramento.
* Pesquisa de satisfação.

## 18. Autenticação e Permissões

O sistema deverá possuir:

* Login e senha.
* Perfis de acesso.
* Permissões por módulo.
* Permissões por ação.
* Controle por setor/equipe.
* Integração futura com Active Directory/LDAP.
* Registro de último acesso.
* Recuperação ou redefinição de senha.

## 19. Auditoria e Rastreabilidade

O sistema deverá registrar:

* Criação de registros.
* Alterações de status.
* Alterações de prioridade.
* Alterações de responsável.
* Comentários adicionados.
* Anexos enviados.
* Aprovações e rejeições.
* Exclusões lógicas.
* Data, hora, usuário e IP da ação.

Regra importante:

* Chamados, históricos e anexos não devem ser apagados definitivamente em operação normal.
* O sistema deverá utilizar exclusão lógica ou arquivamento.

## 20. Requisitos Não Funcionais

### 20.1 Segurança

* Controle de acesso por perfil.
* Proteção contra acesso indevido.
* Proteção CSRF.
* Senhas armazenadas com hash seguro.
* Validação de uploads.
* Restrição de tipos de arquivos.
* Logs de auditoria.
* Backup periódico.
* Configuração segura para ambiente de produção.

### 20.2 Desempenho

* O sistema deverá suportar múltiplos usuários simultâneos.
* As listagens deverão possuir paginação.
* Os filtros deverão ser otimizados.
* Relatórios grandes deverão evitar travamento da aplicação.

### 20.3 Usabilidade

* Interface simples e responsiva.
* Abertura de chamado em poucos passos.
* Painel diferenciado para usuário e técnico.
* Campos obrigatórios claros.
* Histórico de fácil leitura.
* Busca rápida de chamados.

### 20.4 Manutenibilidade

* Código modular.
* Separação por apps/módulos.
* Uso de migrations.
* Documentação técnica.
* Variáveis de ambiente.
* Testes automatizados básicos.
* Padrão de nomenclatura.

### 20.5 Disponibilidade

* Execução em ambiente Docker.
* Backup do banco e arquivos anexos.
* Possibilidade de restauração.
* Logs de aplicação e servidor.

## 21. Tecnologias Sugeridas

### Backend

* Python.
* Django.
* Django REST Framework para API futura.

### Frontend

* HTML, CSS e JavaScript na versão inicial.
* Bootstrap ou Tailwind CSS.
* Futuramente React ou Vue, se necessário.

### Banco de Dados

* PostgreSQL para produção.
* SQLite apenas para desenvolvimento ou testes.

### Infraestrutura

* Docker.
* Docker Compose.
* Nginx.
* Gunicorn.
* Backup automatizado.
* Ambiente Linux.

### Integrações Futuras

* Active Directory/LDAP.
* SMTP institucional.
* Zabbix.
* Grafana.
* Nmap.
* SNMP.
* API REST.
* Webhooks.

## 22. Estrutura Modular Recomendada

Módulos sugeridos:

* `accounts` — usuários, perfis e permissões.
* `organizations` — setores, unidades e localizações.
* `tickets` — chamados e atendimentos.
* `sla` — regras e controle de prazos.
* `catalog` — catálogo de serviços.
* `knowledge` — base de conhecimento.
* `assets` — inventário de ativos.
* `cmdb` — relacionamento entre ativos e serviços.
* `problems` — gestão de problemas.
* `changes` — gestão de mudanças.
* `contracts` — contratos, fornecedores e licenças.
* `reports` — relatórios e dashboards.
* `notifications` — e-mails e alertas.
* `audit` — logs e rastreabilidade.
* `integrations` — AD, e-mail, monitoramento e APIs.

## 23. Estrutura Inicial do Banco de Dados

Tabelas ou modelos principais:

* Usuários.
* Perfis.
* Permissões.
* Setores.
* Unidades.
* Localizações.
* Chamados.
* Tipos de chamado.
* Categorias.
* Subcategorias.
* Prioridades.
* Impactos.
* Urgências.
* Status.
* Comentários.
* Histórico.
* Anexos.
* Equipes.
* Técnicos.
* Regras de SLA.
* Serviços.
* Artigos da base de conhecimento.
* Ativos.
* Tipos de ativos.
* Fornecedores.
* Contratos.
* Licenças.
* Problemas.
* Mudanças.
* Aprovações.
* Logs de auditoria.

## 24. Regras de Negócio

* Todo chamado deve possuir número único.
* Todo chamado deve registrar data e hora de abertura.
* Todo chamado deve possuir solicitante.
* Toda alteração relevante deve ser registrada no histórico.
* O encerramento deve exigir solução aplicada.
* O usuário solicitante deve conseguir acompanhar seus chamados.
* O técnico deve poder registrar observações internas.
* Comentários internos não devem ser visíveis ao solicitante.
* Chamados não devem ser excluídos definitivamente.
* Chamados resolvidos podem ser reabertos dentro de prazo configurável.
* Chamados críticos devem gerar destaque visual e notificação.
* Chamados vencidos devem aparecer em painel específico.
* Solicitações sensíveis podem exigir aprovação.
* Ativos vinculados devem manter histórico de chamados.
* A base de conhecimento deve permitir artigos internos e públicos.
* Relatórios devem respeitar permissões de acesso.

## 25. Roadmap de Desenvolvimento

### Fase 1 — Base Profissional de Service Desk

* Login.
* Perfis de usuário.
* Setores.
* Equipes.
* Abertura de chamados.
* Listagem e filtros.
* Detalhes do chamado.
* Comentários.
* Anexos.
* Histórico.
* Status.
* Prioridade, impacto e urgência.
* Encerramento.
* Dashboard inicial.
* Relatórios básicos.

### Fase 2 — SLA, Notificações e Catálogo

* Regras de SLA.
* Controle de vencimento.
* Notificações por e-mail.
* Catálogo de serviços.
* Aprovações simples.
* Pesquisa de satisfação.
* Modelos de resposta.

### Fase 3 — Inventário e Base de Conhecimento

* Cadastro de ativos.
* Vinculação de ativos aos chamados.
* Histórico de manutenção.
* Base de conhecimento.
* Sugestão de artigos.
* Relatórios de ativos.

### Fase 4 — Integrações Corporativas

* Active Directory/LDAP.
* SMTP institucional.
* Importação CSV.
* API REST.
* Webhooks.
* Integração com monitoramento.

### Fase 5 — ITSM Avançado

* Gestão de problemas.
* Gestão de mudanças.
* CMDB.
* Contratos.
* Fornecedores.
* Licenças.
* Inventário automático.
* Agente de coleta.
* Indicadores avançados.

## 26. Meta Inicial de Desenvolvimento

A primeira meta deverá ser criar uma versão funcional, estável e organizada com foco em chamados, usuários, setores, equipes, histórico, anexos, dashboard e relatórios básicos.

Essa versão deverá evitar complexidade excessiva, mas já deverá ser estruturada com banco PostgreSQL, Docker, variáveis de ambiente, logs e separação modular, permitindo evolução segura para um sistema de Service Desk completo.
