import socket
import time

SERVER_IP = "127.0.0.1"
SERVER_PORT = 12000
BUFFER_SIZE = 1024
seq_num = 0  # Número de sequência inicial

# Cria socket UDP
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_socket.settimeout(1)

def rdt_send(message: bytes):
    global seq_num
    packet = bytes([seq_num]) + message


    while True:
        client_socket.sendto(packet, (SERVER_IP, SERVER_PORT))

        try:
            response, _ = client_socket.recvfrom(BUFFER_SIZE)

            if response.decode() == f"ACK {seq_num}":
                seq_num = 1 - seq_num
                return

        except socket.timeout:
            print("⚠️  Timeout: Servidor não respondeu. Reenviando...")

def rdt_recv():
    while True:
        try:
            data, _ = client_socket.recvfrom(BUFFER_SIZE)
            recv_seq = data[0]
            message = data[1:]

            client_socket.sendto(f"ACK {recv_seq}".encode(), (SERVER_IP, SERVER_PORT))

            return message.decode()

        except socket.timeout:
            print("⚠️  Timeout: Aguardando pacote do servidor...")

print("=== ChatCin UDP ===")
print("Comandos disponíveis:")
print(" - login <nome>")
print(" - logout")
print(" - follow <nome>") #erro
print(" - unfollow <nome>")
print(" - list:cinners")
print(" - create_group <nome>")
print(" - delete_group <nome>")
print(" - list:groups") #erro
print(" - list:mygroups")
print(" - leave <nome_do_grupo>")
print(" - ban <usuario> <grupo>") #erro
print(" - join <nome_do_grupo> <chave_grupo>")
print(" - chat_group <nome_do_grupo> <chave_grupo> <mensagem>") #erro
print(" - chat_friend <nome_do_amigo> <mensagem>") #erro
print(" - /exit para sair")

while True:
    command = input("> ").strip()

    if command == "/exit":
        break

    try:
        rdt_send(command.encode())
        response = rdt_recv()
        print(response)

    except Exception as e:
        print(f"Erro: {e}")

client_socket.close()
print("Conexão encerrada.")
