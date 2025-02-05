import socket

# Configuração do cliente
SERVER_IP = "127.0.0.1" 
SERVER_PORT = 12000
BUFFER_SIZE = 1024
FILE_TO_SEND = "data.txt"  # Arquivo a ser enviado (modelo txt)
#FILE_TO_SEND = "data.jpg"  # Arquivo a ser enviado (modelo jpg)

# Criando o socket UDP
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Enviar nome do arquivo
client_socket.sendto(FILE_TO_SEND.encode(), (SERVER_IP, SERVER_PORT))

# Enviar arquivo em pacotes
with open(FILE_TO_SEND, "rb") as file:
    while chunk := file.read(BUFFER_SIZE):
        client_socket.sendto(chunk, (SERVER_IP, SERVER_PORT))

# Enviar sinal de fim
client_socket.sendto(b"END", (SERVER_IP, SERVER_PORT))

# Receber o novo nome do arquivo
new_file_name, _ = client_socket.recvfrom(BUFFER_SIZE)
new_file_name = new_file_name.decode()
print(f"Arquivo será salvo como: {new_file_name}")

# Receber o arquivo renomeado e salvar
with open(new_file_name, "wb") as file:
    while True:
        data, _ = client_socket.recvfrom(BUFFER_SIZE)
        if data == b"END":  # Verifica fim da transmissão
            break
        file.write(data)

print(f"Arquivo '{new_file_name}' recebido com sucesso!")

client_socket.close()