import socket

serverPort = 12000
BUFFER_SIZE = 1024

server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(('', serverPort))

print (f"The server is ready to receive in {serverPort}")

while True:
    file_name, client_addr = server_socket.recvfrom(BUFFER_SIZE)
    file_name = file_name.decode()  
    print(f"receive: {file_name} from {client_addr}")

    with open(f"server_{file_name}", "wb") as file:
        while True:
            data, client_addr = server_socket.recvfrom(BUFFER_SIZE)
            if data == b"END": 
                break
            file.write(data)

    print(f"file receive and save as 'server_{file_name}'")

    new_file_name = f"modified_{file_name}"

    server_socket.sendto(new_file_name.encode(), client_addr)

    with open(f"server_{file_name}", "rb") as file:
        while chunk := file.read(BUFFER_SIZE):
            server_socket.sendto(chunk, client_addr)

    server_socket.sendto(b"END", client_addr)

    print(f"file '{new_file_name}' sent back to {client_addr}")
