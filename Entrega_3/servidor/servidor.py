import socket
import threading
from datetime import datetime
import uuid  # Para gerar IDs únicos de grupo

# Configurações
serverPort = 12000
BUFFER_SIZE = 1024

# Estruturas de controle
clients = {}        # addr -> { username, login_time }
users_online = set()
addr_by_username = {}  # username -> addr
following_map = {}     # username -> set of usernames being followed
groups = {}            # group_name -> { id, admin, members, name }

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

        # Remover usuário dos grupos
        for group in groups.values():
            group['members'].discard(username)

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

def handle_create_group(addr, parts):
    client = clients.get(addr)
    if not client:
        server_socket.sendto("Você precisa estar logado para criar um grupo.".encode(), addr)
        return

    if len(parts) < 2:
        server_socket.sendto("Uso: create_group <nome_do_grupo>".encode(), addr)
        return

    group_name = parts[1]
    username = client['username']

    for g in groups.values():
        if g['admin'] == username and group_name == g['name']:
            server_socket.sendto("Erro: você já criou um grupo com esse nome.".encode(), addr)
            return

    group_id = str(uuid.uuid4())[:8]
    groups[group_name] = {
        'id': group_id,
        'admin': username,
        'members': {username},
        'name': group_name
    }

    server_socket.sendto(
        f"O grupo de nome <{group_name}> foi criado com sucesso! ID: {group_id}".encode(), addr
    )
    print(f"[CREATE GROUP] {username} criou o grupo '{group_name}' com ID {group_id}")

def handle_delete_group(addr, parts):
    client = clients.get(addr)
    if not client:
        server_socket.sendto("Você precisa estar logado para excluir um grupo.".encode(), addr)
        return

    if len(parts) < 2:
        server_socket.sendto("Uso: delete_group <nome_do_grupo>".encode(), addr)
        return

    group_name = parts[1]
    username = client['username']

    group = groups.get(group_name)
    if not group:
        server_socket.sendto("Erro: grupo não encontrado.".encode(), addr)
        return

    if group['admin'] != username:
        server_socket.sendto("Erro: apenas o administrador pode excluir o grupo.".encode(), addr)
        return

    members = group['members'] - {username}
    groups.pop(group_name)

    server_socket.sendto(
        f"O grupo '{group_name}' foi deletado com sucesso.".encode(), addr
    )

    for member in members:
        member_addr = addr_by_username.get(member)
        if member_addr:
            notify = f"[{username}/{addr[0]}:{addr[1]}] O grupo '{group_name}' foi deletado pelo administrador."
            server_socket.sendto(notify.encode(), member_addr)

    print(f"[DELETE GROUP] {username} excluiu o grupo '{group_name}'")

# Mapeamento de comandos para funções
handlers = {
    "login": handle_login,
    "logout": handle_logout,
    "list:cinners": handle_list_cinners,
    "list:friends": handle_list_friends,
    "follow": handle_follow,
    "unfollow": handle_unfollow,
    "create_group": handle_create_group,
    "delete_group": handle_delete_group
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
