from launart.service import Service


class AbstractAsgiService(Service):
    id = "http.asgi_runner"
    host: str
    port: int

    def __init__(self, host: str = "127.0.0.1", port: int = 8000):
        self.host = host
        self.port = port
