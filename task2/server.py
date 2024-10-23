import threading
import socket
import typer
import tqdm
import time
import os


app = typer.Typer()

UPLOAD_DIR = "uploads"
counter_unknowns = 0

def recv_exactly(socket, num_bytes, file, bar):
    received_bytes = 0
    start_time = time.time()
    last_check_time = start_time
    last_data_received = 0

    while received_bytes < num_bytes:
        data = socket.recv(min(4096, num_bytes - received_bytes))

        if not data:
            raise ConnectionError("Connection closed by client")
        
        file.write(data)
        received_bytes += len(data)
        
        bar.update(len(data))
        current_time = time.time()
        
        elapsed_time = current_time - start_time
        elapsed_since_last_check = current_time - last_check_time

        if elapsed_since_last_check >= 1.0:
            instant_speed = (received_bytes - last_data_received) / elapsed_since_last_check
            average_speed = received_bytes / elapsed_time

            bar.set_postfix_str(f"Speed: cur -- {instant_speed / 1024:.2f} KB/s | avg -- {average_speed / 1024:.2f} KB/s")

            last_check_time = current_time
            last_data_received = received_bytes    

        time.sleep(0.001)
    
    return received_bytes

def handle_client(client_socket, address):
    try :
        typer.secho(f"Accepted connection from {address[0]}:{address[1]}", fg=typer.colors.GREEN)

        filename_length = int(client_socket.recv(4).decode('utf-8'))
        filename = client_socket.recv(filename_length).decode('utf-8')

        if not filename:
            typer.secho("Filename not received", fg=typer.colors.YELLOW, err=True)
            filename = "unknown"+str(counter_unknowns)
            counter_unknowns += 1

        file_size = int(client_socket.recv(16).decode('utf-8'))

        if file_size <= 0:
            typer.secho("File size not valid", fg=typer.colors.RED, err=True)
            return
        
        typer.echo(f"Receiving {filename} ({file_size} b) from {address[0]}:{address[1]}")

        file_path = os.path.join(UPLOAD_DIR, filename)
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        received_bytes = 0

        tqdm.tqdm

        with open(file_path, 'wb') as file:
            with tqdm.tqdm(desc=filename, total=file_size, unit='B', unit_scale=True, unit_divisor=1024, colour='green') as bar:
                received_bytes = recv_exactly(client_socket, file_size, file, bar)

        if received_bytes != file_size:
            raise ValueError(f"Received {received_bytes} bytes, but expected {file_size} bytes")

        typer.secho(f"File {filename} received successfully", fg=typer.colors.GREEN)
        client_socket.send(b"OK")

    except (ConnectionResetError, BrokenPipeError) as e:
        typer.secho(f"Connection error: {str(e)}", fg=typer.colors.RED, err=True)
    except ValueError as e:
        typer.secho(f"Data error: {str(e)}", fg=typer.colors.RED, err=True)
    except Exception as e:
        typer.secho(f"Unknown error: {str(e)}", fg=typer.colors.RED, err=True)
    finally:
        client_socket.close()
        typer.echo(f"Connection with {address[0]}:{address[1]} closed")

@app.command()
def start_server(port: int):
    """Start a server that receives files from clients."""
    
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('', port))
        server_socket.listen(5)

        typer.secho(f"Server started at port {port}", fg=typer.colors.GREEN)

        while True:
            try:
                client_socket, address = server_socket.accept()
                client_thread = threading.Thread(target=handle_client, args=(client_socket, address))
                client_thread.start()
            except socket.error as e:
                typer.secho(f"Error of connection: {str(e)}", fg=typer.colors.RED, err=True)
    except Exception as e:
        typer.secho(f"Unknown error: {str(e)}", fg=typer.colors.RED, err=True)
    finally:
        server_socket.close()
        typer.echo("Server stopped")


if __name__ == "__main__":
    app()
