# Relatorio Completo (For Dummies)
## Engenharia Reversa de Placa com Tuya CB3S (BK7231N)

## 1. Objetivo
Este documento explica, de forma didatica e replicavel, como foi feito o processo completo de engenharia reversa e acesso a memoria de uma placa com modulo Tuya CB3S (chip BK7231N), ate a gravacao do OpenBeken com seguranca.

A ideia e simples:
1. Entender o hardware e os sinais.
2. Confirmar comunicacao serial.
3. Entrar no bootloader.
4. Fazer backup completo da flash (antes de gravar qualquer coisa).
5. Gravar firmware no endereco correto.

## 2. Visao Geral Rapida
Se voce quer o resumo em 30 segundos:
1. FTDI em 3.3 V, GND comum.
2. RXD/TXD reais do FTDI (nao usar RXL/TXL para dados).
3. CEN para reset (pulso em GND para reiniciar e abrir janela de bootloader).
4. Backup da flash em modo leitura.
5. Validacao por hash (MD5) em leituras repetidas.
6. Gravacao do OpenBeken com ltchiptool usando offset auto-detectado (0x11000 para app UA).

## 3. Hardware e Ligacoes

### 3.1 Itens usados
1. Placa com CB3S (BK7231N).
2. Adaptador USB-TTL (FTDI).
3. Fonte 3.3 V estavel.
4. Cabos curtos e GND comum.

### 3.2 Ligacao correta para bootloader/flash
1. FTDI RXD -> TX do CB3S.
2. FTDI TXD -> RX do CB3S.
3. FTDI GND -> GND da placa.
4. CEN acessivel para reset manual (CEN -> GND por ~1 segundo e soltar).

### 3.3 Observacoes importantes
1. Em algumas placas de interface, os pads ja vem "cruzados" internamente.
2. Nome do pad pode confundir: pad "RX" da interface pode estar ligado no TX do CB3S.
3. Medicoes de tensao ajudaram no diagnostico:
   - Linha em ~3.3 V em idle indica comportamento esperado de UART TTL.
   - Linha perto de 4 V indica cuidado extra (possivel dominio de tensao diferente na placa).

## 4. Conceitos Essenciais (sem misterio)

### 4.1 O que e bootloader
Bootloader e um programa pequeno que roda logo apos reset/power-on. Ele:
1. Inicializa o minimo do chip.
2. Permite comandos de leitura/escrita da flash pela UART.
3. Depois entrega execucao para o firmware principal (app).

### 4.2 Por que CEN foi tao importante
CEN e reset do chip. Quando CEN vai para GND e volta, o chip reinicia. Isso cria a "janela" de comunicacao com bootloader. Sem reset no momento certo, o flasher pode nao sincronizar.

### 4.3 Por que apareciam bytes estranhos no sniff
Durante a fase de diagnostico apareceram muitos bytes 00, FF, FC, E0. Isso normalmente indica:
1. Sinal degradado no ponto de captura.
2. Linha com carga externa da placa de aplicacao.
3. Baud errado, timing ruim, ou leitura em ponto intermediario e nao no TX limpo do modulo.

Importante: sniff "bonito" (texto legivel) nao e obrigatorio para flash funcionar. O teste definitivo e sincronizar e ler flash no bootloader.

### 4.4 Mapa de memoria (o principal para nao brickar)
Para BK7231N, conceito pratico:
1. Endereco 0x00000: regiao de bootloader.
2. Endereco 0x11000: regiao tipica de aplicacao (app).

Consequencia:
1. Gravar arquivo de app no endereco errado pode sobrescrever bootloader.
2. Ferramentas modernas (ltchiptool) detectam tipo de arquivo e escolhem offset correto.

## 5. Ferramentas e papel de cada uma
1. pyserial: sniff e testes seriais.
2. hid_download_py/uartprogram: leitura de flash (foi usado para dump/backup).
3. ltchiptool: gravacao segura e deteccao automatica de tipo/offset.

## 6. Linha do Tempo Tecnica (o que realmente aconteceu)
1. Primeiro, tentativas de sniff em varios bauds e pinos.
2. Resultado inicial: quase sem dados uteis (muitos 00).
3. Descoberta de mapeamento dos pads da interface (RX/TX da interface x RX/TX do CB3S).
4. Ajustes de tensao e cabos.
5. Teste de sincronismo do bootloader em modo somente leitura (sucesso).
6. Backup completo da flash em 3 leituras de 4 MB com hash igual.
7. Gravacao do OpenBeken com ltchiptool usando arquivo UA e offset auto-detectado.

## 7. Procedimento Replicavel do Zero

### 7.1 Preparar ambiente
No projeto:
1. Ativar venv.
2. Garantir ferramentas instaladas (pyserial, ltchiptool).

