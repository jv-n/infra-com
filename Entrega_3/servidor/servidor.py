import socket
import threading
from datetime import datetime

# Configurações
serverPort = 12000
BUFFER_SIZE = 1024

# Estruturas de controle
clients = {}        # addr -> { username, login_time }
users_online = set()

# Criando socket UDP
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(('', serverPort))

print(f"Servidor pronto na porta {serverPort}")

# Funções de manipulação de comandos
def handle_login(addr, parts):
    if len(parts) < 2:
        server_socket.sendto("Erro: comando 'login' requer um nome de usuário.".encode(), addr)
        return

    username = parts[1]
    if username in users_online:
        server_socket.sendto(f"Erro: usuário {username} já está logado.".encode(), addr)
    else:
        clients[addr] = {
            "username": username,
            "login_time": datetime.now()
        }
        users_online.add(username)
        server_socket.sendto(f"Usuário {username} logado com sucesso.".encode(), addr)
        print(f"[LOGIN] {username} ({addr})")

def handle_logout(addr, parts):
    client = clients.get(addr)
    if client:
        username = client['username']
        users_online.discard(username)
        clients.pop(addr)
        server_socket.sendto(f"Logout do usuário {username} realizado com sucesso.".encode(), addr)
        print(f"[LOGOUT] {username} ({addr})")
    else:
        server_socket.sendto("Erro: usuário não está logado.".encode(), addr)

def handle_status(addr, parts):
    client = clients.get(addr)
    if client:
        username = client['username']
        login_time = client['login_time'].strftime("%H:%M:%S")
        server_socket.sendto(f"Usuário: {username}, Logado desde: {login_time}".encode(), addr)
    else:
        server_socket.sendto("Você não está logado.".encode(), addr)

# Mapeamento de comandos para funções
handlers = {
    "login": handle_login,
    "logout": handle_logout,
    "status": handle_status
}

# Thread para escutar os comandos dos clientes
def commandrcv():
    while True:
        try:
            data, addr = server_socket.recvfrom(BUFFER_SIZE)
            message = data.decode().strip()
            if not message:
                continue

            parts = message.split()
            command = parts[0].lower()

            handler = handlers.get(command)
            if handler:
                handler(addr, parts)
            else:
                server_socket.sendto("Erro: comando desconhecido.".encode(), addr)

        except Exception as e:
            server_socket.sendto(f"Erro interno: {str(e)}".encode(), addr)

# Iniciar servidor em thread
threading.Thread(target=commandrcv, daemon=True).start()

# Manter o servidor rodando
try:
    while True:
        pass
except KeyboardInterrupt:
    print("\nServidor encerrado.")
