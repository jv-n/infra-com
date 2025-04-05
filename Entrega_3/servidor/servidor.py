import socket
import threading
from datetime import datetime
import uuid

# Configurações
serverPort = 12000
BUFFER_SIZE = 1024

# Estado do RDT
expected_seq = {}
send_seq = {}

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
server_socket.settimeout(1)

print(f"[SERVIDOR] Servidor pronto na porta {serverPort}")

# Função RDT de recepção
def rdt_recvfrom():
    while True:
        try:
            data, addr = server_socket.recvfrom(BUFFER_SIZE)
        except socket.timeout:
            continue

        seq_num = data[0]
        payload = data[1:]


        if addr not in expected_seq:
            expected_seq[addr] = 0

        if seq_num == expected_seq[addr]:
            server_socket.sendto(f"ACK {seq_num}".encode(), addr)
            expected_seq[addr] = 1 - expected_seq[addr]
            return payload.decode(), addr
        else:
            server_socket.sendto(f"ACK {1 - expected_seq[addr]}".encode(), addr)
            continue

# Função RDT de envio
def rdt_sendto(message: str, addr):
    if addr not in send_seq:
        send_seq[addr] = 0

    packet = bytes([send_seq[addr]]) + message.encode()


    while True:
        server_socket.sendto(packet, addr)
        try:
            ack, _ = server_socket.recvfrom(BUFFER_SIZE)
            if ack.decode() == f"ACK {send_seq[addr]}":
                send_seq[addr] = 1 - send_seq[addr]
                return
        except socket.timeout:
            print(f"⚠️  Timeout: reenviando pacote para {addr}...")

# Manipuladores de comandos
def handle_login(addr, parts):
    if len(parts) < 2:
        rdt_sendto("Erro: comando 'login' requer um nome de usuário.", addr)
        return

    username = parts[1]
    if username in users_online:
        rdt_sendto(f"Erro: usuário {username} já está logado.", addr)
    else:
        clients[addr] = {
            "username": username,
            "login_time": datetime.now()
        }
        users_online.add(username)
        rdt_sendto(f"Usuário {username} logado com sucesso.", addr)
        print(f"[LOGIN] {username} ({addr}) logado.")

def handle_logout(addr, parts):
    client = clients.get(addr)
    if client:
        username = client['username']
        users_online.discard(username)
        clients.pop(addr)
        rdt_sendto(f"Logout do usuário {username} realizado com sucesso.", addr)
        print(f"[LOGOUT] {username} ({addr}) deslogado.")
    else:
        rdt_sendto("Erro: usuário não está logado.", addr)

def handle_list_cinners(addr, parts):
    if addr not in clients:
        rdt_sendto("Você precisa estar logado para usar esse comando.", addr)
        return

    if not users_online:
        rdt_sendto("Nenhum usuário está conectado no momento.", addr)
    else:
        lista = "\n".join(users_online)
        rdt_sendto(f"Usuários online:\n{lista}", addr)




def handle_create_group(addr, parts):
    client = clients.get(addr)
    if not client:
        rdt_sendto("Você precisa estar logado para criar um grupo.", addr)
        return

    if len(parts) < 2:
        rdt_sendto("Uso: create_group <nome_do_grupo>", addr)
        return

    username = client['username']
    group_name = parts[1]

    if group_name in groups and groups[group_name]['admin'] == username:
        rdt_sendto("Erro: você já criou um grupo com esse nome.", addr)
        return

    if group_name in groups:
        rdt_sendto("Erro: esse nome de grupo já está em uso.", addr)
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

    rdt_sendto(f"O grupo de nome {group_name} foi criado com sucesso!", addr)

def handle_delete_group(addr, parts):
    client = clients.get(addr)
    if not client:
        rdt_sendto("Você precisa estar logado para excluir um grupo.", addr)
        return

    if len(parts) < 2:
        rdt_sendto("Uso: delete_group <nome_do_grupo>", addr)
        return

    username = client['username']
    group_name = parts[1]

    group = groups.get(group_name)
    if not group:
        rdt_sendto("Grupo inexistente.", addr)
        return

    # Verifica se quem enviou o comando é o admin
    if group['admin'] != username:
        rdt_sendto("Apenas o administrador pode excluir o grupo.", addr)
        return

    # Notificar membros (endereços) que o grupo foi deletado
    for member_addr in group['members']:
        if member_addr == addr:
            continue  # não precisa notificar o admin
        msg = f"[{username}/{addr[0]}:{addr[1]}] O grupo '{group_name}' foi deletado pelo administrador."
        rdt_sendto(msg, member_addr)

        # Remove o grupo da lista de grupos do usuário
        member_client = clients.get(member_addr)
        if member_client:
            member_username = member_client['username']
            user_groups.get(member_username, set()).discard(group_name)
            member_admin = group['admin']
            user_groups.get(member_admin, set()).discard(group_name)

    # Remove o grupo da lista de grupos criados pelo admin
    created_groups.get(username, set()).discard(group_name)

    # Remove o grupo do dicionário principal
    groups.pop(group_name)

    rdt_sendto(f"Grupo '{group_name}' excluído com sucesso.", addr)

