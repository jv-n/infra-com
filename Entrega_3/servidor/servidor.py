import socket
import random
from datetime import datetime
import uuid

# Configurações
BUFFER_SIZE = 1024
LOSS_PROBABILITY = 0
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(('localhost', 12345))
print("Servidor RDT iniciado...")

# Estado
db_clients = {}        # addr -> { username, login_time }
users_online = set()
addr_by_username = {}  # username -> addr
following_map = {}     # username -> set of usernames being followed
groups = {}            # group_name -> { id, admin, created_at, members, banned }
user_groups = {}       # username -> set of group names
created_groups = {}    # username -> set of group names criados

# Estado de sequência por cliente
seq_num_send_map = {}  # addr -> seq_num_send
seq_num_recv_map = {}  # addr -> seq_num_recv

# ========= RDT por cliente =========
def rdt_send(sock, addr, msg):
    seq_num_send = seq_num_send_map.get(addr, 0)

    if random.random() < LOSS_PROBABILITY:
        print("[X] Pacote perdido (simulado)")
        return

    packet = f"{seq_num_send}|".encode('utf-8') + msg
    sock.sendto(packet, addr)

    while True:
        ack_data, _ = sock.recvfrom(BUFFER_SIZE)
        if ack_data == f"ACK{seq_num_send}".encode('utf-8'):
            print(f"[✓] ACK{seq_num_send} recebido de {addr}")
            seq_num_send_map[addr] = 1 - seq_num_send
            break
        else:
            print("[!] ACK incorreto, aguardando o correto...")

def rdt_receive(sock):
    while True:
        data, addr = sock.recvfrom(BUFFER_SIZE)
        if b'|' not in data:
            continue
        header, msg = data.split(b'|', 1)
        recv_seq_num = int(header.decode('utf-8'))
        expected = seq_num_recv_map.get(addr, 0)

        if recv_seq_num == expected:
            sock.sendto(f"ACK{recv_seq_num}".encode('utf-8'), addr)
            seq_num_recv_map[addr] = 1 - expected
            return msg, addr
        else:
            sock.sendto(f"ACK{1 - expected}".encode('utf-8'), addr)

# ========= Comandos =========
def handle_login(addr, parts):
    if len(parts) < 2:
        msg = "Erro: comando 'login' requer um nome de usuário."
        rdt_send(server_socket, addr, msg.encode('utf-8'))
        return

    username = parts[1]
    if username in users_online:
        rdt_send(server_socket, addr, f"Erro: usuário {username} já está logado.".encode())
    else:
        db_clients[addr] = {
            "username": username,
            "login_time": datetime.now()
        }
        users_online.add(username)
        addr_by_username[username] = addr
        rdt_send(server_socket, addr, f"Usuário {username} logado com sucesso.".encode())
        print(f"[LOGIN] {username} ({addr}) logado.")

def handle_logout(addr):
    client = db_clients.get(addr)
    if client:
        username = client['username']
        users_online.discard(username)
        db_clients.pop(addr)
        addr_by_username.pop(username, None)
        rdt_send(server_socket, addr, f"Logout do usuário {username} realizado com sucesso.".encode())
        print(f"[LOGOUT] {username} ({addr}) deslogado.")
    else:
        msg = "Erro: usuário não está logado."
        rdt_send(server_socket, addr, msg.encode('utf-8'))

def handle_list_cinners(addr):
    if addr not in db_clients:
        msg = "Você precisa estar logado para usar esse comando."
        rdt_send(server_socket, addr,  msg.encode('utf-8'))
        return

    if not users_online:
        msg = "Nenhum usuário está conectado no momento."
        rdt_send(server_socket, addr, msg.encode('utf-8'))
    else:
        lista = "\n".join(users_online)
        rdt_send(server_socket, addr, f"Usuários online:\n{lista}".encode())

def handle_create_group(addr, parts):
    client = db_clients.get(addr)
    if not client:
        rdt_send(server_socket, addr, "Você precisa estar logado para criar um grupo.".encode())
        return

    if len(parts) < 2:
        rdt_send(server_socket, addr, "Uso: create_group <nome_do_grupo>".encode())
        return

    username = client['username']
    group_name = parts[1]

    if group_name in groups and groups[group_name]['admin'] == username:
        rdt_send(server_socket, addr, "Erro: você já criou um grupo com esse nome.".encode())
        return

    if group_name in groups:
        rdt_send(server_socket, addr, "Erro: esse nome de grupo já está em uso.".encode())
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

    rdt_send(server_socket, addr, f"O grupo de nome {group_name} foi criado com sucesso!".encode())

