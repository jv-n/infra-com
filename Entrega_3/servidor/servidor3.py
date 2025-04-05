import socket
import threading
import time

clients = {}
users_online = set()
friendships = {}
groups = {}

def commandrcv(address, server_socket):
    while True:
        try:
            data, addr = server_socket.recvfrom(1024)
            message = data.decode()
            if not message:
                continue

            command_parts = message.strip().split(" ")
            command = command_parts[0]
            username = clients.get(addr, None)

            if command == "login":
                username = command_parts[1]
                clients[addr] = username
                users_online.add(username)
                server_socket.sendto(f"Usuário {username} logado com sucesso.".encode(), addr)

            elif command == "login":
                if username:
                    users_online.discard(username)
                    clients.pop(addr)
                    server_socket.sendto(f"Logout do usuário {username} realizado com sucesso".encode(), addr)
        except Exception as e:
                server_socket.sendto(f"erro {str(e)}".enconde(), ,addr)
