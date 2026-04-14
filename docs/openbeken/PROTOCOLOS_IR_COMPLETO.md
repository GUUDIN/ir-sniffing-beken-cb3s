# Guia Completo de Protocolos IR (base tecnica para o laboratorio)

## 1. Objetivo
Este documento consolida a base tecnica necessaria para entender, capturar, classificar e reaproveitar comandos IR no contexto do modulo CB3S com OpenBeken.

Escopo pratico:
1. Entender por que existem varios protocolos IR.
2. Relacionar os protocolos mais usados com seus parametros essenciais.
3. Definir um metodo replicavel para catalogar comandos no laboratorio.
4. Reduzir ambiguidade durante analise de eventos UNKNOWN e capturas com Bits=0.

## 2. Conceitos essenciais

### 2.1 Portadora, mark e space
1. O LED IR nao transmite nivel logico direto; ele transmite rajadas em uma frequencia de portadora (tipicamente 36 kHz, 38 kHz ou 40 kHz).
2. Mark: periodo com rajada da portadora.
3. Space: periodo sem rajada.
4. O receptor demodulado entrega apenas a envoltoria mark/space para o firmware decodificar.

### 2.2 Formas de codificacao mais comuns
1. Pulse Distance: pulso com largura fixa; o que muda e o espaco.
2. Pulse Width: espaco fixo; o que muda e a largura do pulso.
3. Bi-phase (Manchester): transicao no meio do bit define 0/1.
4. Pulse Position: posicao temporal do pulso codifica o simbolo.

### 2.3 Estrutura logica de um frame IR
Em geral, um frame tem:
1. Preambulo (leader/start) para sincronismo e ajuste de AGC.
2. Campo de endereco (device/family).
3. Campo de comando (tecla).
4. Bits de redundancia (inverso, CRC, toggle) dependendo do protocolo.
5. Politica de repeticao enquanto o botao permanece pressionado.

## 3. Protocolos priorizados para este projeto

Tabela de referencia rapida (valores tipicos):

| Protocolo | Codificacao | Portadora tipica | Estrutura tipica | Ordem de bits | Repeticao tipica |
| --- | --- | --- | --- | --- | --- |
| NEC | Pulse Distance | 38 kHz | 32 bits (addr + addr_inv + cmd + cmd_inv) | LSB first | Frame de repeticao dedicado ~110 ms |
| Extended NEC | Pulse Distance | 38 kHz | 16 bits addr + 8 bits cmd + cmd_inv | LSB first | Similar ao NEC |
| RC5 | Bi-phase | 36 kHz | 14 bits (2 start + toggle + 5 addr + 6 cmd) | MSB first | Repeticao ~114 ms, toggle diferencia novo aperto |
| RC6 (Mode 0) | Bi-phase | 36 kHz | Header + trailer(toggle) + 8 addr + 8 cmd | MSB first | Repeticao dependente do emissor |
| Sony SIRC 12/15/20 | Pulse Width | 40 kHz | 7 cmd + 5/8/13 bits adicionais (addr/ext) | LSB first | Repeticao ~45 ms |
| JVC | Pulse Distance | 38 kHz | 8 addr + 8 cmd | LSB first | Repeticao 50-60 ms |
| RECS-80 | Pulse Distance | 38 kHz | Sub-sistema + comando + toggle | MSB first | Repeticao ~121.5 ms |
| RCMM | Pulse Position | 36 kHz | 12 ou 24 bits, 2 bits por simbolo temporal | MSB first | Repeticao ~27.8 ms |
| Kaseikyo / Panasonic (familia) | Variantes de pulse distance | 36-37 kHz (tipico) | Frames longos (familia 48 bits e variantes) | Variavel por implementacao | Depende do fabricante |
| Samsung (familia) | Predominio de pulse distance | 38 kHz (tipico) | Variantes 32/48 bits e derivados | Variavel por implementacao | Depende do fabricante |

## 4. O que chega no OpenBeken e como interpretar

### 4.1 Publicacoes relevantes no OBK
Com as flags 14/22 ativas, o OBK pode publicar:
1. RAW textual de IR (flag 14).
2. JSON estilo Tasmota em RESULT (flag 22), com campos equivalentes a Protocol, Bits e Data.

### 4.2 Leitura operacional dos campos
1. Protocol: nome da familia reconhecida pelo decoder.
2. Bits: tamanho logico detectado.
3. Data/Hex: payload da tecla.

