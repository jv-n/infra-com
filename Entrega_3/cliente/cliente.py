import socket
import threading

SERVER_IP = "127.0.0.1"
SERVER_PORT = 12000
BUFFER_SIZE = 1024

# Cria socket UDP
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_socket.settimeout(2)

def listen_for_messages():
    while True:
        try:
            data, _ = client_socket.recvfrom(BUFFER_SIZE)
            print("\n📩 Mensagem recebida:", data.decode())
            print("> ", end="", flush=True)
        except socket.timeout:
            continue
        except Exception as e:
            print(f"\n❌ Erro ao receber mensagem: {e}")
            break

# Thread para receber mensagens inesperadas do servidor
threading.Thread(target=listen_for_messages, daemon=True).start()

print("=== ChatCin UDP ===")
print("Comandos disponíveis:")
print(" - login <nome>")
print(" - logout")
print(" - follow <nome>")
print(" - unfollow <nome>")
print(" - list:cinners")
print(" - create_group <nome>")
print(" - delete_group <nome>")
print(" - list:groups")
print(" - list:mygroups")
print(" - leave <nome_do_grupo>")
print(" - ban <usuario> <grupo>")
print(" - join <nome_do_grupo> <chave_grupo>")
print(" - /exit para sair")

while True:
    command = input("> ").strip()

    if command == "/exit":
        break

    try:
        # Envia comando para o servidor
        client_socket.sendto(command.encode(), (SERVER_IP, SERVER_PORT))

        # Aguarda resposta principal
        response, _ = client_socket.recvfrom(BUFFER_SIZE)
        print(response.decode())

    except socket.timeout:
        print("⚠️  Servidor não respondeu (timeout).")
    except Exception as e:
        print(f"Erro: {e}")

client_socket.close()
