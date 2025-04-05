import socket
import threading
from datetime import datetime

# Configurações
serverPort = 12000
BUFFER_SIZE = 1024

# Estruturas de controle
clients = {}         # addr -> { username, login_time }
users_online = set() # usernames logados
seguidores = {}      # username -> set(de quem está seguindo esse usuário)
amigos = {}          # username -> set(usuários que está seguindo)

# Criando socket UDP
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(('', serverPort))

print(f"Servidor pronto na porta {serverPort}")

def get_username(addr):
    return clients.get(addr, {}).get("username")

def get_address_by_username(username):
    for addr, data in clients.items():
        if data['username'] == username:
            return addr
    return None

# Comando: login
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
        seguidores.setdefault(username, set())
        amigos.setdefault(username, set())
        server_socket.sendto(f"Usuário {username} logado com sucesso.".encode(), addr)
        print(f"[LOGIN] {username} ({addr})")

# Comando: logout
def handle_logout(addr, parts):
    client = clients.get(addr)
    if client:
        username = client['username']
        users_online.discard(username)
        clients.pop(addr)
        seguidores.pop(username, None)
        amigos.pop(username, None)
        server_socket.sendto(f"Logout do usuário {username} realizado com sucesso.".encode(), addr)
        print(f"[LOGOUT] {username} ({addr})")
    else:
        server_socket.sendto("Erro: usuário não está logado.".encode(), addr)

# Comando: list:cinners
def handle_list_cinners(addr, parts):
    if addr not in clients:
        server_socket.sendto("Você precisa estar logado para usar esse comando.".encode(), addr)
        return

    if not users_online:
        server_socket.sendto("Nenhum usuário está conectado no momento.".encode(), addr)
    else:
        lista = "\n".join(users_online)
        server_socket.sendto(f"Usuários online:\n{lista}".encode(), addr)

# Comando: follow
def handle_follow(addr, parts):
    seguidor = get_username(addr)
    if not seguidor:
        server_socket.sendto("Você precisa estar logado para usar esse comando.".encode(), addr)
        return

    if len(parts) < 2:
        server_socket.sendto("Erro: comando 'follow' requer o nome de um usuário.".encode(), addr)
        return

    seguido = parts[1]
    if seguido == seguidor:
        server_socket.sendto("Você não pode se seguir.".encode(), addr)
        return

    if seguido not in users_online:
        server_socket.sendto(f"Usuário {seguido} não está online ou não existe.".encode(), addr)
        return

    if seguido in amigos[seguidor]:
        server_socket.sendto(f"Você já está seguindo {seguido}.".encode(), addr)
        return

    # Atualiza estruturas
    amigos[seguidor].add(seguido)
    seguidores[seguido].add(seguidor)

    server_socket.sendto(f"{seguido} foi adicionado à sua lista de amigos seguidos.".encode(), addr)

    seguido_addr = get_address_by_username(seguido)
    if seguido_addr:
        server_socket.sendto(
            f"Você foi seguido por <{seguidor}> / {addr[0]}:{addr[1]}".encode(),
            seguido_addr
        )

# Comando: unfollow
def handle_unfollow(addr, parts):
    seguidor = get_username(addr)
    if not seguidor:
        server_socket.sendto("Você precisa estar logado para usar esse comando.".encode(), addr)
        return

    if len(parts) < 2:
        server_socket.sendto("Erro: comando 'unfollow' requer o nome de um usuário.".encode(), addr)
        return

    seguido = parts[1]
    if seguido not in amigos[seguidor]:
        server_socket.sendto(f"Você não está seguindo {seguido}.".encode(), addr)
        return

    # Atualiza estruturas
    amigos[seguidor].discard(seguido)
    seguidores[seguido].discard(seguidor)

    server_socket.sendto(f"Você deixou de seguir {seguido}.".encode(), addr)

    seguido_addr = get_address_by_username(seguido)
    if seguido_addr:
        server_socket.sendto(
            f"<{seguidor}> / {addr[0]}:{addr[1]} deixou de seguir você.".encode(),
            seguido_addr
        )

# Mapeamento de comandos para funções
handlers = {
    "login": handle_login,
    "logout": handle_logout,
    "list:cinners": handle_list_cinners,
    "follow": handle_follow,
    "unfollow": handle_unfollow
}

# Thread para escutar comandos
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
            try:
                server_socket.sendto(f"Erro interno: {str(e)}".encode(), addr)
            except:
                pass

# Rodar servidor em thread
threading.Thread(target=commandrcv, daemon=True).start()

# Loop principal
try:
    while True:
        pass
except KeyboardInterrupt:
    print("\nServidor encerrado.")
