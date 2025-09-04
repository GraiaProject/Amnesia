from graia.amnesia.builtins.asgi import HypercornASGIService
from creart import it
from launart import Launart

manager = it(Launart)
manager.add_component(serv := HypercornASGIService("127.0.0.1", 5333))
serv.patch_logger()
manager.launch_blocking()
