import socket
import time

SERVER_IP = "127.0.0.1"
SERVER_PORT = 12000
BUFFER_SIZE = 1024

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_socket.settimeout(1)

seq_num = 0


def send_command_rdt(command: str):

    # Divide em pacotes RDT
    for i in range(0, len(command), BUFFER_SIZE - 1):
        chunk = command[i:i + BUFFER_SIZE - 1]
        packet = bytes([seq_num]) + chunk.encode()

        while True:
            client_socket.sendto(packet, (SERVER_IP, SERVER_PORT))
            print(f"Enviado pacote {seq_num}, aguardando ACK...")

            try:
                ack, _ = client_socket.recvfrom(BUFFER_SIZE)
                if ack.decode() == f"ACK {seq_num}":
                    print(f"Recebido {ack.decode()}, enviando próximo pacote.")
                    seq_num = 1 - seq_num
                    break
            except socket.timeout:
                print(f"Timeout! Reenviando pacote {seq_num}...")

    # Sinaliza fim da mensagem
    client_socket.sendto(b"END", (SERVER_IP, SERVER_PORT))

    response, _ = client_socket.recvfrom(BUFFER_SIZE)
    response = response.decode()
    print(f"{response}")


def commandrcv(command: str):
    if command.startswith("login "):
        send_command_rdt(command)
    elif command == "logout":
        send_command_rdt(command)
    elif command == "list:cinners":
        send_command_rdt(command)
    elif command == "list:friends":
        send_command_rdt(command)
    elif command == "list:mygroups":
        send_command_rdt(command)
    elif command == "list:groups":
        send_command_rdt(command)
    elif command.startswith("follow ") or command.startswith("unfollow "):
        send_command_rdt(command)
    elif command.startswith("create_group ") or command.startswith("delete_group "):
        send_command_rdt(command)
    elif command.startswith("join ") or command.startswith("leave "):
        send_command_rdt(command)
    elif command.startswith("ban "):
        send_command_rdt(command)
    elif command.startswith("chat_group "):
        send_command_rdt(command)
    elif command.startswith("chat_friend "):
        send_command_rdt(command)
    elif command == "/exit":
        print("Cliente encerrando conexão...")
        return False
    else:
        print("Comando inválido ou não reconhecido.")
    return True

#LOOP PRINCIPAL
print("=== ChatCin UDP ===")
print("Digite um comando (/exit para sair)")
while True:
    user_command = input(">> ")
    if not commandrcv(user_command):
        break

client_socket.close()
