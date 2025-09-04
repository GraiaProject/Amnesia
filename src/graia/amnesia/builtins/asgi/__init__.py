try:
    from .uvicorn import UvicornASGIService as UvicornASGIService
except ImportError:
    UvicornASGIService = None

try:
    from .hypercorn import HypercornASGIService as HypercornASGIService
except ImportError:
    HypercornASGIService = None


def __getattr__(name):
    if name == "UvicornASGIService":
        if UvicornASGIService is None:
            raise ImportError("Please install `uvicorn` first. Install with `pip install graia-amnesia[uvi]`")
        return UvicornASGIService
    if name == "HypercornASGIService":
        if HypercornASGIService is None:
            raise ImportError("Please install `hypercorn` first. Install with `pip install graia-amnesia[hyper]`")
        return HypercornASGIService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["UvicornASGIService", "HypercornASGIService"]
