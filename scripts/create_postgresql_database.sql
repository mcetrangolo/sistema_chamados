-- Execute este arquivo conectado como usuario administrador do PostgreSQL.
-- Ajuste a senha antes de rodar em producao.
--
-- Exemplo:
-- psql -U postgres -h localhost -f scripts/create_postgresql_database.sql

CREATE USER sistema_chamados WITH PASSWORD 'troque_esta_senha';

CREATE DATABASE sistema_chamados
    WITH
    OWNER = sistema_chamados
    ENCODING = 'UTF8'
    TEMPLATE = template0;

GRANT ALL PRIVILEGES ON DATABASE sistema_chamados TO sistema_chamados;
