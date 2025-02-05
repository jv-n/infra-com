import socket

def main(host="localhost", port=23):

    adrr = (host, port)
    dest = (host, 1044)

    buffer_size = 1024
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    udp.bind(adrr)

    while True:

        data = "Olá server"
        udp.sendto(data.encode(), dest)

        with open(linkdata, 'rb') as f:
            l = f.read(buffer_size)
            while l:
                udp.sendto(l, dest)
                l = f.read(buffer_size)
            udp.sendto(b'', dest)

        _, servidor = udp.recvfrom(buffer_size)
        extention = extention.decode('utf-8')

        with open(linkdatarcv, 'wb') as f:
            while True:
                msg, servidor = udp.recvfrom(buffer_size)
                if not msg:
                    break
                f.write(msg)

    server.close()