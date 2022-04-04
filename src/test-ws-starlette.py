from starlette.applications import Starlette
from starlette.websockets import WebSocket
from uvicorn import Config, Server

app = Starlette()


@app.router.websocket_route("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Hello World!")
    await websocket.send_text("Bye!")


Server(Config(app)).run()
