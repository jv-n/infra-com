import socket

def main(host="localhost", port=23):
    # Define os endereços e portas do servidor e do destinatário
    addr = (host, port)  # Correção no nome da variável (antes era "adrr")
    dest = (host, 12000)  # Endereço do destinatário para envio de dados

    buffer_size = 1024  # Define o tamanho do buffer para a comunicação UDP
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Cria um socket UDP

    udp.bind(addr)  # Vincula o socket ao endereço e porta especificados

    # Definição das variáveis antes do uso
    linkdata = "data.txt"  # Caminho do arquivo a ser enviado
    linkdatarcv = "received_data.txt"  # Caminho do arquivo recebido

    while True:
        # Envia uma mensagem inicial para o servidor
        data = "Olá server"
        udp.sendto(data.encode(), dest)

        # Abre um arquivo para leitura e envia seus dados em blocos
        with open(linkdata, 'rb') as f:
            l = f.read(buffer_size)  # Lê um bloco do arquivo
            while l:
                udp.sendto(l, dest)  # Envia o bloco para o destino
                l = f.read(buffer_size)  # Lê o próximo bloco
            udp.sendto(b'', dest)  # Envia um sinal indicando o fim do arquivo

        # Aguarda uma resposta do servidor
        msg, servidor = udp.recvfrom(buffer_size)
        extension = msg.decode('utf-8')  # Correção: 'extension' agora está corretamente definida

        # Abre um arquivo para salvar os dados recebidos do servidor
        with open(linkdatarcv, 'wb') as f:
            while True:
                msg, servidor = udp.recvfrom(buffer_size)  # Recebe um bloco de dados
                if not msg:
                    break  # Encerra se não houver mais dados
                f.write(msg)  # Escreve os dados no arquivo

    udp.close()  # Correção: 'server.close()' foi substituído por 'udp.close()'