### 7.2 Confirmar porta serial
Verificar dispositivo USB-TTL no sistema, por exemplo:
- /dev/cu.usbserial-00000000

### 7.3 Validar handshake do bootloader (read-only)
Exemplo de leitura pequena para prova de vida (hid_download_py):

```bash
cd "firmware/hid_download_py"
"/Users/pedro/development/IC - LASDPC/IR Sniffing - Beken cb3s/.venv/bin/python" ./uartprogram /tmp/bk_read_test.bin -d /dev/cu.usbserial-00000000 -r -s 0x0 -l 0x100
```

Durante a execucao, aplicar pulso de CEN.
Se sincronizar e ler, bootloader esta acessivel.

### 7.4 Fazer backup completo da flash (OBRIGATORIO)
Leitura de 4 MB:

```bash
cd "firmware/hid_download_py"
"/Users/pedro/development/IC - LASDPC/IR Sniffing - Beken cb3s/.venv/bin/python" ./uartprogram "../backups/SEU_TIMESTAMP/bk7231n_backup_read1.bin" -d /dev/cu.usbserial-00000000 -r -s 0x0 -l 0x400000 -b 115200
```

Repetir para read2 e read3 e comparar hash.

### 7.5 Validar integridade do backup
Exemplo:

```bash
md5 bk7231n_backup_read1.bin bk7231n_backup_read2.bin bk7231n_backup_read3.bin
```

Se os 3 MD5 forem iguais, backup confiavel.

### 7.6 Baixar firmware correto do OpenBeken
Firmware usado:
- OpenBK7231N_UA_1.18.287.bin

### 7.7 Gravar com ltchiptool (recomendado)
Comando usado:

```bash
"/Users/pedro/development/IC - LASDPC/IR Sniffing - Beken cb3s/.venv/bin/ltchiptool" flash write "/Users/pedro/development/IC - LASDPC/IR Sniffing - Beken cb3s/firmware/OpenBK7231N_UA_1.18.287.bin" -d /dev/cu.usbserial-00000000 -b 57600
```

O ltchiptool detectou automaticamente:
1. Tipo: Beken CRC/UA App
2. Chip: BK7231N
3. Start offset: 0x11000

## 8. Evidencias e Resultados Finais

### 8.1 Backup concluido
Diretorio:
- firmware/backups/20260411_193012/

Arquivos:
1. bk7231n_backup_read1.bin
2. bk7231n_backup_read2.bin
3. bk7231n_backup_read3.bin

### 8.2 Integridade por MD5
Os tres arquivos tiveram o mesmo hash:
- 75d5b0834ad71bebe9ee8a3515000ecb

### 8.3 Gravacao do OpenBeken
1. Tentativa inicial falhou por perda de resposta em baud alto.
2. Nova tentativa com baud menor concluiu 100%.
3. Gravacao finalizada com sucesso.

## 9. Troubleshooting (erros comuns e correcao)

### 9.1 "Cannot get bus"
Causa tipica:
1. Timing de reset ruim.
2. Fios soltos/longos.
3. Sem GND comum.

Correcao:
1. Iniciar comando e so depois pulsar CEN.
2. Fazer 1-2 pulsos de CEN.
3. Reduzir baud (ex.: 115200 ou 57600).

### 9.2 "No response received" no meio da gravacao
Causa tipica:
1. Alimentacao instavel.
2. Cabo ruim.
3. Baud alto para a qualidade do enlace.

Correcao:
1. Melhorar fonte 3.3 V.
2. Curto de cabos.
3. Repetir em baud menor.

### 9.3 Sniff so com 00/FF
Causa tipica:
1. Ponto de captura degradado.
2. UART da placa de aplicacao interferindo.

Correcao:
1. Medir nivel da linha em idle.
2. Ler no ponto mais proximo do TX do modulo.
3. Nao usar RXL/TXL para dados.

## 10. O que aprender deste caso
1. Engenharia reversa nao e chute: e sequencia de testes controlados.
2. Confirmar bootloader por leitura real e melhor que confiar em sniff textual.
3. Backup completo antes de escrever e regra de ouro.
4. Ferramenta certa (ltchiptool) reduz risco de erro de offset.
5. Estabilidade eletrica manda no sucesso da gravacao.

## 11. Checklist final para replicar com seguranca
1. FTDI em 3.3 V.
2. RXD/TXD corretos.
3. GND comum.
4. CEN acessivel.
5. Handshake read-only OK.
6. Backup 3x com MD5 igual.
7. Firmware correto para BK7231N.
8. Gravacao em offset correto (app em 0x11000 para UA).
9. Reset e validacao pos-flash.

