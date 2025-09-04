try:
    from .uvicorn import UvicornASGIService as _UvicornASGIService
except ImportError:
    _UvicornASGIService = None

try:
    from .hypercorn import HypercornASGIService as _HypercornASGIService
except ImportError:
    _HypercornASGIService = None


def __getattr__(name):
    if name == "UvicornASGIService":
        if _UvicornASGIService is None:
            raise ImportError("Please install `uvicorn` first. Install with `pip install graia-amnesia[uvicorn]`")
        return _UvicornASGIService
    if name == "HypercornASGIService":
        if _HypercornASGIService is None:
            raise ImportError("Please install `hypercorn` first. Install with `pip install graia-amnesia[hypercorn]`")
        return _HypercornASGIService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
