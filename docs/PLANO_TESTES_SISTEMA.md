# Plano de Testes do Sistema IR

## 1. Objetivo
Executar baterias de teste repetiveis para validar captura e emulacao de codigos IR, com foco principal em ar-condicionado.

## 2. Pre-condicoes
1. Broker Mosquitto ativo.
2. Backend Flask ativo em `http://127.0.0.1:5050`.
3. OpenBeken online no MQTT.
4. Device com IP reservado no roteador.
5. Flags de IR ativas no OpenBeken (14 e 22).

## 3. Baterias de teste

### Bateria A - Sanidade de infraestrutura
Objetivo: garantir conectividade basica antes de testar IR.

Passos:
1. Verificar ping do device.
2. Verificar subscription de topicos MQTT.
3. Validar carregamento do dashboard e endpoint de monitor.

Criterio de aceite:
1. Sem perda de conexao durante 5 minutos.
2. Monitor MQTT recebendo eventos Rx e Tx.

### Bateria B - Captura de controle comum (TV)
Objetivo: validar pipeline rapido com protocolos curtos.

Passos:
1. Pressionar 5 vezes cada tecla: Power, Vol+, Vol-, Mute, Source.
2. Conferir entradas no dashboard e em `master_ir_codes.csv`.
3. Conferir consolidacao em `ir_command_profiles.csv`.

Criterio de aceite:
1. Pelo menos 4 teclas com assinatura estavel.
2. Taxa de ruido abaixo de 30%.

### Bateria C - Captura de ar-condicionado (principal)
Objetivo: capturar frames longos e estados completos.

Passos:
1. Usar sequencia fixa por ciclo:
   1. Power On
   2. Temp+
   3. Temp-
   4. Mode
   5. Fan
2. Repetir 5 ciclos completos.
3. Salvar log cru em `server/data/raw_runs`.
4. Rodar resumo:
```bash
python scripts/summarize_ir_log.py
```

Criterio de aceite:
1. Aparicao de candidatos longos no resumo.
2. Reducao consistente de UNKNOWN com `IRParam 24 20`.
3. Assinaturas repetiveis por funcao.

### Bateria D - Replay para alvo real
Objetivo: validar emissao em equipamento real, nao apenas LED.

Passos:
1. Selecionar 3 comandos estaveis no dashboard.
2. Disparar replay a partir da UI.
3. Confirmar resposta fisica do equipamento.
4. Repetir com variacao de repeticoes (1, 2, 3).

Criterio de aceite:
1. Pelo menos 2 comandos funcionando no alvo real.
2. Sem falha de publish MQTT no endpoint de replay.

### Bateria E - Regressao completa
Objetivo: garantir que mudancas de parser/UI nao quebraram fluxo principal.

Passos:
1. Executar baterias A, B, C e D em sequencia.
2. Limpar tabelas e repetir um mini ciclo de captura/replay.
3. Exportar snapshot JSON final.

Criterio de aceite:
1. Nenhum erro HTTP 5xx nos endpoints principais.
2. Captura e replay funcionando apos limpeza de tabela.

## 4. Evidencias obrigatorias por rodada
1. Print do painel com captura valida.
2. Print do monitor MQTT com evento de replay.
3. Arquivo de log cru da rodada.
4. Snapshot JSON final da sessao.

## 5. Comandos operacionais recomendados
```bash
# Broker
docker compose up -d mosquitto

# Backend
python server/app.py

# Validacao MQTT
mosquitto_sub -h localhost -t '#' -v

# Resumo de captura
python scripts/summarize_ir_log.py

# Snapshot JSON
python scripts/export_ir_snapshot.py
```