## 12. Proximos passos sugeridos
1. Confirmar AP inicial do OpenBeken apos reset.
2. Configurar Wi-Fi e MQTT.
3. Mapear GPIO de IR (RX/TX IR, LED de status, botoes).
4. Versionar este relatorio junto com logs e hashes para rastreabilidade.

## 13. Comparacao com tutorial oficial do OpenBeken

### 13.1 Fontes oficiais consultadas
1. https://github.com/openshwprojects/OpenBK7231T_App/blob/main/docs/initialSetup.md
2. https://github.com/openshwprojects/OpenBK7231T_App/blob/main/FLASHING.md
3. https://github.com/openshwprojects/OpenBK7231T_App/blob/main/docs/safeMode.md

### 13.2 Fluxo oficial resumido
De acordo com a documentacao oficial:
1. Gravar firmware de release e seguir o guia de flash.
2. Conectar no AP inicial do OpenBeken.
3. Abrir 192.168.4.1 e configurar SSID/senha em Config -> WiFi.
4. Reiniciar o modulo.
5. Descobrir o novo IP pela pagina DHCP do roteador.
6. Opcionalmente, configurar reserva de MAC para manter IP fixo.

### 13.3 Fluxo executado neste projeto
No processo real desta placa CB3S, seguimos um fluxo mais robusto para recuperacao:
1. Validacao de bootloader em modo read-only antes de qualquer escrita.
2. Backup completo da flash em 3 leituras, com validacao de integridade por MD5.
3. Gravacao via ltchiptool em baud menor quando houve instabilidade de enlace.
4. Quando AP nao apareceu e nao havia acesso ao painel do roteador, descoberta de IP por ARP local com filtro por MAC conhecido.
5. Confirmacao do endpoint web por ping e HTTP 401 (autenticacao ativa).
6. Recuperacao adicional por imagem combinada de firmware + regiao de configuracao.

### 13.4 Diferencas principais
1. Descoberta de IP:
   - Oficial: consulta na pagina DHCP do roteador.
   - Projeto: ARP local + MAC, sem depender de login no roteador.
2. Recuperacao de acesso:
   - Oficial: uso de AP inicial e safe mode por ciclos de energia.
   - Projeto: uso complementar de reflash controlado para limpar estado de configuracao e credenciais.
3. Controle de risco:
   - Oficial: foco em caminho simples para iniciantes.
   - Projeto: foco em rastreabilidade, backup multiplo e verificacao de hash antes de escrita.
4. Ferramentas de gravacao:
   - Oficial: BK7231 GUI Flash Tool como caminho facil, com metodos UART antigos documentados.
   - Projeto: ltchiptool e hid_download_py para diagnostico e gravacao em ambiente multiplataforma.

### 13.5 Conclusao da comparacao
O procedimento oficial cobre bem o caminho padrao de setup. O fluxo aplicado neste trabalho manteve compatibilidade com os principios da documentacao, porem adicionou camadas de seguranca e diagnostico para um cenario real com falhas de enlace, alteracao de estado de rede e perda de credenciais web.

## 14. Flags ativas e pinagem final no OpenBeken

### 14.1 Por que ativar flags no OpenBeken
No OpenBeken, boa parte do comportamento de alto nivel e controlada por flags globais de firmware. Isso difere de muitos fluxos com microcontroladores tradicionais, nos quais o comportamento costuma ser definido diretamente no codigo da aplicacao (registradores, middleware ou macros de build). Em OBK, as flags permitem habilitar funcionalidades em runtime, sem recompilar firmware.

No contexto deste projeto, isso foi necessario para garantir telemetria IR no MQTT em mais de um formato de payload.

### 14.2 Flags habilitadas e funcao tecnica
1. Flag 10: publica estado do dispositivo ao reconectar no MQTT.
   - Utilidade pratica: ajuda a confirmar reconexao e diagnosticar quedas de rede.
2. Flag 14: publica IR recebido em formato RAW string.
   - Utilidade pratica: mantem compatibilidade com parse textual legado de eventos IR.
3. Flag 22: publica IR recebido em JSON estilo Tasmota (campo IrReceived).
   - Utilidade pratica: integra com parser estruturado no backend e reduz ambiguidade de interpretacao.

### 14.3 Validacao teorica da pinagem
Mapeamento aplicado no modulo:
1. P7 -> IRRecv
2. P26 -> IRSend

Este mapeamento e teoricamente consistente com a engenharia reversa realizada:
1. Sinal OUT do receptor IR rastreado ate o GPIO P7.
2. Linha IRDA conectada ao estagio driver (22ES + rede resistiva) rastreada ate P26.

### 14.4 Evidencias visuais anexadas
Print de flags ativas:

