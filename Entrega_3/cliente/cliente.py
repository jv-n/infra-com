import socket
import time

# Configuração do cliente
SERVER_IP = "127.0.0.1"
SERVER_PORT = 12000
BUFFER_SIZE = 1024
#FILE_TO_SEND = "data.txt"  # Arquivo a ser enviado (modelo txt)
FILE_TO_SEND = "data.jpg"  # Arquivo a ser enviado (modelo jpg)


# Criando o socket UDP
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_socket.settimeout(1)  # Timeout de 1 segundo para receber ACKs

# Enviar arquivo com RDT 3.0
seq_num = 0  # Número de sequência inicial

##### IMPLEMENTAR LOOP INFINITO
command = input() 
for i in range(0, len(command), BUFFER_SIZE - 1):
    chunk = command[i:i + BUFFER_SIZE - 1]
    packet = bytes([seq_num]) + chunk  # Adiciona número de sequência ao pacote

    while True:  # Loop até receber o ACK correto
        client_socket.sendto(packet, (SERVER_IP, SERVER_PORT))
        print(f"Enviado pacote {seq_num}, aguardando ACK...")

        try:
            ack, _ = client_socket.recvfrom(BUFFER_SIZE)
            if ack.decode() == f"ACK {seq_num}":
                print(f"Recebido {ack.decode()}, enviando próximo pacote.")
                seq_num = 1 - seq_num  # Alterna sequência (0 -> 1, 1 -> 0)
                break  # Sai do loop se ACK correto for recebido
        except socket.timeout:
            print(f"Timeout! Reenviando pacote {seq_num}...")

# Enviar sinal de fim
client_socket.sendto(b"END", (SERVER_IP, SERVER_PORT))

# Receber novo nome do arquivo
response, _ = client_socket.recvfrom(BUFFER_SIZE)
response = response.decode()
print(f"{response}")


client_socket.close()
