import socket
import threading

clients = {}
users_online = set()

# Configuração do servidor
serverPort = 12000
BUFFER_SIZE = 1024

# Criando socket UDP
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(('', serverPort))

print(f"Servidor pronto na porta {serverPort}")

def commandrcv():
    while True:
        try:
            data, addr = server_socket.recvfrom(BUFFER_SIZE)
            message = data.decode().strip()
            if not message:
                continue

            command_parts = message.split(" ")
            command = command_parts[0]
            username = clients.get(addr, None)

            if command == "login":
                username = command_parts[1]
                if username in users_online:
                    server_socket.sendto(f"Erro: usuário {username} já está logado.".encode(), addr)
                else:
                    clients[addr] = username
                    users_online.add(username)
                    server_socket.sendto(f"Usuário {username} logado com sucesso.".encode(), addr)

            elif command == "logout":
                if username:
                    users_online.discard(username)
                    clients.pop(addr)
                    server_socket.sendto(f"Logout do usuário {username} realizado com sucesso.".encode(), addr)
                else:
                    server_socket.sendto("Erro: usuário não está logado.".encode(), addr)

        except Exception as e:
            server_socket.sendto(f"Erro: {str(e)}".encode(), addr)

# Rodando o servidor em uma thread
threading.Thread(target=commandrcv, daemon=True).start()

# Mantém o servidor vivo
while True:
    pass