def handle_delete_group(addr, parts):
    client = db_clients.get(addr)
    if not client:
        rdt_send(server_socket, addr, "Você precisa estar logado para excluir um grupo.".encode())
        return

    if len(parts) < 2:
        rdt_send(server_socket, addr, "Uso: delete_group <nome_do_grupo>".encode())
        return

    username = client['username']
    group_name = parts[1]

    group = groups.get(group_name)
    if not group:
        rdt_send(server_socket, addr, "Grupo inexistente.".encode())
        return

    if group['admin'] != username:
        rdt_send(server_socket, addr, "Apenas o administrador pode excluir o grupo.".encode())
        return

    for member_addr in group['members']:
        if member_addr == addr:
            continue
        msg = f"[{username}/{addr[0]}:{addr[1]}] O grupo '{group_name}' foi deletado pelo administrador."
        rdt_send(server_socket, member_addr, msg.encode())

        member_client = db_clients.get(member_addr)
        if member_client:
            member_username = member_client['username']
            user_groups.get(member_username, set()).discard(group_name)
            user_groups.get(username, set()).discard(group_name)

    created_groups.get(username, set()).discard(group_name)
    groups.pop(group_name)

    rdt_send(server_socket, addr, f"Grupo '{group_name}' excluído com sucesso.".encode())

def handle_list_groups(addr, parts):
    client = db_clients.get(addr)
    if not client:
        rdt_send(server_socket, addr, "Você precisa estar logado.".encode())
        return

    username = client['username']
    my_groups = user_groups.get(username, set())
    if not my_groups:
        rdt_send(server_socket, addr, "Você não participa de nenhum grupo.".encode())
        return

    lines = []
    for g in my_groups:
        group = groups[g]
        lines.append(f"Grupo: {g}, Criado em: {group['created_at']}, Admin: {group['admin']}")

    rdt_send(server_socket, addr, "\n".join(lines).encode())

def handle_list_mygroups(addr, parts):
    client = db_clients.get(addr)
    if not client:
        rdt_send(server_socket, addr, "Você precisa estar logado.".encode())
        return

    username = client['username']
    my_created = created_groups.get(username, set())
    my_groups = user_groups.get(username, set())
    if not my_groups:
        rdt_send(server_socket, addr, "Você não participa de nenhum grupo.".encode())
        return
    if not my_created:
        rdt_send(server_socket, addr, "Você não criou nenhum grupo.".encode())
        return

    lines = [f"{g} - chave: {groups[g]['id']}" for g in my_created]
    rdt_send(server_socket, addr, "\n".join(lines).encode())

def handle_leave(addr, parts):
    client = db_clients.get(addr)
    if not client:
        rdt_send(server_socket, addr, "Você precisa estar logado.".encode())
        return

    if len(parts) < 2:
        rdt_send(server_socket, addr, "Uso: leave <nome_do_grupo>".encode())
        return

    username = client['username']
    group_name = parts[1]
    group = groups.get(group_name)
    if not group or addr not in group['members']:
        rdt_send(server_socket, addr, "Você não participa desse grupo.".encode())
        return

    group['members'].remove(addr)
    user_groups.get(username, set()).discard(group_name)

    for member in group['members']:
        if member:
            msg = f"[{username}/{addr[0]}:{addr[1]}] {username} saiu do grupo"
            rdt_send(server_socket, member, msg.encode())

    rdt_send(server_socket, addr, f"Você saiu do grupo {group_name}!".encode())

