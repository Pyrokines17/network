import threading
import select
import socket
import typer
import sys

# version with threading

chr_to_int = lambda x: x
encode_str = lambda x: x.encode()

BACKLOG = 128
SOCKS_TIMEOUT = 5
RESEND_TIMEOUT = 30
MAX_RECV_SIZE = 65536

VER = b'\x05'
METHOD = b'\x00'

SUCCESS = b'\x00'

SOCKS_FAIL = b'\x01'
NETWORK_FAIL = b'\x03'
HOST_FAIL = b'\x04'
REFUSED = b'\x05'
TTL_EXPIRED = b'\x06'
UNSUPPORTED_CMD = b'\x07'
UNSUPPORTED_ATYP = b'\x08'

UNASSIGNED = b'\x09'

ATYP_IPV4 = b'\x01'
ATYP_DOMAIN = b'\x03'
ATYP_IPV6 = b'\x04'

CMD_CONNECT = b'\x01'
CMD_BIND = b'\x02'
CMD_UDP = b'\x03'

class Socks5Server:
    def __init__(self, port):
        self.sock_send_buf = {}
        self.cli_dest_map = {}

        self.backlog = BACKLOG
        self.port = port
        self.host = ""
        
        self.cli_dest_map_lock = threading.Lock()

    def buf_recv(self, sock):
        target_sock = self.cli_dest_map[sock]

        try:
            buf = sock.recv(MAX_RECV_SIZE)
        except Exception as e:
            typer.secho(f"Error receiving data: {e}", fg=typer.colors.RED)

        if len(buf) == 0:
            self.flush_and_close_sock(sock)
        elif target_sock not in self.sock_send_buf:
            self.sock_send_buf[target_sock] = buf
        else:
            self.sock_send_buf[target_sock] = self.sock_send_buf[target_sock] + buf

    def buf_send(self, sock):
        if sock in self.sock_send_buf:
            try:
                bytes_sent = sock.send(self.sock_send_buf[sock])
            except Exception as e:
                typer.secho(f"Error sending data: {e}", fg=typer.colors.RED)
                
            self.sock_send_buf[sock] = self.sock_send_buf[sock][bytes_sent:]

    def flush_and_close_sock(self, sock, err_msg=None):
        if err_msg:
            typer.secho("Flush and close sock with error: " + err_msg, fg=typer.colors.RED)
        else:
            typer.secho("Flush and close sock", fg=typer.colors.CYAN)
        with self.cli_dest_map_lock:
            try:
                sec_sock = self.cli_dest_map.pop(sock)
                self.cli_dest_map.pop(sec_sock)
            except Exception as e:
                typer.secho(f"Error poping: {e}", fg=typer.colors.RED)
        try:
            sec_sock.send(self.sock_send_buf.pop(sec_sock, b''))
            sec_sock.close()
            sock.send(self.sock_send_buf.pop(sock, b''))
            sock.close()
        except Exception as e:
            typer.secho(f"Error flushing and closing sock: {e}", fg=typer.colors.RED)

    def establish_conn(self, sock):
        dest_host, dest_port = None, None

        try:
            ver = sock.recv(1)

            if ver != VER:
                typer.secho(f"Invalid version: {ver}", fg=typer.colors.RED)
                sock.sendall(VER + b'\xFF')
                sock.close()
                return None, None
            
            nmethods = sock.recv(1)
            numMethods = ord(nmethods)
            methods = []

            for _ in range(numMethods):
                methods.append(sock.recv(1))

            if METHOD not in methods:
                typer.secho("Method not supported", fg=typer.colors.RED)
                sock.sendall(VER + b'\xFF')
                sock.close()
                return None, None
            
            sock.sendall(VER + METHOD)
            ver = sock.recv(1)

            if ver != VER:
                typer.secho(f"Invalid version: {ver}", fg=typer.colors.RED)
                sock.sendall(VER + SOCKS_FAIL + b'\x00' + ATYP_IPV4 + b'\x00' * 6)
                sock.close()
                return None, None
            
            cmd, rsv, atyp = sock.recv(1), sock.recv(1), sock.recv(1)
            
            dst_addr = None
            dst_port = None

            if atyp == ATYP_IPV4:
                dst_addr, dst_port = sock.recv(4), sock.recv(2)
                dst_addr = '.'.join([str(ord(x)) for x in dst_addr])
            elif atyp == ATYP_DOMAIN:
                addr_len = ord(sock.recv(1))
                dst_addr, dst_port = sock.recv(addr_len), sock.recv(2)
                dst_addr = ''.join([chr(chr_to_int(x)) for x in dst_addr])
            elif atyp == ATYP_IPV6:
                dst_addr, dst_port = sock.recv(16), sock.recv(2)
                tmp_addr = []

                for i in range(len(dst_addr) // 2):
                    tmp_addr.append(chr(dst_addr[2 * i] * 256 + dst_addr[2 * i + 1]))
                
                dst_addr = ':'.join(tmp_addr)
            
            dst_port = chr_to_int(dst_port[0]) * 256 + chr_to_int(dst_port[1])
            server_sock = sock
            server_ip = ''.join([chr(int(x)) for x in socket.gethostbyname(self.host).split('.')])

            if cmd == CMD_BIND:
                typer.secho("Command BIND not supported", fg=typer.colors.RED)
                sock.close()
            elif cmd == CMD_UDP:
                typer.secho("Command UDP not supported", fg=typer.colors.RED)
                sock.close()
            elif cmd == CMD_CONNECT:
                sock.sendall(VER + SUCCESS + b'\x00' + ATYP_IPV4 + 
                             encode_str(server_ip + chr(self.port // 256) + chr(self.port % 256)))
                dest_host, dest_port = dst_addr, dst_port
            else:
                typer.secho("Unsupported/unknown command", fg=typer.colors.RED)
                sock.sendall(VER + UNSUPPORTED_CMD + 
                             encode_str(server_ip + chr(self.port // 256) + chr(self.port % 256)))
                sock.close()

        except Exception as e:
            typer.secho(f"Error establishing connection: {e}", fg=typer.colors.RED)
            
        return dest_host, dest_port
    
    def handle_conn(self, cli_sock, addr):
        typer.secho(f"Connection from {addr}", fg=typer.colors.CYAN)
        cli_sock.settimeout(SOCKS_TIMEOUT)

        dest_host, dest_port = self.establish_conn(cli_sock)

        if None in (dest_host, dest_port):
            cli_sock.close()
            return None
        
        typer.secho(f"Connecting to {dest_host}:{dest_port}", fg=typer.colors.CYAN)

        dest_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        dest_sock.settimeout(SOCKS_TIMEOUT)

        try:
            dest_sock.connect((dest_host, dest_port))
        except Exception as e:
            typer.secho(f"Error connecting to dest {dest_host}:{dest_port}: {e}", fg=typer.colors.RED)
            cli_sock.close()
            return None
        
        typer.secho(f"Connected to {dest_host}:{dest_port}", fg=typer.colors.CYAN)

        cli_sock.settimeout(RESEND_TIMEOUT)
        
        cli_sock.setblocking(False)
        dest_sock.setblocking(False)

        with self.cli_dest_map_lock:
            self.cli_dest_map[cli_sock] = dest_sock
            self.cli_dest_map[dest_sock] = cli_sock

        typer.secho(f"Connection established between {addr} and {dest_host}:{dest_port}", fg=typer.colors.GREEN)

    def accept_conn(self):
        (cli, addr) = self.server_sock.accept()
        thr = threading.Thread(target=self.handle_conn, args=(cli, addr))
        thr.daemon = True
        thr.start()

    def start(self):
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.server_sock.bind((self.host, self.port))
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.setblocking(False);
        
        self.server_sock.listen(self.backlog)

        typer.secho(f"Server started on port {self.port}", fg=typer.colors.GREEN)

        while True:
            conn_socks = list(self.cli_dest_map.keys()) 
            in_socks = [self.server_sock] + conn_socks
            out_socks = conn_socks
            
            readable, writable, exceptional = select.select(in_socks, out_socks, [])

            for sock in readable:
                if sock == self.server_sock:
                    self.accept_conn()
                else:
                    try:
                        self.buf_recv(sock)
                    except Exception as e:
                        self.flush_and_close_sock(sock, str(e))

            for sock in writable:
                try:
                    self.buf_send(sock)
                except Exception as e:
                    self.flush_and_close_sock(sock, str(e))

            for sock in exceptional:
                if sock == self.server_sock:
                    typer.secho("Exceptional condition on server socket", fg=typer.colors.RED)

                    for conn in conn_socks:
                        conn.close()

                    self.server_sock.close()
                    sys.exit(1)
                else:
                    self.flush_and_close_sock(sock, "Unexpected exceptional condition")