def handle_list_groups(addr, parts):
    client = clients.get(addr)
    if not client:
        rdt_sendto("Você precisa estar logado.", addr)
        return

    username = client['username']
    print("USERNAME: ", username)
    my_groups = user_groups.get(username, set())
    print("USERGROUPS", user_groups)
    print("MYGROUPS: ", my_groups)
    if not my_groups:
        rdt_sendto("Você não participa de nenhum grupo.", addr)
        return

    lines = []
    for g in my_groups:
        group = groups[g]
        lines.append(f"Grupo: {g}, Criado em: {group['created_at']}, Admin: {group['admin']}")

    rdt_sendto("\n".join(lines), addr)

def handle_list_mygroups(addr, parts):
    client = clients.get(addr)
    if not client:
        rdt_sendto("Você precisa estar logado.", addr)
        return

    username = client['username']
    my_created = created_groups.get(username, set())
    if not my_created:
        rdt_sendto("Você não criou nenhum grupo.", addr)
        return

    lines = [f"{g} - chave: {groups[g]['id']}" for g in my_created]
    rdt_sendto("\n".join(lines), addr)

def handle_leave(addr, parts):
    client = clients.get(addr)
    if not client:
        rdt_sendto("Você precisa estar logado.", addr)
        return

    if len(parts) < 2:
        rdt_sendto("Uso: leave <nome_do_grupo>", addr)
        return

    username = client['username']
    group_name = parts[1]
    print("GROUP NAME: ", group_name)
    group = groups.get(group_name)
    print("GROUP MEMBERS: ", group['members'])
    if not group or addr not in group['members']:
        rdt_sendto("Você não participa desse grupo.", addr)
        return

    group['members'].remove(addr)
    user_groups.get(username, set()).discard(group_name)

    for member in group['members']:
        if member:
            msg = f"[{username}/{addr[0]}:{addr[1]}] {username} saiu do grupo"
            rdt_sendto(msg, member)
    rdt_sendto(f"Você saiu do grupo {group_name}!", addr)

def handle_ban(addr, parts):
    client = clients.get(addr)
    if not client:
        rdt_sendto("Você precisa estar logado.", addr)
        return

    if len(parts) < 3:
        rdt_sendto("Uso: ban <nome_do_usuario> <nome_do_grupo>", addr)
        return

    admin = client['username']
    target = parts[1]
    group_name = parts[2]

    group = groups.get(group_name)
    print("GRUPO: ", group)
    if not group or group['admin'] != admin:
        rdt_sendto("Apenas o administrador pode banir membros do grupo.", addr)
        return
    t_addr = addr_by_username.get(target)
    print("TARGET NOVO: ", t_addr)
    if t_addr not in group['members']:
        rdt_sendto(f"{target} não é membro do grupo.", addr)
        return

    group['members'].remove(t_addr)
    print("MEMBERS: ", group['members'])
    group['banned'].add(t_addr)
    print("BANIDOS: ", group['banned'])
    user_groups.get(target, set()).discard(group_name)

    for member in group['members']:
        m_addr = addr_by_username.get(member)
        if m_addr:
            msg = f"{target} foi banido do grupo"
            rdt_sendto(msg, m_addr)

    target_addr = addr_by_username.get(target)
    if target_addr:
        msg = f"[{admin}/{addr[0]}:{addr[1]}] O administrador do grupo {group_name} o baniu"
        rdt_sendto(msg, target_addr)


def handle_list_friends(addr, parts):
    client = clients.get(addr)
    if not client:
        rdt_sendto("Você precisa estar logado para usar esse comando.", addr)
        return

    username = client['username']
    friends = following_map.get(username, set())

    if not friends:
        rdt_sendto("Você ainda não segue ninguém.", addr)
    else:
        lista = "\n".join(friends)
        rdt_sendto(f"Você está seguindo:\n{lista}", addr)

def handle_follow(addr, parts):
    client = clients.get(addr)
    if not client:
        rdt_sendto("Você precisa estar logado para seguir alguém.", addr)
        return

    if len(parts) < 2:
        rdt_sendto("Uso: follow <nome_do_usuario>", addr)
        return

    follower = client['username']
    target = parts[1]

    if target == follower:
        rdt_sendto("Você não pode seguir a si mesmo.", addr)
        return

    if target not in users_online:
        rdt_sendto(f"O usuário {target} não está online.", addr)
        return

    if target in following_map[follower]:
        rdt_sendto(f"Você já está seguindo {target}.", addr)
        return

    following_map[follower].add(target)
    rdt_sendto(f"{target} foi adicionado à sua lista de amigos seguidos.", addr)

    # Notifica quem foi seguido
    target_addr = addr_by_username.get(target)
    if target_addr:
        notify = f"Você foi seguido por <{follower}> / {addr[0]}:{addr[1]}"
        rdt_sendto(notify, target_addr)