### 4.3 Regras praticas para qualidade de captura
1. `Bits = 0` com `Hex = 0x0`: quase sempre ruido, reflexo, interferencia optica ou borda invalida.
2. `Protocol = UNKNOWN` com `Bits > 0` e `Hex != 0x0`: sinal real detectado, mas nao classificado por assinatura conhecida.
3. Mesmo botao deve gerar valor estavel em multiplas repeticoes para ser considerado comando valido de catalogo.

## 5. Por que aparecem muitos UNKNOWN e Bits=0

Causas frequentes:
1. Receptor com ruido de alimentacao (desacoplamento insuficiente).
2. Forte iluminacao ambiente (sol direto, lampada com flicker).
3. Distancia/angulo ruins entre controle e receptor.
4. Ganho e filtro do receptor inadequados para o padrao temporal observado.
5. Pino configurado sem pull-up em condicao de maior susceptibilidade.

Mitigacoes de bancada:
1. Testar `IRRecv` e `IRRecv_nPup` e escolher o que gera menor falso positivo.
2. Garantir aterramento comum e trilha curta no sinal do receptor.
3. Melhorar desacoplamento local do receptor (capacitor proximo ao VCC/GND).
4. Executar captura em ambiente com menor iluminacao infravermelha parasita.
5. Coletar varias amostras por tecla e aplicar criterio de maioria.

## 6. Metodo replicavel de catalogacao (versao completa)

### 6.1 Preparacao
1. Confirmar pinagem: P7 como IRRecv (ou IRRecv_nPup apos teste A/B) e P26 como IRSend.
2. Manter flags 14, 15 e 22 ativas para ampliar telemetria.
3. Validar conectividade MQTT estavel antes da sessao.

### 6.2 Coleta por tecla
Para cada tecla alvo:
1. Pressionar e soltar 5 vezes com intervalo de 1 s.
2. Pressionar e segurar 1 vez por 2 s (captura de repeticao).
3. Registrar todos os eventos com timestamp.

### 6.3 Criterio de aceite da tecla
Aceitar comando como valido quando:
1. Pelo menos 3 capturas possuem `Bits > 0`.
2. Payload principal (Hex) se repete de forma consistente.
3. Repeticao longa nao muda endereco/comando principal, apenas padrao de repeat.

### 6.4 Classificacao final
1. Classe A: protocolo conhecido + bits consistentes.
2. Classe B: UNKNOWN com bits validos e assinatura estavel.
3. Classe C: ruido (Bits=0 predominante ou hex instavel).

## 7. Base minima de protocolos que o laboratorio deve reconhecer
Para cobertura inicial de eletronicos de consumo:
1. NEC / Extended NEC.
2. RC5 / RC6.
3. Sony SIRC.
4. JVC.
5. Samsung (familia).
6. Panasonic/Kaseikyo (familia).
7. LG e Denon/Sharp (familias comuns em bibliotecas modernas).

Observacao: para cobertura ampla (incluindo ar-condicionado e protocolos longos), usar bibliotecas multi-protocolo com base de assinaturas extensa, como IRremoteESP8266 e IRMP.

## 8. Referencias tecnicas
1. SB-Projects, teoria geral de IR: https://www.sbprojects.net/knowledge/ir/index.php
2. SB-Projects, NEC: https://www.sbprojects.net/knowledge/ir/nec.php
3. SB-Projects, RC5: https://www.sbprojects.net/knowledge/ir/rc5.php
4. SB-Projects, RC6: https://www.sbprojects.net/knowledge/ir/rc6.php
5. SB-Projects, Sony SIRC: https://www.sbprojects.net/knowledge/ir/sirc.php
6. SB-Projects, JVC: https://www.sbprojects.net/knowledge/ir/jvc.php
7. SB-Projects, RCMM: https://www.sbprojects.net/knowledge/ir/rcmm.php
8. SB-Projects, RECS-80: https://www.sbprojects.net/knowledge/ir/recs80.php
9. Vishay, Data Formats for IR Remote Control (Doc 80071): https://www.vishay.com/docs/80071/dataform.pdf
10. Arduino-IRremote (protocolos suportados e troubleshooting): https://github.com/Arduino-IRremote/Arduino-IRremote
11. IRremoteESP8266 (base extensa de protocolos): https://github.com/crankyoldgit/IRremoteESP8266
12. IRMP (visao multi-protocolo e metodos de codificacao): https://www.mikrocontroller.net/articles/IRMP_-_english
13. Referencia contextual indicada pela equipe (leitura manual): https://www.reddit.com/r/homeautomation/comments/kqaggm/how_does_the_remote_control_work_explained/

Nota sobre a referencia do Reddit: o acesso automatico por crawler foi bloqueado pelo robots.txt do dominio. O link permanece listado porque foi uma fonte de direcao conceitual apontada pela equipe.