import socket
import threading
from datetime import datetime

# Configurações
serverPort = 12000
BUFFER_SIZE = 1024

# Estruturas de controle
clients = {}        # addr -> { username, login_time }
users_online = set()
addr_by_username = {}  # username -> addr
following_map = {}     # username -> set of usernames being followed

# Criando socket UDP
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(('', serverPort))

print(f"Servidor pronto na porta {serverPort}")

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
        addr_by_username[username] = addr
        users_online.add(username)
        following_map.setdefault(username, set())
        server_socket.sendto(f"Usuário {username} logado com sucesso.".encode(), addr)
        print(f"[LOGIN] {username} ({addr})")

def handle_logout(addr, parts):
    client = clients.get(addr)
    if client:
        username = client['username']
        users_online.discard(username)
        clients.pop(addr)
        addr_by_username.pop(username, None)
        following_map.pop(username, None)
        server_socket.sendto(f"Logout do usuário {username} realizado com sucesso.".encode(), addr)
        print(f"[LOGOUT] {username} ({addr})")
    else:
        server_socket.sendto("Erro: usuário não está logado.".encode(), addr)

def handle_list_cinners(addr, parts):
    if addr not in clients:
        server_socket.sendto("Você precisa estar logado para usar esse comando.".encode(), addr)
        return

    if not users_online:
        server_socket.sendto("Nenhum usuário está conectado no momento.".encode(), addr)
    else:
        lista = "\n".join(users_online)
        server_socket.sendto(f"Usuários online:\n{lista}".encode(), addr)

def handle_list_friends(addr, parts):
    client = clients.get(addr)
    if not client:
        server_socket.sendto("Você precisa estar logado para usar esse comando.".encode(), addr)
        return

    username = client['username']
    friends = following_map.get(username, set())

    if not friends:
        server_socket.sendto("Você ainda não segue ninguém.".encode(), addr)
    else:
        lista = "\n".join(friends)
        server_socket.sendto(f"Você está seguindo:\n{lista}".encode(), addr)

def handle_follow(addr, parts):
    client = clients.get(addr)
    if not client:
        server_socket.sendto("Você precisa estar logado para seguir alguém.".encode(), addr)
        return

    if len(parts) < 2:
        server_socket.sendto("Uso: follow <nome_do_usuario>".encode(), addr)
        return

    follower = client['username']
    target = parts[1]

    if target == follower:
        server_socket.sendto("Você não pode seguir a si mesmo.".encode(), addr)
        return

    if target not in users_online:
        server_socket.sendto(f"O usuário {target} não está online.".encode(), addr)
        return

    if target in following_map[follower]:
        server_socket.sendto(f"Você já está seguindo {target}.".encode(), addr)
        return

    following_map[follower].add(target)
    server_socket.sendto(f"{target} foi adicionado à sua lista de amigos seguidos.".encode(), addr)

    # Notifica quem foi seguido
    target_addr = addr_by_username.get(target)
    if target_addr:
        notify = f"Você foi seguido por <{follower}> / {addr[0]}:{addr[1]}"
        server_socket.sendto(notify.encode(), target_addr)

def handle_unfollow(addr, parts):
    client = clients.get(addr)
    if not client:
        server_socket.sendto("Você precisa estar logado para deixar de seguir alguém.".encode(), addr)
        return

    if len(parts) < 2:
        server_socket.sendto("Uso: unfollow <nome_do_usuario>".encode(), addr)
        return

    follower = client['username']
    target = parts[1]

    if target not in following_map.get(follower, set()):
        server_socket.sendto(f"Você não está seguindo {target}.".encode(), addr)
        return

    following_map[follower].discard(target)
    server_socket.sendto(f"Você deixou de seguir {target}.".encode(), addr)

    # Notifica quem deixou de ser seguido
    target_addr = addr_by_username.get(target)
    if target_addr:
        notify = f"<{follower}> / {addr[0]}:{addr[1]} deixou de seguir você."
        server_socket.sendto(notify.encode(), target_addr)

# Mapeamento de comandos para funções
handlers = {
    "login": handle_login,
    "logout": handle_logout,
    "list:cinners": handle_list_cinners,
    "list:friends": handle_list_friends,
    "follow": handle_follow,
    "unfollow": handle_unfollow
}

# Thread para escutar comandos dos clientes
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

# Iniciar servidor
threading.Thread(target=commandrcv, daemon=True).start()

try:
    while True:
        pass
except KeyboardInterrupt:
    print("\nServidor encerrado.")
