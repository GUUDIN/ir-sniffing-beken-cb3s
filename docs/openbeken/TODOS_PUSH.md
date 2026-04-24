# TODOs Consolidado para Push e Proxima Rodada

Data de atualizacao: 2026-04-14

## Concluidos nesta rodada (Atualizado 2026-04-24)
- [x] Validar emissao IR no hardware local com comando `blink_ir` (retorno `OK`).
- [x] Salvar evidencia de emissao em `docs/openbeken/prints/21_led_ir_blink_ok.png`.
- [x] Executar matriz A/B de `IRParam` (Vencedor: 24 20).
- [x] Consolidar documentação de Arquitetura de Software em `docs/ARQUITETURA_SISTEMA.md`.
- [x] Confirmar visualizacao completa no painel local `server` na porta 5050 com dados reais.

## Pendencias para proxima rodada tecnica
- [ ] Validar envio IR em alvo externo (equipamento controlado) alem do LED local.
- [ ] Criar repositório remoto no GitHub e realizar o primeiro Push.
- [ ] Adicionar sistema de autenticação simples no Dashboard (opcional).
- [ ] Realizar teste de longa duração (stress test) na captura de AC.

## Status operacional de hoje (2026-04-24)
- [x] Broker MQTT local ativo.
- [x] Backend Flask ativo e estável.
- [x] Dispositivo OBK configurado com `IRParam 24 20` via autoexec.bat.
- [x] Logs de teste A/B movidos para histórico (`server/data/ab_runs`).

### Acao imediata durante a sessao AC
- [ ] Pressionar sequencia fixa no controle (Power, Temp+, Temp-, Mode, Fan) com 5 repeticoes por tecla.
- [ ] Rodar resumo do log apos a coleta.
- [ ] Confirmar surgimento de frames longos/candidatos AC no resumo.

### Troubleshooting rapido (emissao IR)
- [ ] Confirmar no OBK que o pino do transmissor esta como `IRSend` (nao `LED`).
- [ ] Testar comando `IRSend` direto (evitar `SetChannel` para emissao IR).
- [ ] Validar flash do LED IR com camera do celular (olho nu pode nao enxergar).

### Troubleshooting rapido (acesso web)
- [ ] Se `ircontrol-lasdpc` estiver unreachable, usar IP direto atual do modulo (ex.: 10.0.3.155).
- [ ] Atualizar reserva DHCP/DNS local para evitar drift de hostname x IP.

## Criterios de aceite para proximo push
- [ ] Pelo menos uma evidencia de RX util e uma de TX em alvo externo.
- [ ] README/relatorio sem secoes contraditorias sobre status de IR.
- [ ] Nenhum arquivo de backup bruto ou dataset temporario listado no staging.
