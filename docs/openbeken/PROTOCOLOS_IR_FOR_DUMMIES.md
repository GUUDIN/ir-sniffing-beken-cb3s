# Protocolos IR For Dummies (replicacao rapida no laboratorio)

## 1. O que voce precisa saber em 1 minuto
1. Controle remoto IR envia pulsos de luz com um padrao.
2. Esse padrao vira `Protocol`, `Bits` e `Hex` no OpenBeken.
3. Nem todo pulso vira comando valido. Muito `Bits=0` costuma ser ruido.

## 2. Como ler o resultado sem complicacao
Quando chegar algo no MQTT/CSV, olhe esta regra:
1. `Bits > 0` e `Hex != 0x0`: bom sinal, captura util.
2. `Bits = 0` e `Hex = 0x0`: normalmente ruido, ignore.
3. `Protocol = UNKNOWN` com `Bits > 0`: comando real, so nao classificado.

## 3. Receita de bolo para cadastrar uma tecla
Para cada tecla do controle:
1. Aperte e solte 5 vezes.
2. Depois segure 1 vez por 2 segundos.
3. No final, escolha o valor `Hex` que mais repetiu com `Bits > 0`.

Se nao repetir nada confiavel:
1. Mude angulo/distancia do controle (30 cm a 80 cm).
2. Reduza luz forte no ambiente.
3. Teste `IRRecv` no lugar de `IRRecv_nPup` (ou vice-versa) e compare.

## 4. Quais protocolos importam primeiro
Para a maioria dos aparelhos do laboratorio, estes ja resolvem muita coisa:
1. NEC
2. RC5
3. RC6
4. Sony SIRC
5. JVC
6. Samsung (familia)
7. Panasonic/Kaseikyo (familia)

## 5. Checklist rapido antes de testar
1. P7 configurado como IRRecv (ou IRRecv_nPup apos teste A/B).
2. P26 configurado como IRSend.
3. Flags 14, 15 e 22 ativas.
4. MQTT conectado e recebendo mensagens.

## 6. Exemplo de decisao rapida
Caso A:
1. `Protocol=NEC`, `Bits=32`, `Hex=0x20DF10EF` repetiu varias vezes.
2. Resultado: salvar como tecla valida.

Caso B:
1. `Protocol=UNKNOWN`, `Bits=32`, `Hex=0x60D49407` apareceu varias vezes na mesma tecla.
2. Resultado: salvar como tecla valida (classe UNKNOWN estavel).

Caso C:
1. `Protocol=UNKNOWN`, `Bits=0`, `Hex=0x0` em rajada.
2. Resultado: ignorar como ruido.

## 7. Regras do laboratorio para nao se perder
1. Nunca validar tecla com uma unica leitura.
2. Sempre coletar repeticoes e usar maioria.
3. Separar comandos em tres classes: conhecida, unknown estavel e ruido.
4. Documentar data, controle usado e condicoes do ambiente.

## 8. Onde aprofundar (quando precisar)
1. Guia completo interno: `docs/openbeken/PROTOCOLOS_IR_COMPLETO.md`
2. Teoria geral: https://www.sbprojects.net/knowledge/ir/index.php
3. Protocolos e timings: https://www.sbprojects.net/knowledge/ir/
4. Base extensa de suporte: https://github.com/Arduino-IRremote/Arduino-IRremote
5. Referencia contextual indicada pela equipe: https://www.reddit.com/r/homeautomation/comments/kqaggm/how_does_the_remote_control_work_explained/