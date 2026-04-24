// IR Sniffer autoexec for CB3S / BK7231N (OpenBeken)
// Adjust pin numbers below to your board wiring.

// Cleanup old handlers/events if this file is reloaded many times.
clearAllHandlers
clearRepeatingEvents

// 1) GPIO roles
// IR receiver on P7 (no internal pull-up).
SetPinRole 7 IRRecv_nPup

// IR transmitter LED/driver control pin.
// NOTE: this must be IRSend (not LED) for actual 38kHz IR carrier emission.
SetPinRole 26 IRSend

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

// 4) IR emission helper
// Human eyes usually cannot see IR LED blinking. Use a phone camera to confirm flashes.
alias blink_ir IRSend NEC-20DF-10EF-1

// NOTE:
// OpenBeken emits generic IR events only for selected protocols (NEC/Samsung/RC5/RC6/Sony/Sharp),
// while AC protocols like TCL112AC are published through JSON on ir_sniffer/RESULT.
// Because of that, a protocol-agnostic per-capture LED blink is handled more reliably in backend/UI.

// Startup heartbeat
publish ir_sniffer/capture sniffer_ready 1
