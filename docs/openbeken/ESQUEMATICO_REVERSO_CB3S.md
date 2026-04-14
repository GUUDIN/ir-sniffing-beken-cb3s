# Esquematico Reverso (Parcial) - Placa com CB3S

Data base: 2026-04-13
Status: parcial, com bloco IR mapeado por continuidade

## 1. Resumo funcional
1. Alimentacao principal em 5V.
2. Regulacao local para 3V3 por HL1117-3.3.
3. Modulo CB3S (BK7231N) como nucleo de controle Wi-Fi/IR.
4. Bloco IR RX com receptor de 3 pinos alimentado em 3V3.
5. Bloco IR TX com driver discreto (22ES) acionando 2 pares de LEDs IR.

## 2. Componentes identificados
1. Ureg: HL1117-3.3 (marcacao: HL1117 33 2422)
2. Qtx: 22ES (encapsulamento SOT-23, 1 pino superior + 2 inferiores)
3. Dtx1, Dtx2: LEDs IR (marcacao IR87), em pares na rede de emissao
4. Uir: receptor IR 3 pinos
5. Rtx_pd: 10k (pull-down no controle do Qtx)
6. Rtx_in: 100 ohm (entre GPIO e controle do Qtx)
7. Rrx_vcc: resistor em serie entre 3V3 e VCC do receptor IR (estimado ~100 ohm)

## 3. Netlist reverso (confianca alta)
1. +5V -> entrada de Ureg (HL1117-3.3)
2. GND -> referencia comum da placa
3. +3V3 <- saida de Ureg
4. CB3S P26 -> Rtx_in (100 ohm) -> no de controle de Qtx
5. no de controle de Qtx -> Rtx_pd (10k) -> GND
6. Qtx pino inferior direito -> GND
7. Qtx pino superior isolado -> rede dos LEDs IR (Dtx1/Dtx2)
8. Uir pino GND -> GND
9. Uir pino VCC <- +3V3 via Rrx_vcc
10. Uir pino OUT -> CB3S P7

## 4. Pinagem funcional OBK (derivada do hardware)
1. P7  -> IRRecv
2. P26 -> IRSend

## 5. Analise da medicao no resistor de VCC do receptor IR
Medicao fornecida:
1. Queda em Rrx_vcc: 22.7 mV
2. Rrx_vcc estimado: 100 ohm

Corrente estimada:
1. I = V / R = 22.7 mV / 100 ohm = 0.227 mA

Interpretacao:
1. Corrente de repouso baixa, plausivel para receptor IR em idle.
2. Resistor em serie melhora imunidade de alimentacao local e reduz injecao de ruido.
3. Com capacitor local, forma filtro RC para o receptor.

## 6. Esquematico textual (bloco IR)

5V ----> [HL1117-3.3] ----> 3V3 ------------------------+
                                                         |
                                                         +--> [Rrx_vcc ~100] --> Uir VCC
GND -----------------------------------------------------> Uir GND
Uir OUT --------------------------------------------------> CB3S P7 (IRRecv)

CB3S P26 (IRSend) --> [Rtx_in 100] --> no_ctrl ----> Qtx (22ES)
                                         |
                                         +--> [Rtx_pd 10k] --> GND

Qtx output ---------------------------------------------> rede LEDs IR (IR87 x2 pares)
Qtx GND pin --------------------------------------------> GND

## 7. Itens pendentes
1. Confirmar polaridade detalhada de cada LED IR no ramo de emissao.
2. Validar emissao IR em alvo externo (equipamento final) apos fechamento da etapa de decodificacao AC.

Itens ja validados:
1. Captura IR em runtime no MQTT com P7 configurado como IRRecv_nPup.
2. Emissao IR em runtime com P26 (comando blink_ir no OpenBeken com retorno OK).
