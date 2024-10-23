import socket
import typer
import os

app = typer.Typer()

@app.command()
def send_file(host: str, port: int, file_path: str):
    """Start a client that sends a file to the server."""

    if not os.path.exists(file_path):
        typer.secho(f"File not found: {file_path}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
                
    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)

    try:

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect((host, port))

            typer.secho(f"Connected to {host}:{port}", fg=typer.colors.GREEN)

            encoded_filename = filename.encode('utf-8')

            client_socket.send(str(len(encoded_filename)).encode('utf-8').zfill(4))
            client_socket.send(encoded_filename)
            client_socket.send(str(file_size).encode('utf-8').zfill(16))

            with open(file_path, 'rb') as file:
                typer.echo(f"Sending {filename} ({file_size}) to {host}:{port}")
                readed_bytes = 0

                while (readed_bytes < file_size):
                    data = file.read(4096)
                    client_socket.sendall(data)
                    readed_bytes += len(data)

                    if (readed_bytes >= file_size):
                        typer.echo(f"Sent {readed_bytes} bytes of {file_size} bytes")
                        break

                typer.secho(f"File {filename} sent successfully", fg=typer.colors.GREEN)
                answear = client_socket.recv(2)

                if answear != b"OK":
                    typer.secho("Server did not receive the file", fg=typer.colors.RED, err=True)
                    raise typer.Exit(code=1)
                
                typer.secho("Server received the file", fg=typer.colors.GREEN)

    except (socket.error, ConnectionRefusedError) as e:
        typer.secho(f"Error of connection: {str(e)}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    
    except Exception as e:
        typer.secho(f"Unknown error: {str(e)}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
                    

if __name__ == "__main__":
    app()