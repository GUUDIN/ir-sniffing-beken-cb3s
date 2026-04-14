# TODOs Consolidado para Push e Proxima Rodada

Data de atualizacao: 2026-04-14

## Concluidos nesta rodada
- [x] Validar emissao IR no hardware local com comando `blink_ir` (retorno `OK`).
- [x] Salvar evidencia de emissao em `docs/openbeken/prints/21_led_ir_blink_ok.png`.
- [x] Atualizar diario tecnico com status de emissao IR e preparo para push.
- [x] Atualizar relatorio principal com secao de validacao do LED IR.
- [x] Organizar documentos de requisitos em `docs/requisitos/`.
- [x] Atualizar `.gitignore` para excluir artefatos de runtime e backups.

## Pendencias para proxima rodada tecnica
- [ ] Capturar evidencia visual dedicada de recepcao IR em runtime (print de evento util no monitor).
- [ ] Validar envio IR em alvo externo (equipamento controlado) alem do LED local.
- [ ] Executar plano de estabilidade para captura de AC (reduzir UNKNOWN e ruide em massa).
- [ ] Confirmar visualizacao completa no painel local `server` na porta 5050 com dados reais.
- [ ] Fechar checklist de reproducao em ambiente limpo.

## Criterios de aceite para proximo push
- [ ] Pelo menos uma evidencia de RX util e uma de TX em alvo externo.
- [ ] README/relatorio sem secoes contraditorias sobre status de IR.
- [ ] Nenhum arquivo de backup bruto ou dataset temporario listado no staging.
