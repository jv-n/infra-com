import socket

# Definição da porta do servidor e do tamanho do buffer de recepção
serverPort = 12000
BUFFER_SIZE = 1024

# Criação do socket UDP
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Associa o socket a uma porta específica para escutar conexões
server_socket.bind(('', serverPort))

print(f"The server is ready to receive in {serverPort}")

while True:
    # Aguarda o recebimento do nome do arquivo do cliente
    file_name, client_addr = server_socket.recvfrom(BUFFER_SIZE)
    file_name = file_name.decode()  # Decodifica os bytes recebidos para string
    print(f"Received: {file_name} from {client_addr}")

    # Abre um arquivo localmente para salvar os dados recebidos do cliente
    with open(f"server_{file_name}", "wb") as file:
        while True:
            data, client_addr = server_socket.recvfrom(BUFFER_SIZE)
            if data == b"END":  # Se receber "END", termina a recepção
                break
            file.write(data)  # Escreve os dados no arquivo

    print(f"File received and saved as 'server_{file_name}'")

    # Define o novo nome do arquivo a ser enviado de volta ao cliente
    new_file_name = f"modified_{file_name}"

    # Envia o novo nome do arquivo ao cliente
    server_socket.sendto(new_file_name.encode(), client_addr)

    # Abre o arquivo salvo para leitura e envio de volta ao cliente
    with open(f"server_{file_name}", "rb") as file:
        while chunk := file.read(BUFFER_SIZE):  # Lê o arquivo em pedaços
            server_socket.sendto(chunk, client_addr)  # Envia cada pedaço ao cliente

    # Indica o fim da transmissão enviando "END"
    server_socket.sendto(b"END", client_addr)

    print(f"File '{new_file_name}' sent back to {client_addr}")
