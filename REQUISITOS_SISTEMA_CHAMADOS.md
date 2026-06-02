# Requisitos do Sistema de Controle de Chamados de TI

## 1. Objetivo do Sistema

Desenvolver um sistema web para controle dos atendimentos e atividades realizadas pelo setor de TI, permitindo registrar, acompanhar, priorizar e documentar chamados técnicos.

O sistema deve iniciar com um módulo simples de chamados, mas ser estruturado de forma modular para permitir futuras integrações com inventário de rede, controle de equipamentos, fluxo de processos, BPM, relatórios gerenciais e outros módulos administrativos.

## 2. Problema a Ser Resolvido

Atualmente, os atendimentos de TI são realizados sem um controle centralizado, o que dificulta:

- Registro dos serviços executados.
- Acompanhamento das demandas abertas.
- Identificação de demandas recorrentes.
- Comprovação dos atendimentos realizados.
- Geração de relatórios de produtividade.
- Planejamento de melhorias na infraestrutura.

## 3. Usuários do Sistema

### 3.1 Administrador

Usuário com acesso total ao sistema.

Permissões:

- Cadastrar usuários.
- Cadastrar setores.
- Gerenciar categorias de chamados.
- Alterar status dos chamados.
- Gerar relatórios.
- Acessar todos os chamados.

### 3.2 Técnico de TI

Usuário responsável pelo atendimento dos chamados.

Permissões:

- Visualizar chamados atribuídos.
- Alterar status dos chamados.
- Registrar andamento do atendimento.
- Inserir solução aplicada.
- Vincular equipamento ao chamado.
- Encerrar chamado.

### 3.3 Usuário Solicitante

Servidor ou colaborador que abre o chamado.

Permissões:

- Abrir chamado.
- Acompanhar andamento.
- Responder solicitações do técnico.
- Avaliar atendimento, caso a funcionalidade seja implementada.

## 4. Módulo Inicial: Chamados de TI

### 4.1 Cadastro de Chamado

O sistema deve permitir o cadastro de chamados contendo:

- Número do chamado.
- Data e hora de abertura.
- Nome do solicitante.
- Setor.
- Telefone ou ramal.
- E-mail.
- Categoria do problema.
- Prioridade.
- Descrição do problema.
- Anexos, se necessário.
- Status.
- Técnico responsável.
- Data de conclusão.
- Solução aplicada.

## 5. Status dos Chamados

Os chamados podem possuir os seguintes status:

- Aberto.
- Em análise.
- Em atendimento.
- Aguardando usuário.
- Aguardando fornecedor.
- Resolvido.
- Encerrado.
- Cancelado.

## 6. Prioridade dos Chamados

O sistema deve permitir classificar os chamados por prioridade:

- Baixa.
- Média.
- Alta.
- Crítica.

Critérios sugeridos:

- **Baixa:** solicitação simples, sem impacto direto no trabalho.
- **Média:** problema que afeta um usuário, mas possui alternativa temporária.
- **Alta:** problema que afeta um setor ou atividade importante.
- **Crítica:** problema que paralisa serviço essencial ou vários usuários.

## 7. Categorias Iniciais

Categorias sugeridas:

- Computador.
- Impressora.
- Internet.
- Rede.
- Sistema.
- E-mail.
- Telefonia.
- Acesso de usuário.
- Instalação de software.
- Manutenção preventiva.
- Outros.

## 8. Funcionalidades Essenciais da Primeira Versão

A primeira versão do sistema deve conter:

- Login de usuários.
- Cadastro de usuários.
- Cadastro de setores.
- Abertura de chamados.
- Listagem de chamados.
- Filtro por status, setor, prioridade e técnico.
- Tela de detalhes do chamado.
- Registro de andamento.
- Encerramento do chamado.
- Relatório simples de chamados por período.
- Relatório por técnico.
- Relatório por setor.
- Relatório por categoria.

## 9. Funcionalidades Futuras

O sistema deve ser planejado para receber futuramente os seguintes módulos.

### 9.1 Inventário de Equipamentos

Permitir cadastrar e controlar:

- Computadores.
- Notebooks.
- Impressoras.
- Switches.
- Roteadores.
- Servidores.
- Nobreaks.
- Telefones IP.
- Monitores.
- Periféricos.

Cada equipamento poderá ser vinculado a um chamado.

### 9.2 Inventário de Rede

Permitir registrar:

- IP.
- Hostname.
- MAC address.
- Setor.
- Usuário responsável.
- Sistema operacional.
- Status do equipamento.
- Histórico de manutenção.

### 9.3 Fluxo de Processos / BPM

Permitir criar fluxos internos, como:

- Solicitação de novo usuário.
- Solicitação de equipamento.
- Troca de setor.
- Desligamento de servidor.
- Aquisição de equipamento.
- Autorização de acesso.
- Manutenção programada.

### 9.4 Base de Conhecimento

Criar uma base com soluções recorrentes, tutoriais e procedimentos internos.

### 9.5 Dashboard Gerencial

Exibir indicadores como:

- Chamados abertos.
- Chamados concluídos.
- Chamados atrasados.
- Tempo médio de atendimento.
- Categorias mais recorrentes.
- Setores com maior volume de chamados.
- Produtividade por técnico.

## 10. Sugestão de Tecnologias

### Backend

- Python com Django ou FastAPI.

### Frontend

- HTML, CSS e JavaScript.
- React futuramente, caso o sistema evolua para uma interface mais dinâmica.

### Banco de Dados

- PostgreSQL.
- MySQL ou MariaDB como alternativas.

### Ambiente

- Sistema web local ou intranet.
- Possibilidade futura de acesso externo seguro via VPN.

## 11. Estrutura Inicial do Banco de Dados

Tabelas sugeridas:

- `usuarios`
- `setores`
- `chamados`
- `categorias`
- `prioridades`
- `status_chamado`
- `historico_chamado`
- `equipamentos`
- `anexos`
- `comentarios`

## 12. Regras Básicas

- Todo chamado deve possuir número único.
- Todo chamado deve registrar data e hora de abertura.
- Toda alteração de status deve ser registrada no histórico.
- O encerramento do chamado deve exigir descrição da solução aplicada.
- O usuário solicitante deve conseguir acompanhar o andamento.
- O técnico deve conseguir registrar observações internas.
- Chamados não devem ser apagados definitivamente, apenas cancelados ou arquivados.

## 13. Primeira Meta de Desenvolvimento

Criar um MVP com as seguintes telas:

- Tela de login.
- Painel inicial.
- Cadastro de usuário.
- Cadastro de setor.
- Abertura de chamado.
- Listagem de chamados.
- Detalhes do chamado.
- Atualização de status.
- Encerramento do chamado.
- Relatório simples.

## 14. Observações para Desenvolvimento com IA

- O sistema deve ser desenvolvido de forma modular, permitindo expansão futura.
- A primeira versão deve priorizar simplicidade, organização do código e funcionamento básico dos chamados.
- Evitar criar funcionalidades complexas no início.
- Priorizar uma base sólida para futuras integrações com inventário, BPM, dashboards e relatórios.