def handle_ban(addr, parts):
    client = db_clients.get(addr)
    if not client:
        rdt_send(server_socket, addr, "Você precisa estar logado.".encode())
        return

    if len(parts) < 3:
        rdt_send(server_socket, addr, "Uso: ban <nome_do_usuario> <nome_do_grupo>".encode())
        return

    admin = client['username']
    target = parts[1]
    group_name = parts[2]

    group = groups.get(group_name)
    if not group or group['admin'] != admin:
        rdt_send(server_socket, addr, "Apenas o administrador pode banir membros do grupo.".encode())
        return

    target_addr = addr_by_username.get(target)
    if target_addr not in group['members']:
        rdt_send(server_socket, addr, f"{target} não é membro do grupo.".encode())
        return

    group['members'].remove(target_addr)
    group['banned'].add(target_addr)
    user_groups.get(target, set()).discard(group_name)

    for member in group['members']:
        msg = f"{target} foi banido do grupo"
        rdt_send(server_socket, member, msg.encode())

    if target_addr:
        msg = f"[{admin}/{addr[0]}:{addr[1]}] O administrador do grupo {group_name} o baniu"
        rdt_send(server_socket, target_addr, msg.encode())

def handle_follow(addr, parts):
    client = db_clients.get(addr)
    if not client:
        rdt_send(server_socket, addr, "Você precisa estar logado para seguir alguém.".encode())
        return

    if len(parts) < 2:
        rdt_send(server_socket, addr, "Uso: follow <nome_do_usuario>".encode())
        return

    follower = client['username']
    target = parts[1]

    if target == follower:
        rdt_send(server_socket, addr, "Você não pode seguir a si mesmo.".encode())
        return

    if target not in users_online:
        rdt_send(server_socket, addr, f"O usuário {target} não está online.".encode())
        return

    if follower not in following_map:
        following_map[follower] = set()

    if target in following_map[follower]:
        rdt_send(server_socket, addr, f"Você já está seguindo {target}.".encode())
        return

    following_map[follower].add(target)
    rdt_send(server_socket, addr, f"{target} foi adicionado à sua lista de amigos seguidos.".encode())

    target_addr = addr_by_username.get(target)
    if target_addr:
        notify = f"Você foi seguido por <{follower}> / {addr[0]}:{addr[1]}"
        rdt_send(server_socket, target_addr, notify.encode())

def handle_unfollow(addr, parts):
    client = db_clients.get(addr)
    if not client:
        rdt_send(server_socket, addr, "Você precisa estar logado para deixar de seguir alguém.".encode())
        return

    if len(parts) < 2:
        rdt_send(server_socket, addr, "Uso: unfollow <nome_do_usuario>".encode())
        return

    follower = client['username']
    target = parts[1]

    if target not in following_map.get(follower, set()):
        rdt_send(server_socket, addr, f"Você não está seguindo {target}.".encode())
        return

    following_map[follower].discard(target)
    rdt_send(server_socket, addr, f"Você deixou de seguir {target}.".encode())

    target_addr = addr_by_username.get(target)
    if target_addr:
        notify = f"<{follower}> / {addr[0]}:{addr[1]} deixou de seguir você."
        rdt_send(server_socket, target_addr, notify.encode())

def handle_list_friends(addr, parts):
    client = db_clients.get(addr)
    if not client:
        rdt_send(server_socket, addr, "Você precisa estar logado para usar esse comando.".encode())
        return

    username = client['username']
    friends = following_map.get(username, set())

    if not friends:
        rdt_send(server_socket, addr, "Você ainda não segue ninguém.".encode())
    else:
        lista = "\n".join(friends)
        rdt_send(server_socket, addr, f"Você está seguindo:\n{lista}".encode())

def handle_join(addr, parts):
    if len(parts) < 3:
        rdt_send(server_socket, addr, "Uso: join <nome_do_grupo> <chave_grupo>".encode())
        return

    group_name = parts[1]
    group_key = parts[2]

    username = db_clients.get(addr)
    if not username:
        rdt_send(server_socket, addr, "Você precisa estar logado para entrar em um grupo.".encode())
        return

    group = groups.get(group_name)
    if not group:
        rdt_send(server_socket, addr, "Grupo não encontrado.".encode())
        return

    if group["id"] != group_key:
        rdt_send(server_socket, addr, "Chave incorreta.".encode())
        return

    if addr in group["members"]:
        rdt_send(server_socket, addr, "Você já está no grupo.".encode())
        return

    if addr in group['banned']:
        rdt_send(server_socket, addr, "Você foi banido deste grupo.".encode())
        return

    group["members"].add(addr)
    user_groups.setdefault(username["username"], set()).add(group_name)
    rdt_send(server_socket, addr, f"Você entrou no grupo {group_name}".encode())

    join_message = f"[{username['username']}/{addr[0]}:{addr[1]}] {username['username']} acabou de entrar no grupo"
    for member_addr in group["members"]:
        if member_addr != addr:
            rdt_send(server_socket, member_addr, join_message.encode())

