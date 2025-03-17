import socket
import random

# Configuração do servidor
serverPort = 12000
BUFFER_SIZE = 1024

# Criando socket UDP
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(('', serverPort))

print(f"Servidor pronto na porta {serverPort}")

while True:
    # Recebe nome do arquivo
    file_name, client_addr = server_socket.recvfrom(BUFFER_SIZE)
    file_name = file_name.decode()
    print(f"Recebido: {file_name} de {client_addr}")

    # Criar arquivo para armazenar os dados recebidos
    with open(f"servidor/server_{file_name}", "wb") as file:
        expected_seq = 0  # Esperamos receber pacotes começando com 0

        while True:
            data, client_addr = server_socket.recvfrom(BUFFER_SIZE)
            
            # Se for o sinal de fim, encerra
            if data == b"END":
                break
            
            seq_num = data[0]  # Primeiro byte é o número de sequência
            payload = data[1:]  # O restante são os dados reais

            # Simula perda de pacotes (30% de chance de descartar o pacote)
            if random.random() < 0.3:
                print(f"Pacote {seq_num} perdido! (Simulação)")
                continue  # Não responde, simulando perda
            
            if seq_num == expected_seq:  # Verifica se é o pacote correto
                file.write(payload)
                print(f"Recebido pacote {seq_num}, enviando ACK {seq_num}")
                server_socket.sendto(f"ACK {seq_num}".encode(), client_addr)
                expected_seq = 1 - expected_seq  # Alterna sequência
            else:
                print(f"Pacote duplicado {seq_num}, reenviando ACK {1 - expected_seq}")
                server_socket.sendto(f"ACK {1 - expected_seq}".encode(), client_addr)

    print(f"Arquivo salvo como 'server_{file_name}'")

    # Enviar novo nome do arquivo
    new_file_name = f"modified_{file_name}"
    server_socket.sendto(new_file_name.encode(), client_addr)

    # Enviar arquivo de volta ao cliente
    with open(f"servidor/server_{file_name}", "rb") as file:
        while chunk := file.read(BUFFER_SIZE):
            server_socket.sendto(chunk, client_addr)

    # Enviar sinal de fim
    server_socket.sendto(b"END", client_addr)

    print(f"Arquivo '{new_file_name}' enviado de volta para {client_addr}")