def handle_unfollow(addr, parts):
    client = clients.get(addr)
    if not client:
        rdt_sendto("Você precisa estar logado para deixar de seguir alguém.", addr)
        return

    if len(parts) < 2:
        rdt_sendto("Uso: unfollow <nome_do_usuario>", addr)
        return

    follower = client['username']
    target = parts[1]

    if target not in following_map.get(follower, set()):
        rdt_sendto(f"Você não está seguindo {target}.", addr)
        return

    following_map[follower].discard(target)
    rdt_sendto(f"Você deixou de seguir {target}.", addr)

    # Notifica quem deixou de ser seguido
    target_addr = addr_by_username.get(target)
    if target_addr:
        notify = f"<{follower}> / {addr[0]}:{addr[1]} deixou de seguir você."
        rdt_sendto(notify, target_addr)

def handle_join(addr, parts):
    if len(parts) < 3:
        rdt_sendto("Uso: join <nome_do_grupo> <chave_grupo>", addr)
        return

    group_name = parts[1]
    group_key = parts[2]

    username = clients.get(addr)
    if not username:
        rdt_sendto("Você precisa estar logado para entrar em um grupo.", addr)
        return

    group = groups.get(group_name)
    if not group:
        rdt_sendto("Grupo não encontrado.", addr)
        return

    if group["id"] != group_key:
        rdt_sendto("Chave incorreta.", addr)
        return

    if addr in group["members"]:
        rdt_sendto("Você já está no grupo.", addr)
        return
        
    if addr in group['banned']:
        rdt_sendto("Você foi banido deste grupo.", addr)
        return

    group["members"].add(addr)
    user_groups.setdefault(username["username"], set()).add(group_name)
    rdt_sendto(f"✅ Você entrou no grupo {group_name}", addr)

    join_message = f"[{username["username"]}/{addr[0]}:{addr[1]}] {username["username"]} acabou de entrar no grupo"
    for member_addr in group["members"]:
        if member_addr != addr:
            rdt_sendto(join_message, member_addr)

def handle_chat_group(addr, parts):
    if len(parts) < 4:
        rdt_sendto("Uso: chat_group <nome_do_grupo> <chave_grupo> <mensagem>", addr)
        return

    group_name = parts[1]
    group_key = parts[2]
    message = ' '.join(parts[3:])

    username = clients.get(addr)
    if not username:
        rdt_sendto("Você precisa estar logado para entrar em um grupo.", addr)
        return

    group = groups.get(group_name)
    if not group:
        rdt_sendto("Grupo não encontrado.", addr)
        return

    if group["id"] != group_key:
        rdt_sendto("Chave incorreta.", addr)
        return

    if addr in group["members"]:
        for member in group['members']:
            if member not in group['banned']:  # Verificação se o membro está banido
                msg = f"[{username}/{addr[0]}:{addr[1]}]: {message}"
                rdt_sendto(msg, member)  # Envia a mensagem para o membro não banido
        rdt_sendto(f"Mensagem enviada", addr)
        return

def handle_chat_friend(addr, parts):
    if len(parts) < 3:
        rdt_sendto("Uso: chat_friend <nome_do_amigo> <mensagem>", addr)
        return

    friend_name = parts[1]
    message = ' '.join(parts[2:])


    client = clients.get(addr)
    if not client:
        rdt_sendto("Você precisa estar logado para enviar mensagens.", addr)
        return
    
    username = client["username"]

    amigos = following_map.get(username)
    if not amigos or friend_name not in amigos:
        rdt_sendto(f"{friend_name} não está na sua lista de amigos.", addr)
        return

    destinatario_addr = addr_by_username.get(friend_name)
    if not destinatario_addr:
        rdt_sendto(f"{friend_name} não está online.", addr)
        return

    msg = f"[{username}/{addr[0]}:{addr[1]} -> {friend_name}]: {message}"
    rdt_sendto(msg, destinatario_addr)

    rdt_sendto(f"Mensagem enviada para {friend_name}.", addr)





# Comandos disponíveis
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
    "join": handle_join,
    "chat_group": handle_chat_group,
    "chat_friend": handle_chat_friend
}

# Thread de escuta de comandos
def commandrcv():
    while True:
        try:
            message, addr = rdt_recvfrom()
            parts = message.strip().split()
            if not message:
                continue

            command = parts[0].lower()
            print(f"[COMANDO] {command} recebido de {addr}")

            handler = handlers.get(command)
            if handler:
                handler(addr, parts)
            else:
                rdt_sendto("Erro: comando desconhecido.", addr)

        except Exception as e:
            print(f"[ERRO] {e}")
            try:
                rdt_sendto(f"Erro interno: {str(e)}", addr)
            except:
                pass

# Iniciar thread do servidor
threading.Thread(target=commandrcv, daemon=True).start()

# Manter o servidor ativo
try:
    while True:
        pass
except KeyboardInterrupt:
    print("\n[ENCERRANDO] Servidor encerrado.")
