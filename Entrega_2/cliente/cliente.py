import socket
import time

# Configuração do cliente
SERVER_IP = "127.0.0.1"
SERVER_PORT = 12000
BUFFER_SIZE = 1024
FILE_TO_SEND = "data.jpg"  # Arquivo a ser enviado

# Criando o socket UDP
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_socket.settimeout(1)  # Timeout de 1 segundo para receber ACKs

# Enviar nome do arquivo
client_socket.sendto(FILE_TO_SEND.encode(), (SERVER_IP, SERVER_PORT))

# Enviar arquivo com RDT 3.0
seq_num = 0  # Número de sequência inicial

with open(f"cliente/{FILE_TO_SEND}", "rb") as file:
    while chunk := file.read(BUFFER_SIZE - 1):  # Deixamos 1 byte para o número de sequência
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
new_file_name, _ = client_socket.recvfrom(BUFFER_SIZE)
new_file_name = new_file_name.decode()
print(f"Arquivo será salvo como: {new_file_name}")

# Receber o arquivo renomeado
with open(f"cliente/{new_file_name}", "wb") as file:
    while True:
        data, _ = client_socket.recvfrom(BUFFER_SIZE)
        if data == b"END":
            break
        file.write(data)

print(f"Arquivo '{new_file_name}' recebido com sucesso!")

client_socket.close()