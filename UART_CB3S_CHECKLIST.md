# Checklist Executavel - UART CB3S (BK7231N)

Objetivo: confirmar comunicacao serial de bootlog antes de flashing.

## Pre-condicoes

1. FTDI em nivel logico 3.3V.
2. CB3S alimentado em 3.3V estavel.
3. GND comum entre CB3S e FTDI.
4. FTDI TX desconectado para modo sniff puro.

## Comando padrao de sniff (RX-only, 12s)

Use exatamente este comando em cada teste:

```bash
"/Users/pedro/development/IC - LASDPC/IR Sniffing - Beken cb3s/.venv/bin/python" - <<'PY'
import serial, time, sys
port='/dev/cu.usbserial-00000000'
baud=115200
try:
    ser=serial.Serial(port, baud, timeout=0.2)
except Exception as e:
    print(f'[sniff] open failed: {e}')
    sys.exit(2)
start=time.time(); total=0; nonzero=0; chunks=0
print(f'[sniff] listening on {port} @{baud} for 12s (RX-only)...')
while time.time()-start<12:
    b=ser.read(256)
    if b:
        chunks += 1
        total += len(b)
        nonzero += sum(1 for x in b if x != 0)
        hx=' '.join(f'{x:02x}' for x in b)
        txt=b.decode('utf-8','replace').replace('\r','\\r').replace('\n','\\n')
        print(f'[rx] {len(b)} bytes | hex={hx} | txt={txt}')
ser.close()
print(f'[sniff] summary total={total} nonzero={nonzero} chunks={chunks}')
PY
```

## Fluxo de decisao (passo a passo)

### Passo 1 - Porta FTDI

1. Rode: `ls -l /dev/cu.usbserial*`
2. Se nao aparecer porta: problema de cabo/driver/FTDI.
3. Se aparecer, continue.

### Passo 2 - Porta livre

1. Rode: `lsof | grep usbserial`
2. Se houver processo ocupando, feche/mate e repita.
3. Se livre, continue.

### Passo 3 - Validar FTDI com loopback

1. Curte FTDI TX com FTDI RX.
2. Rode o script [scripts/test_serial.py](scripts/test_serial.py).
3. Se ecoar dados, FTDI OK.
4. Se nao ecoar, pare e corrija FTDI/pinos/cabo.

### Passo 4 - Sniff puro no TX1

1. Remova loopback.
2. Ligue somente:
   - CB3S GND -> FTDI GND
   - CB3S P11 (TX1) -> FTDI RX
3. Power-cycle CB3S durante os 12s de sniff.
4. Interpretacao:
   - `nonzero > 0` e bursts repetiveis: candidato forte a TX de log.
   - so zeros/nenhum byte: provavelmente pino errado ou sem log.

### Passo 5 - Sniff puro no TX2

1. Mantenha GND comum.
2. Troque apenas o fio de sinal para CB3S P0 (TX2) -> FTDI RX.
3. Repita comando de sniff e power-cycle.
4. Interpretacao igual ao passo 4.

### Passo 6 - Baud alternativo

1. Se houver bytes estranhos (nao legiveis), repita trocando `baud=9600`.
2. Compare `nonzero` e estabilidade.
3. Escolha baud/pino com maior volume consistente de bytes nao-zero.

### Passo 7 - Reset por CEN

1. Com sniff rodando, curto CEN -> GND por 1 segundo e solte.
2. Esperado: burst imediato de bytes na soltura.
3. Se LED pisca mas sem bytes, ainda nao esta no TX real.

## Criterios de sucesso

1. Aparecem linhas/bytes em todo ciclo de reset/power-cycle.
2. `nonzero` aumenta de forma consistente.
3. O padrao se repete no mesmo pino e baud.

## Criterios de falha

1. `summary total=0 nonzero=0 chunks=0` apos varios ciclos.
2. Apenas bytes esporadicos isolados (`00`, `03`, etc.) sem padrao de boot.
3. A placa deixa de bootar ao conectar o fio de RX (indicando contencao/pino indevido).

## Acao final apos sucesso

1. Fixar pino e baud validados para logs.
2. So depois conectar FTDI TX -> CB3S RX1 (P10) para etapa de flashing.
3. Manter reset por CEN conforme guia CB3S durante inicio do flash.
