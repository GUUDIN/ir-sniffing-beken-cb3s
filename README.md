# IR Sniffing - Beken CB3S

Projeto de engenharia reversa e automacao para captura e emulacao de sinais IR usando CB3S (BK7231N com OpenBeken), broker MQTT local e dashboard Flask.

## Objetivo principal
Capturar e reproduzir comandos de controle remoto, com foco em ar-condicionado, de forma confiavel e reproduzivel em laboratorio.

## Estado atual
1. Firmware OpenBeken validado no hardware.
2. Captura e replay funcionais no dashboard local.
3. Parser e perfilamento de comandos IR operacionais.
4. Persistencia em CSV e snapshot JSON operacional.

## Quick start
1. Subir broker MQTT:
```bash
docker compose up -d mosquitto
```
2. Rodar backend:
```bash
source .venv/bin/activate
python server/app.py
```
3. Abrir dashboard:
```text
http://127.0.0.1:5050
```

## Estrutura principal
1. `server/app.py`: backend Flask e ingestao MQTT.
2. `server/templates/index.html`: dashboard e controles de replay.
3. `server/data`: historico de capturas e perfis.
4. `docs`: documentacao tecnica e operacional.
5. `scripts`: utilitarios de resumo e snapshot.

## Documentacao recomendada
1. Arquitetura: `docs/ARQUITETURA_SISTEMA.md`
2. Rede e persistencia: `docs/OPERACAO_REDE_PERSISTENCIA.md`
3. Plano de testes: `docs/PLANO_TESTES_SISTEMA.md`
4. Diario OpenBeken: `docs/openbeken/DIARIO_PASSO_A_PASSO.md`

## Prioridades restantes
1. Validar replay em alvo real de ar-condicionado.
2. Reservar IP fixo no roteador para o device.
3. Executar bateria de testes completa e registrar evidencias.