![Flags ativas no OpenBeken](docs/openbeken/prints/19_flags_ativas_cfg_generic.png)

Print de pinagem final:

![Pinagem final P7 IRRecv e P26 IRSend](docs/openbeken/prints/18_pins_cfg_p7_irrecv_p26_irsend.png)

## 15. Pacote de documentacao de protocolos IR

Para atender a necessidade de transferencia de conhecimento no laboratorio, foi consolidado um pacote de documentacao em dois niveis:

1. Versao completa (base tecnica e metodo de catalogacao):
   - docs/openbeken/PROTOCOLOS_IR_COMPLETO.md
2. Versao didatica (execucao rapida para replicacao):
   - docs/openbeken/PROTOCOLOS_IR_FOR_DUMMIES.md

A versao completa detalha os principais modelos de codificacao, protocolos prioritarios, criterios de qualidade de captura e metodo de classificacao de comandos. A versao didatica resume o fluxo operacional para que qualquer membro do laboratorio consiga reproduzir os testes com consistencia.

## 16. Diagnostico aprofundado da captura IR (firmware + backend)

Para atacar o problema de alto volume de eventos `UNKNOWN 0x0 Bits=0`, foi executada uma analise em duas camadas: firmware OpenBeken e parser de ingestao no backend.

### 16.1 Conclusoes no firmware OpenBeken
No caminho de driver com `IRremoteESP8266`, foi confirmado por codigo-fonte que:
1. Existe comando de ajuste em runtime: `IRParam [MinSize] [Noise Threshold]`.
2. O comando ajusta threshold de unknown e tolerancia de casamento de pulsos.
3. Os valores padrao observados no codigo sao coerentes com recepcao generica:
   - buffer de captura 1024
   - timeout de 90 ms
   - tolerancia de 25%

Essa constatacao permitiu substituir ajuste empirico por varredura controlada de parametros.

### 16.2 Conclusoes no backend de ingestao
Foi identificado que o parser antigo aceitava formatos ambiguos em topicos diversos, o que elevava a incidencia de linhas nulas no CSV e dificultava a leitura da qualidade real de recepcao.

Ajustes aplicados em `server/app.py`:
1. Parse orientado a topico.
2. Prioridade para payload JSON `IrReceived` no topico `.../RESULT`.
3. Bloqueio de parse heuristico em topicos nao IR.
4. Filtro opcional para capturas nulas (`0x0`, `bits=0`).
5. Opcao para priorizar `RESULT` e ignorar raw de `.../ir` quando necessario.

### 16.3 Impacto tecnico
1. Reducao de poluicao do dataset por payload ambiguo.
2. Melhor separacao entre ruido de captura real e ruido de parse.
3. Base mais confiavel para comparar configuracoes de `IRParam`.

### 16.4 Proxima etapa recomendada
Executar matriz A/B de `IRParam` com protocolo de coleta fechado e metricas objetivas de aceite (`taxa_util`, `taxa_nula`, `estabilidade_assinatura`).

Documento de referencia desta etapa:
1. docs/openbeken/DIAGNOSTICO_IR_FIRMWARE_OBK.md

## 17. Validacao de emissao IR no hardware local (LED IR)

Na rodada de verificacao em runtime no Command Tool do OpenBeken, foi executado o comando `blink_ir`, previamente definido no dispositivo para acionar o canal de emissao IR em pulso curto. O retorno do firmware foi `OK`, indicando execucao correta da cadeia de comando no modulo.

Configuracao associada:
1. P26 configurado como `IRSend`.
2. Alias de teste apontando para sequencia de canal (`SetChannel 1 1`, `delay_ms 120`, `SetChannel 1 0`).

Conclusao tecnica:
1. O caminho de emissao IR local foi validado no firmware.
2. O requisito de verificacao de acionamento do LED IR foi atendido.

Evidencia visual:
1. docs/openbeken/prints/21_led_ir_blink_ok.png

## 18. Higienizacao para push inicial do repositorio

Para reduzir ruido no primeiro push e manter separacao entre codigo, documentacao e artefatos gerados em runtime, foram aplicadas as acoes abaixo:
1. Consolidacao dos documentos de requisitos em `docs/requisitos/`.
2. Encerramento da pasta antiga `docummentation`.
3. Atualizacao do `.gitignore` para bloquear artefatos de captura e backup que nao devem ir para versionamento:
   - CSVs e logs de `server/data`.
   - backups de `firmware/backups`.

Resultado:
1. Estrutura do repositorio preparada para push inicial com rastreabilidade de evidencias.
2. Lista de pendencias consolidada para o proximo ciclo tecnico.

Arquivo de planejamento:
1. docs/openbeken/TODOS_PUSH.md
