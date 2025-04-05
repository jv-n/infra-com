import socket

SERVER_IP = "127.0.0.1"
SERVER_PORT = 12000
BUFFER_SIZE = 1024

# Cria socket UDP
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_socket.settimeout(2)

print("=== ChatCin UDP ===")
print("Comandos disponíveis:")
print(" - login <nome>")
print(" - logout")
print(" - status")
print(" - /exit para sair")

while True:
    command = input("> ").strip()

    if command == "/exit":
        break

    try:
        # Envia comando para o servidor
        client_socket.sendto(command.encode(), (SERVER_IP, SERVER_PORT))

        # Aguarda resposta
        response, _ = client_socket.recvfrom(BUFFER_SIZE)
        print(response.decode())

    except socket.timeout:
        print("⚠️  Servidor não respondeu (timeout).")
    except Exception as e:
        print(f"Erro: {e}")

client_socket.close()
