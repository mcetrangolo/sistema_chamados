# Modelo de Dados

## Entidades principais

### Usuario

Representa usuários do sistema e usuários finais.

Campos sugeridos:

- id;
- nome;
- email;
- login;
- setor_id;
- perfil_id;
- ativo;
- ultimo_acesso;
- criado_em;
- atualizado_em.

### Setor

Representa setores/departamentos da organização.

Campos sugeridos:

- id;
- nome;
- sigla;
- responsavel;
- ativo.

### Ativo

Representa qualquer item de TI controlado pela plataforma.

Campos sugeridos:

- id;
- tipo;
- hostname;
- patrimonio;
- fabricante;
- modelo;
- numero_serie;
- setor_id;
- usuario_responsavel_id;
- status;
- localizacao;
- data_aquisicao;
- garantia_fim;
- criado_em;
- atualizado_em.

### Computador

Especialização de ativo.

Campos sugeridos:

- ativo_id;
- sistema_operacional;
- versao_so;
- cpu;
- memoria_total;
- disco_total;
- ip;
- mac;
- dominio;
- ultimo_usuario;
- ultima_coleta.

### SoftwareInstalado

- id;
- ativo_id;
- nome;
- versao;
- fabricante;
- data_instalacao;
- coletado_em.

### Chamado

- id;
- numero;
- titulo;
- descricao;
- solicitante_id;
- tecnico_id;
- setor_id;
- ativo_id;
- categoria_id;
- prioridade;
- status;
- criado_em;
- atualizado_em;
- encerrado_em.

### ComentarioChamado

- id;
- chamado_id;
- autor_id;
- texto;
- publico;
- criado_em.

### ArtigoConhecimento

- id;
- titulo;
- conteudo;
- categoria_id;
- publicado;
- criado_por;
- atualizado_por;
- criado_em;
- atualizado_em.

## Relacionamentos importantes

- Um usuário pertence a um setor.
- Um ativo pode estar vinculado a um setor.
- Um ativo pode estar vinculado a um usuário responsável.
- Um chamado pode estar vinculado a um ativo.
- Um chamado pode ter vários comentários.
- Um artigo pode ser relacionado a chamados recorrentes.