def handle_chat_group(addr, parts):
    if len(parts) < 4:
        rdt_send(server_socket, addr, "Uso: chat_group <nome_do_grupo> <chave_grupo> <mensagem>".encode())
        return

    group_name = parts[1]
    group_key = parts[2]
    message = ' '.join(parts[3:])

    username = db_clients.get(addr)
    if not username:
        rdt_send(server_socket, addr, "Você precisa estar logado para entrar em um grupo.".encode())
        return

    group = groups.get(group_name)
    if not group:
        rdt_send(server_socket, addr, "Grupo não encontrado.".encode())
        return

    if group["id"] != group_key:
        rdt_send(server_socket, addr, "Chave incorreta.".encode())
        return

    if addr in group["members"]:
        for member in group['members']:
            if member not in group['banned']:
                msg = f"[{username['username']}/{addr[0]}:{addr[1]}]: {message}"
                rdt_send(server_socket, member, msg.encode())
        rdt_send(server_socket, addr, "Mensagem enviada".encode())
        return

def handle_chat_friend(addr, parts):
    if len(parts) < 3:
        rdt_send(server_socket, addr, "Uso: chat_friend <nome_do_amigo> <mensagem>".encode())
        return

    friend_name = parts[1]
    message = ' '.join(parts[2:])

    client = db_clients.get(addr)
    if not client:
        rdt_send(server_socket, addr, "Você precisa estar logado para enviar mensagens.".encode())
        return

    username = client["username"]
    amigos = following_map.get(username)
    if not amigos or friend_name not in amigos:
        rdt_send(server_socket, addr, f"{friend_name} não está na sua lista de amigos.".encode())
        return

    destinatario_addr = addr_by_username.get(friend_name)
    if not destinatario_addr:
        rdt_send(server_socket, addr, f"{friend_name} não está online.".encode())
        return

    msg = f"[{username}/{addr[0]}:{addr[1]} -> {friend_name}]: {message}"
    rdt_send(server_socket, destinatario_addr, msg.encode())
    rdt_send(server_socket, addr, f"Mensagem enviada para {friend_name}.".encode())

# ========= Processador de comandos =========
def processar_comando(msg_str, addr):
    partes = msg_str.strip().split()
    if not partes:
        rdt_send(server_socket, addr, b"Comando vazio.")
        return

    comando = partes[0]

    if comando == "login":
        handle_login(addr, partes)
    elif comando == "logout":
        handle_logout(addr)
    elif comando == "list:cinners":
        handle_list_cinners(addr)
    elif comando == "create_group":
        handle_create_group(addr, partes)
    elif comando == "delete_group":
        handle_delete_group(addr, partes)
    elif comando == "list:groups":
        handle_list_groups(addr, partes)
    elif comando == "list:mygroups":
        handle_list_mygroups(addr, partes)
    elif comando == "leave":
        handle_leave(addr, partes)
    elif comando == "ban":
        handle_ban(addr, partes)
    elif comando == "follow":
        handle_follow(addr, partes)
    elif comando == "unfollow":
        handle_unfollow(addr, partes)
    elif comando == "list:friends":
        handle_list_friends(addr, partes)
    elif comando == "join":
        handle_join(addr, partes)
    elif comando == "chat_group":
        handle_chat_group(addr, partes)
    elif comando == "chat_friend":
        handle_chat_friend(addr, partes)
    else:
        rdt_send(server_socket, addr, b"Comando desconhecido.")

# ========= Loop Principal =========
while True:
    try:
        msg, client_addr = rdt_receive(server_socket)
        msg_str = msg.decode('utf-8')
        print(f"[{client_addr}] -> {msg_str}")
        processar_comando(msg_str, client_addr)

    except Exception as e:
        print(f"Erro no servidor: {e}")
