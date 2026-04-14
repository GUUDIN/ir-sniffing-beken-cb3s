# Diagnostico de Captura IR no OpenBeken (Foco em Bits Nulos)

## 1. Objetivo
Este documento consolida as evidencias tecnicas sobre o comportamento de captura IR observado no CB3S com OpenBeken, com foco no problema de alto volume de eventos nulos (`UNKNOWN`, `0x0`, `Bits=0`).

## 2. Evidencias de codigo-fonte (OpenBeken)

### 2.1 Driver ativo e comandos de ajuste em runtime
No caminho de firmware com `IRremoteESP8266` (`driver/drv_ir_new.cpp`), existem comandos de ajuste direto para recepcao:
1. `IREnable [Str] [1or0]`
2. `IRParam [MinSize] [Noise Threshold]`

`IRParam` aplica, em runtime:
1. `setUnknownThreshold(kMinUnknownSize)`
2. `setTolerance(kTolerancePercentage)`

Valores padrao no proprio driver:
1. `kMinUnknownSize = 12`
2. `kTolerancePercentage = 25`

### 2.2 Buffer e timeout de captura
No `IRrecv` da biblioteca `IRremoteESP8266`:
1. Buffer padrao de captura: `kRawBuf = 1024`
2. Timeout padrao: `kTimeoutMs = 90`
3. Tolerancia padrao: `kTolerance = 25`
4. Threshold padrao de unknown na lib: `kUnknownThreshold = 6`

No driver OBK, o comentario em `drv_ir_new.cpp` confirma intencao de uso com buffer 1024 e timeout 90 ms.

### 2.3 Publicacao MQTT de IR
No caminho `drv_ir_new.cpp`, quando flags estao ativas:
1. Flag 14 publica string em topico `ir`.
2. Flag 22 publica JSON em `RESULT` com `IrReceived`.

Para diagnostico, o payload JSON do `RESULT` e o formato mais confiavel para parser.

Observacao relevante para codigos longos (AC): em alguns casos o driver publica no topico `.../ir` um formato reduzido com apenas dois campos, tipicamente:
1. `<proto_id_hex>,0x<estado_em_hex>`

Nesse formato nao existe campo explicito de `Bits`. Portanto, um backend que so aceite triplets (`proto,data,bits`) pode descartar precisamente os frames mais importantes.

## 3. Hipotese tecnica principal
O pipeline esta funcional, mas a base de dados estava misturando:
1. eventos validos,
2. eventos de ruide/unknown curto,
3. formatos textuais ambiguos de multiplos topicos.

Isso distorce a leitura de qualidade de captura e mascara os codigos validos raros.

## 4. Ajuste aplicado no backend local
Arquivo alterado: `server/app.py`.

Mudancas:
1. Parser sensivel ao topico.
2. Em `.../RESULT`, aceita preferencialmente JSON `IrReceived`.
3. Bloqueia parse heuristico em topicos nao IR.
4. Filtro opcional para capturas nulas (`Bits=0` com `0x0`).
5. Chave de ambiente para priorizar `RESULT` em vez de raw de `.../ir`.
6. Suporte ao payload reduzido de `.../ir` (dois campos) para AC (`proto_id_hex,0xSTATE`), inferindo `Bits` pelo tamanho do hex.
7. Classificacao de `PROTO_ID_*` como `unknown` e bloqueio de replay desse placeholder, pois `IRSend` espera nomes de protocolos (ex.: `NEC`, `RC5`), nao IDs numericos.

Objetivo do ajuste:
1. reduzir falso positivo no CSV,
2. medir qualidade real da recepcao,
3. separar problema de parser de problema de firmware/hardware.

## 5. Plano A/B recomendado (firmware)
Executar testes em janelas controladas, sempre com um unico controle por rodada.

### 5.1 Condicao fixa
1. Pinagem: `P7=IRRecv_nPup`, `P26=IRSend`.
2. Flags: 14, 15 e 22 ativas.
3. Backend em modo de priorizacao de `RESULT`.
4. CSV zerado antes de cada rodada.

### 5.2 Matriz de teste `IRParam`
1. Baseline: `IRParam 12 25`
2. Menos unknown curto: `IRParam 24 25`
3. Mais restritivo: `IRParam 40 25`
4. Match mais rigido: `IRParam 24 20`
5. Match mais permissivo: `IRParam 24 30`

### 5.3 Protocolo de coleta
Para cada configuracao:
1. Pressionar 30 vezes o mesmo botao (intervalo de 1 s a 2 s).
2. Repetir para 3 botoes diferentes do mesmo controle.
3. Repetir com o segundo controle.

## 6. Metricas de aceite
Para cada rodada:
1. `taxa_util = linhas_validas / linhas_totais`
2. `taxa_nula = linhas_(0x0, bits=0) / linhas_totais`
3. `estabilidade_assinatura = repeticoes_do_mesmo_codigo / total_do_botao`

Criterio minimo para considerar configuracao aceitavel:
1. `taxa_util >= 0.60`
2. `taxa_nula <= 0.30`
3. pelo menos um botao com assinatura estavel acima de `0.80`

## 7. Decisao tecnica apos A/B
1. Se `IRParam` elevar a taxa util de forma consistente, manter melhor configuracao e congelar baseline.
2. Se `IRParam` nao elevar taxa util de forma material, o gargalo provavel passa a ser camada fisica (sensor, alimentacao, ruido, angulo, distancia) ou diferenca de stack de firmware em relacao ao build antigo.
3. Se somente codigos curtos forem estaveis, mas frames longos nao aparecerem, priorizar caminho alternativo para AC (captura bruta dedicada e decoder especifico fora do OBK atual).
4. Se a necessidade for transmitir AC, tratar como requisito de arquitetura: o caminho `IRSend` do OpenBeken analisado bloqueia AC e, portanto, o envio tende a exigir outra solucao (outro firmware, outro dispositivo transmissor, ou um caminho de envio RAW que nao esta presente neste stack).
