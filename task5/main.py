from typing_extensions import Annotated
from proxy import Socks5Server

import typer

app = typer.Typer()

@app.command()
def start_server(port: Annotated[int, typer.Argument(help="Which should use")] = 1080):
    """Start the server"""

    server = Socks5Server(port)
    server.start()

if __name__ == "__main__":
    app()
