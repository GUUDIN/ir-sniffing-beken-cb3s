// IR Sniffer autoexec for CB3S / BK7231N (OpenBeken)
// Adjust pin numbers below to your board wiring.

// Cleanup old handlers/events if this file is reloaded many times.
clearAllHandlers
clearRepeatingEvents

// 1) GPIO roles
// Example: IR receiver on P8 (no internal pull-up).
SetPinRole 8 IRRecv_nPup

// Example: status LED on P26.
SetPinRole 26 LED
SetPinChannel 26 1
SetChannel 1 0

// 2) MQTT identity
// This makes base topics start with ir_sniffer/...
ShortName ir_sniffer

// 3) IR publish behavior
// Flag 14: publish raw IR triplet to ir_sniffer/ir/get (protocolIdHex,dataHex,bits)
// Flag 15: allow unknown protocol captures
// Flag 22: publish decoded JSON to ir_sniffer/RESULT
//          Example payload:
//          {"IrReceived":{"Protocol":"TCL112AC","Bits":112,"Data":"0x..."}}
SetFlag 14 1
SetFlag 15 1
SetFlag 22 1

// 4) Visual feedback helper
alias blink_ir backlog SetChannel 1 1; delay_ms 120; SetChannel 1 0

// NOTE:
// OpenBeken emits generic IR events only for selected protocols (NEC/Samsung/RC5/RC6/Sony/Sharp),
// while AC protocols like TCL112AC are published through JSON on ir_sniffer/RESULT.
// Because of that, a protocol-agnostic per-capture LED blink is handled more reliably in backend/UI.

// Startup heartbeat
publish ir_sniffer/capture sniffer_ready 1
