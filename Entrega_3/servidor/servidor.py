import socket
import threading
from datetime import datetime
import uuid

# Configurações
serverPort = 12000
BUFFER_SIZE = 1024

# Estruturas de controle
clients = {}        # addr -> { username, login_time }
users_online = set()
addr_by_username = {}  # username -> addr
following_map = {}     # username -> set of usernames being followed
groups = {}            # group_name -> { id, admin, created_at, members, banned }
user_groups = {}       # username -> set of group names
created_groups = {}    # username -> set of group names criados

# Criando socket UDP
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(('', serverPort))

print(f"Servidor pronto na porta {serverPort}")

# --- Funções de Grupo ---

def handle_create_group(addr, parts):
    client = clients.get(addr)
    if not client:
        server_socket.sendto("Você precisa estar logado para criar um grupo.".encode(), addr)
        return

    if len(parts) < 2:
        server_socket.sendto("Uso: create_group <nome_do_grupo>".encode(), addr)
        return

    username = client['username']
    group_name = parts[1]

    if group_name in groups and groups[group_name]['admin'] == username:
        server_socket.sendto("Erro: você já criou um grupo com esse nome.".encode(), addr)
        return

    if group_name in groups:
        server_socket.sendto("Erro: esse nome de grupo já está em uso.".encode(), addr)
        return

    group_id = str(uuid.uuid4())[:8]
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    groups[group_name] = {
        "id": group_id,
        "admin": username,
        "created_at": created_at,
        "members": {addr},
        "banned": set()
    }

    user_groups.setdefault(username, set()).add(group_name)
    created_groups.setdefault(username, set()).add(group_name)

    server_socket.sendto(f"O grupo de nome {group_name} foi criado com sucesso!".encode(), addr)

def handle_delete_group(addr, parts):
    client = clients.get(addr)
    if not client:
        server_socket.sendto("Você precisa estar logado para excluir um grupo.".encode(), addr)
        return

    if len(parts) < 2:
        server_socket.sendto("Uso: delete_group <nome_do_grupo>".encode(), addr)
        return

    username = client['username']
    group_name = parts[1]

    group = groups.get(group_name)
    if not group:
        server_socket.sendto("Grupo inexistente.".encode(), addr)
        return

    if group['admin'] != username:
        server_socket.sendto("Apenas o administrador pode excluir o grupo.".encode(), addr)
        return

    # Notificar membros
    for member in group['members']:
        if member == username:
            continue
        m_addr = addr_by_username.get(member)
        if m_addr:
            msg = f"[{username}/{addr[0]}:{addr[1]}] O grupo {group_name} foi deletado pelo administrador"
            server_socket.sendto(msg.encode(), m_addr)

    # Limpar
    for member in group['members']:
        user_groups.get(member, set()).discard(group_name)

    created_groups.get(username, set()).discard(group_name)
    groups.pop(group_name)
    server_socket.sendto(f"Grupo {group_name} excluído com sucesso.".encode(), addr)

def handle_list_groups(addr, parts):
    client = clients.get(addr)
    if not client:
        server_socket.sendto("Você precisa estar logado.".encode(), addr)
        return

    username = client['username']
    my_groups = user_groups.get(username, set())
    if not my_groups:
        server_socket.sendto("Você não participa de nenhum grupo.".encode(), addr)
        return

    lines = []
    for g in my_groups:
        group = groups[g]
        lines.append(f"Grupo: {g}, Criado em: {group['created_at']}, Admin: {group['admin']}")

    server_socket.sendto("\n".join(lines).encode(), addr)

def handle_list_mygroups(addr, parts):
    client = clients.get(addr)
    if not client:
        server_socket.sendto("Você precisa estar logado.".encode(), addr)
        return

    username = client['username']
    my_created = created_groups.get(username, set())
    if not my_created:
        server_socket.sendto("Você não criou nenhum grupo.".encode(), addr)
        return

    lines = [f"{g} - chave: {groups[g]['id']}" for g in my_created]
    server_socket.sendto("\n".join(lines).encode(), addr)

