from creart import it
from launart import Launart

from graia.amnesia.builtins.asgi import HypercornASGIService

manager = it(Launart)
manager.add_component(HypercornASGIService("127.0.0.1", 5333, patch_logger=True))
manager.launch_blocking()
