# Arquitetura do Sistema - Sitezinho Local IR Sniffing

## 1. Visão Geral
Este documento descreve a arquitetura de software desenvolvida para capturar, processar, armazenar e retransmitir sinais de infravermelho (IR) utilizando o stack **OpenBeken + MQTT + Flask**.

## 2. Fluxo de Dados

### 2.1 Captura (Ingestão)
1. O hardware (CB3S) detecta um sinal IR.
2. O OpenBeken publica o sinal no tópico MQTT `stat/obkCB3S/RESULT` (formato JSON) ou `obkCB3S/ir` (formato raw string).
3. O servidor Flask (`app.py`) assina esses tópicos via um thread dedicado (`paho-mqtt`).

### 2.2 Processamento (Backend - `app.py`)
O backend realiza as seguintes etapas críticas:
* **Filtro de Ruído**: Ignora eventos com `Bits: 0` ou códigos hexadecimais zerados (`0x0`).
* **Normalização**: Converte diferentes formatos de hex (ex: remove `0x`, padroniza maiúsculas).
* **Criação de Assinaturas (Signatures)**: Gera uma chave única baseada em `Protocolo + Bits + Hexadecimal` para agrupar comandos repetidos.
* **Classificação de Classe**: Diferencia comandos de "Controle Remoto Comum" (TV/DVD) de "Estado Completo" (Ar Condicionado).
* **Gerador de Replay**: Constrói automaticamente o comando `IRSend` compatível com a API do OpenBeken para que o usuário possa reemitir o sinal com um clique.

### 2.3 Persistência
Os dados são salvos em formato CSV na pasta `server/data/`:
* `master_ir_codes.csv`: Log histórico de todas as capturas válidas.
* `ir_command_profiles.csv`: Catálogo consolidado de comandos únicos (perfis), facilitando a identificação semântica (ex: "Samsung TV Power").

## 3. Interface do Usuário (Frontend - `index.html`)
A interface web é construída com **HTML5/CSS3/JavaScript (vanilla)** e oferece:
* **Monitor em Tempo Real**: Lista os últimos sinais capturados via WebSockets ou polling.
* **Dashboard de Perfis**: Permite dar nomes amigáveis (tags semânticas) aos códigos hexadecimais capturados.
* **Controle de Replay**: Botões interativos para disparar comandos de infravermelho de volta para o dispositivo.
* **Filtros Avançados**: Opção de esconder ruídos `UNKNOWN` ou frames de 0 bits.

## 4. Tecnologias Utilizadas
* **Linguagem**: Python 3.12+
* **Framework Web**: Flask
* **Processamento de Dados**: Pandas
* **Protocolo de Comunicação**: MQTT (Eclipse Mosquitto)
* **Firmware IoT**: OpenBeken (baseado no SDK Beken BK7231N)

## 5. Como Executar o Servidor
1. Ative o ambiente virtual: `source .venv/bin/activate`
2. Instale as dependências: `pip install -r server/requirements.txt`
3. Execute o app: `python server/app.py`
4. Acesse: `http://localhost:5050`
