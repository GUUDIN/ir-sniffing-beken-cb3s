import sys
import time
from typing import List, Any

import serial
from serial import SerialException
from serial.tools import list_ports


def list_serial_ports() -> List[Any]:
    ports = list(list_ports.comports())
    if not ports:
        print("Nenhuma porta serial encontrada.")
        print("Verifique cabo, alimentação e conexão do FTDI.")
        sys.exit(1)

    print("Portas seriais detectadas:")
    for idx, p in enumerate(ports, start=1):
        desc = p.description or "(sem descrição)"
        hwid = p.hwid or "(sem HWID)"
        print(f"  {idx}. {p.device} | {desc} | {hwid}")

    return ports


def choose_port(ports: List[Any]) -> str:
    usb_candidates = [
        p for p in ports
        if "usb" in (p.device or "").lower() or "usb" in (p.description or "").lower()
    ]

    if len(usb_candidates) == 1:
        selected = usb_candidates[0].device
        print(f"Seleção automática: {selected}")
        return selected

    while True:
        choice = input("Digite o número da porta desejada: ").strip()
        if not choice.isdigit():
            print("Entrada inválida. Digite apenas o número da porta.")
            continue

        idx = int(choice)
        if 1 <= idx <= len(ports):
            return ports[idx - 1].device

        print("Número fora da lista. Tente novamente.")


def open_serial(port_name: str, exit_on_error: bool = True) -> serial.Serial:
    try:
        ser = serial.Serial(
            port=port_name,
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=2,
        )
        return ser
    except SerialException as exc:
        print(f"Erro ao abrir {port_name}: {exc}")
        if exit_on_error:
            print("Soluções sugeridas:")
            print("1) Feche qualquer monitor serial (IDE, screen, minicom, etc.).")
            print("2) Verifique permissões do usuário no dispositivo serial.")
            print("3) Em Linux, adicione seu usuário ao grupo dialout:")
            print("   sudo usermod -aG dialout $USER")
            print("4) No macOS, verifique se outro processo está ocupando a porta com lsof.")
            sys.exit(1)
        raise


def main() -> None:
    ports = list_serial_ports()
    selected_port = choose_port(ports)

    print(f"\nConectando em {selected_port} (115200 8N1, timeout=2s)...")
    ser = open_serial(selected_port)

    print("Conexão aberta com sucesso.")

    # Teste de TX
    cmd = "AT\r\n"
    print(f"Enviando comando de teste TX: {cmd!r}")
    ser.write(cmd.encode("utf-8"))
    ser.flush()

    # Leitura imediata de RX
    immediate = ser.read(256)
    if immediate:
        try:
            decoded = immediate.decode("utf-8", errors="replace")
        except Exception:
            decoded = str(immediate)
        print(f"Resposta imediata RX ({len(immediate)} bytes): {decoded}")
    else:
        print("Sem resposta imediata ao comando AT.")

    print("\nEntrando em modo escuta contínua...")
    print("Agora você pode apertar RESET na placa para capturar bootlog.")
    print("Pressione Ctrl+C para sair.\n")

    try:
        while True:
            try:
                line = ser.readline()
            except SerialException as exc:
                # Common on macOS when USB serial briefly disconnects/re-enumerates.
                print(f"\nFalha de leitura serial: {exc}")
                print("Tentando reconectar automaticamente...")

                try:
                    ser.close()
                except Exception:
                    pass

                reconnected = False
                for attempt in range(1, 11):
                    try:
                        ser = open_serial(selected_port, exit_on_error=False)
                        print(f"Reconectado em {selected_port} (tentativa {attempt}).")
                        reconnected = True
                        break
                    except Exception:
                        pass
                    time.sleep(1)

                if not reconnected:
                    print("Não foi possível reconectar após 10 tentativas. Encerrando.")
                    break

                continue

            if line:
                text = line.decode("utf-8", errors="replace").rstrip("\r\n")
                print(text)
    except KeyboardInterrupt:
        print("\nEncerrando escuta serial...")
    finally:
        ser.close()
        print("Porta serial fechada.")


if __name__ == "__main__":
    main()
