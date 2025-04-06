import socket
import threading
import random
import time

BUFFER_SIZE = 1024
LOSS_PROBABILITY = 0.1
server_address = ('127.0.0.1', 12345)
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

seq_num_send = 0
seq_num_recv = 0

ack_lock = threading.Lock()
last_ack_received = None  # usado para checar ACKs recebidos

LOSS_PROBABILITY = 0.1  # simulação de perda
BUFFER_SIZE = 1024
def rdt_send(sock, addr, msg):
    global seq_num_send, last_ack_received

    seq = seq_num_send
    packet = f"{seq}|".encode('utf-8') + msg

    retries = 0
    max_retries = 10
    timeout = 1  # segundos

    while retries < max_retries:
        if random.random() < LOSS_PROBABILITY:
            print("[X] Pacote perdido (simulado)")
        else:
            sock.sendto(packet, addr)
            print(f"[>] Enviado seq={seq} para {addr}")

        # Espera por ACK no tempo configurado
        start = time.time()
        while time.time() - start < timeout:
            with ack_lock:
                if last_ack_received == seq:
                    print(f"[✓] ACK{seq} recebido de {addr}")
                    seq_num_send = 1 - seq
                    last_ack_received = None
                    return
            time.sleep(0.05)

        print("Timeout, reenviando...")
        retries += 1

    print("[✖] Falha após muitas tentativas.")

def rdt_receive_thread(sock):
    global seq_num_recv, last_ack_received

    while True:
        try:
            data, addr = sock.recvfrom(BUFFER_SIZE)

            # Verifica se é ACK
            if data.startswith(b"ACK"):
                ack_num = int(data.decode('utf-8')[3:])
                with ack_lock:
                    last_ack_received = ack_num
                continue

            # Trata mensagem normal
            if b'|' not in data:
                continue

            header, msg = data.split(b'|', 1)
            recv_seq_num = int(header.decode('utf-8'))

            if recv_seq_num == seq_num_recv:
                sock.sendto(f"ACK{recv_seq_num}".encode('utf-8'), addr)
                seq_num_recv = 1 - seq_num_recv
                print(f"{msg.decode('utf-8')}\n> ", end='', flush=True)
            else:
                ack_to_resend = 1 - seq_num_recv
                sock.sendto(f"ACK{ack_to_resend}".encode('utf-8'), addr)

        except socket.timeout:
            continue  # só ignora timeouts
        except Exception as e:
            print(f"[Erro RDT Thread]: {e}")

# Inicia thread de recepção
threading.Thread(target=rdt_receive_thread, args=(client_socket,), daemon=True).start()

# Interface do usuário
print("=== ChatCin UDP ===")
print("Comandos disponíveis:")
print(" - login <nome>")
print(" - logout")
print(" - follow <nome>")
print(" - unfollow <nome>")
print(" - list:cinners")
print(" - create_group <nome>")
print(" - delete_group <nome>")
print(" - list:groups") 
print(" - list:mygroups")
print(" - leave <nome_do_grupo>")
print(" - ban <usuario> <grupo>") 
print(" - join <nome_do_grupo> <chave_grupo>")
print(" - chat_group <nome_do_grupo> <chave_grupo> <mensagem>") 
print(" - chat_friend <nome_do_amigo> <mensagem>") 
print(" - /exit para sair")


try:
    while True:
        command = input("> ").strip()
        if command == "/exit":
            break
        rdt_send(client_socket, server_address, command.encode('utf-8'))
except KeyboardInterrupt:
    print("\nSaindo...")

client_socket.close()
print("Conexão encerrada.")
