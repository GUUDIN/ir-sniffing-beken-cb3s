# Operacao de Rede e Persistencia

## 1. Objetivo
Este guia fecha os pontos operacionais criticos para manter o sistema estavel no laboratorio:
1. IP fixo para o device OpenBeken.
2. Persistencia de dados fora de container.
3. Rotina simples de backup.

## 2. IP fixo para o CB3S

### 2.1 Dados do dispositivo
1. MAC atual observado: `C8:47:8C:00:00:00`.
2. Hostname observado: `ircontrol-lasdpc`.

### 2.2 Procedimento de reserva DHCP (roteador)
1. Abrir painel do roteador em DHCP ou LAN.
2. Procurar opcao `DHCP Reservation`, `Static Lease` ou equivalente.
3. Criar entrada com MAC `C8:47:8C:00:00:00`.
4. Definir IP fixo recomendado, por exemplo `192.168.0.130`.
5. Salvar e reiniciar o dispositivo CB3S.
6. Validar por ping e acesso web.

### 2.3 Validacao minima
Executar 2 ciclos de reboot e validar que o IP nao mudou.

Comandos de validacao:
```bash
ping -c 3 192.168.0.130
curl -I http://192.168.0.130
```

## 3. Persistencia fora de container

### 3.1 O que ja esta persistido
1. Capturas e perfis ja ficam no host em `server/data`.
2. O Mosquitto agora grava dados e logs no host:
   1. `runtime/mosquitto/data`
   2. `runtime/mosquitto/log`

### 3.2 Subir broker com persistencia
```bash
docker compose up -d mosquitto
```

### 3.3 Conferencia rapida
```bash
ls -la runtime/mosquitto/data runtime/mosquitto/log
```

## 4. Snapshot JSON para backup humano

### 4.1 Script
Arquivo: `scripts/export_ir_snapshot.py`.

### 4.2 Uso
```bash
python scripts/export_ir_snapshot.py
```

Saidas geradas em `server/data/snapshots`:
1. `ir_snapshot_latest.json`
2. `ir_snapshot_YYYYMMDD_HHMMSS.json`

## 5. Quando considerar NoSQL
No estado atual, CSV + snapshot JSON e suficiente para laboratorio porque:
1. O volume de dados e moderado.
2. O objetivo principal e engenharia reversa e validacao de replay.
3. O pipeline precisa de auditabilidade simples.

Migrar para banco (SQLite, Postgres, MongoDB) so passa a ser necessario quando:
1. houver multiusuario simultaneo;
2. houver necessidade de consultas complexas historicas;
3. houver retencao longa com crescimento alto de dados.
