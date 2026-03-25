from creart import it
from launart import Launart

from graia.amnesia.builtins.asgi import UvicornASGIService
from graia.amnesia.builtins.asgi.uvicorn import UvicornOptions


async def app(scope, receive, send):
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
                return
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return

    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [[b"content-type", b"text/plain"]],
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": b"Hello, world!",
        }
    )


manager = it(Launart)
manager.add_component(UvicornASGIService("127.0.0.1", 5333, {"/": app}, options=UvicornOptions(access_log=True), patch_logger=True))
manager.launch_blocking()
