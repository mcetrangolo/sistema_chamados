# Agente de Inventário

## Objetivo

O agente deve coletar informações dos computadores e enviar para a plataforma de forma segura e padronizada.

## Informações mínimas

- Hostname;
- Sistema operacional;
- Versão do sistema;
- CPU;
- Memória RAM;
- Disco;
- IP;
- MAC Address;
- Usuário logado;
- Fabricante;
- Modelo;
- Número de série;
- Placa-mãe;
- Softwares instalados;
- Data/hora da coleta.

## Informações futuras

- SMART dos discos;
- Temperatura;
- BitLocker;
- TPM;
- Secure Boot;
- Antivírus;
- Serviços;
- Processos;
- Logs relevantes;
- Monitores;
- Impressoras;
- Dispositivos USB.

## Requisitos do agente

- Ser leve;
- Funcionar em Windows 7 ou superior, quando possível;
- Registrar logs locais;
- Tratar erros de JSON;
- Reenviar dados em caso de falha;
- Permitir configuração via arquivo;
- Não coletar dados pessoais desnecessários;
- Comunicar-se com API segura.

## Boas práticas

- Nunca travar a máquina do usuário;
- Não consumir muitos recursos;
- Evitar dependências externas;
- Registrar versão do agente;
- Permitir atualização futura.
