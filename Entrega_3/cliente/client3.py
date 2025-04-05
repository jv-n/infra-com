import socket
import time

SERVER_IP = "127.0.0.1"
SERVER_PORT = 12000
BUFFER_SIZE = 1024

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_socket.settimeout(1)

seq_num = 0

print("=== ChatCin UDP ===")
print("Digite um comando (/exit para sair)")
while True:
    command = input("> ")
    if command == "/exit":
        break
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


client_socket.close()