def handle_leave(addr, parts):
    client = clients.get(addr)
    if not client:
        server_socket.sendto("Você precisa estar logado.".encode(), addr)
        return

    if len(parts) < 2:
        server_socket.sendto("Uso: leave <nome_do_grupo>".encode(), addr)
        return

    username = client['username']
    group_name = parts[1]
    group = groups.get(group_name)

    if not group or username not in group['members']:
        server_socket.sendto("Você não participa desse grupo.".encode(), addr)
        return

    group['members'].remove(username)
    user_groups.get(username, set()).discard(group_name)

    for member in group['members']:
        m_addr = addr_by_username.get(member)
        if m_addr:
            msg = f"[{username}/{addr[0]}:{addr[1]}] {username} saiu do grupo"
            server_socket.sendto(msg.encode(), m_addr)

def handle_ban(addr, parts):
    client = clients.get(addr)
    if not client:
        server_socket.sendto("Você precisa estar logado.".encode(), addr)
        return

    if len(parts) < 3:
        server_socket.sendto("Uso: ban <nome_do_usuario> <nome_do_grupo>".encode(), addr)
        return

    admin = client['username']
    target = parts[1]
    group_name = parts[2]

    group = groups.get(group_name)
    if not group or group['admin'] != admin:
        server_socket.sendto("Apenas o administrador pode banir membros do grupo.".encode(), addr)
        return

    if target not in group['members']:
        server_socket.sendto(f"{target} não é membro do grupo.".encode(), addr)
        return

    group['members'].discard(target)
    group['banned'].add(target)
    user_groups.get(target, set()).discard(group_name)

    for member in group['members']:
        m_addr = addr_by_username.get(member)
        if m_addr:
            msg = f"{target} foi banido do grupo"
            server_socket.sendto(msg.encode(), m_addr)

    target_addr = addr_by_username.get(target)
    if target_addr:
        msg = f"[{admin}/{addr[0]}:{addr[1]}] O administrador do grupo {group_name} o baniu"
        server_socket.sendto(msg.encode(), target_addr)

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

def handle_join(addr, parts):
    if len(parts) < 3:
        server_socket.sendto("Uso: join <nome_do_grupo> <chave_grupo>".encode(), addr)
        return

    group_name = parts[1]
    group_key = parts[2]

    username = clients.get(addr)
    print("USUARIO: ",username)
    if not username:
        server_socket.sendto("Você precisa estar logado para entrar em um grupo.".encode(), addr)
        return

    group = groups.get(group_name)
    if not group:
        server_socket.sendto("Grupo não encontrado.".encode(), addr)
        return

    if group["id"] != group_key:
        server_socket.sendto("Chave incorreta.".encode(), addr)
        return

    if addr in group["members"]:
        server_socket.sendto("Você já está no grupo.".encode(), addr)
        return

    print("MEMBROS ANTES: ",group["members"])

    group["members"].add(addr)

    print("MEMBROS DEPOIS: ",group["members"])
    server_socket.sendto(f"✅ Você entrou no grupo {group_name}".encode(), addr)

    join_message = f"[{username["username"]}/{addr[0]}:{addr[1]}] {username["username"]} acabou de entrar no grupo"
    for member_addr in group["members"]:
        if member_addr != addr:
            server_socket.sendto(join_message.encode(), member_addr)


handlers = {
    "login": handle_login,
    "logout": handle_logout,
    "list:cinners": handle_list_cinners,
    "list:friends": handle_list_friends,
    "follow": handle_follow,
    "unfollow": handle_unfollow,
    "create_group": handle_create_group,
    "delete_group": handle_delete_group,
    "list:groups": handle_list_groups,
    "list:mygroups": handle_list_mygroups,
    "leave": handle_leave,
    "ban": handle_ban,
    "join": handle_join
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
