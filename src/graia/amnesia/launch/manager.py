import asyncio
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set, Type

from loguru import logger
from rich.console import Console
from rich.status import Status as RichStatus
from rich.theme import Theme

from graia.amnesia.launch.component import LaunchComponent, resolve_requirements
from graia.amnesia.launch.interface import ExportInterface
from graia.amnesia.launch.service import Service, TInterface
from graia.amnesia.utilles import priority_strategy


class LaunchManager:
    launch_components: Dict[str, LaunchComponent]
    services: List[Service]
    _service_interfaces: Dict[Type[ExportInterface], Service]

    sigexit: asyncio.Event
    maintask: Optional[asyncio.Task] = None
    rich_console: Console

    def __init__(self, rich_console: Optional[Console] = None):
        self.launch_components = {}
        self.services = []
        self._service_interfaces = {}
        self.sigexit = asyncio.Event()
        self.rich_console = rich_console or Console(
            theme=Theme(
                {
                    "logging.level.success": "green",
                    "logging.level.trace": "bright_black",
                }
            )
        )

    def update_launch_components(self, components: List[LaunchComponent]):
        self.launch_components.update({i.id: i for i in components})

    def update_services(self, services: List[Service]):
        self.services.extend(services)
        self._mapping_service_interfaces()

    def _mapping_service_interfaces(self):
        self._service_interfaces = priority_strategy(self.services, lambda s: s.supported_interface_types)

    def has_service(self, service_type: Type[Service]) -> bool:
        return any(isinstance(service, service_type) for service in self.services)

    def get_service(self, service_type: Type[Service]) -> Service:
        for service in self.services:
            if isinstance(service, service_type):
                return service
        raise ValueError(f"service not found: {service_type}")

    def new_launch_component(
        self,
        id: str,
        requirements: Optional[Set[str]] = None,
        mainline: Optional[Callable[["LaunchManager"], Coroutine[None, None, Any]]] = None,
        prepare: Optional[Callable[["LaunchManager"], Coroutine[None, None, Any]]] = None,
        cleanup: Optional[Callable[["LaunchManager"], Coroutine[None, None, Any]]] = None,
    ) -> LaunchComponent:
        component = LaunchComponent(id, requirements or set(), mainline, prepare, cleanup)
        self.launch_components[id] = component
        return component

    def remove_launch_component(self, id: str):
        if id not in self.launch_components:
            raise KeyError("id doesn't exist.")
        del self.launch_components[id]

    def add_service(self, service: Service):
        if service in self.services:
            raise ValueError("existed service")
        self.services.append(service)
        self._mapping_service_interfaces()
        launch_component = service.launch_component
        self.launch_components[launch_component.id] = launch_component

    def remove_service(self, service: Service):
        if service not in self.services:
            raise ValueError("service doesn't exist.")
        self.services.remove(service)
        del self.launch_components[service.launch_component.id]

    def get_interface(self, interface_type: Type[TInterface]) -> TInterface:
        if interface_type not in self._service_interfaces:
            raise ValueError(f"interface type {interface_type} not supported.")
        return self._service_interfaces[interface_type].get_interface(interface_type)

    async def launch(self):
        self.sigexit = asyncio.Event()
        for service in self.services:
            logger.info(f"using service: {service.__class__.__name__}")

        logger.info(f"launch components count: {len(self.launch_components)}")

        with RichStatus("[dark_orange]preparing components...", console=self.rich_console) as status:
            for component_layer in resolve_requirements(set(self.launch_components.values())):
                tasks = [
                    asyncio.create_task(component.prepare(self), name=component.id)
                    for component in component_layer
                    if component.prepare
                ]
                for task in tasks:
                    task.add_done_callback(
                        lambda t: status.update(f"[magenta]{t.get_name()}[/magenta] [dark_orange]prepared.")
                    )
                if tasks:
                    await asyncio.wait(tasks)
            status.update("[dark_orange bold]all launch components prepared.")
            await asyncio.sleep(1)

        logger.info("components prepared, switch to mainlines and block main thread.", style="green bold")

        loop = asyncio.get_running_loop()
        tasks = [
            loop.create_task(component.mainline(self), name=component.id)
            for component in self.launch_components.values()
            if component.mainline
        ]
        for task in tasks:

            def cb(t: asyncio.Task):
                exc = t.exception()
                if exc:
                    logger.opt(exception=exc).error(
                        f"mainline {t.get_name()} failed.",
                        alt=f"[red bold]mainline [magenta]{t.get_name()}[/magenta] failed.",
                    )
                else:
                    logger.success(
                        f"mainline {t.get_name()} completed.",
                        alt=f"mainline [magenta]{t.get_name()}[/magenta] completed.",
                    )

            task.add_done_callback(cb)

        logger.info(f"mainline count: {len(tasks)}")
        try:
            if tasks:
                self.maintask = loop.create_task(asyncio.wait(tasks))
                await asyncio.shield(self.maintask)
        except asyncio.CancelledError:
            logger.info("cancelled by user.", style="red bold")
            if not self.sigexit.is_set():
                self.sigexit.set()
        finally:
            logger.info("all mainlines exited, cleanup start.", style="red bold")
            for component_layer in reversed(resolve_requirements(set(self.launch_components.values()))):
                tasks = [
                    asyncio.create_task(component.cleanup(self), name=component.id)
                    for component in component_layer
                    if component.cleanup
                ]
                if tasks:
                    for task in tasks:
                        task.add_done_callback(
                            lambda t: logger.success(
                                f"{t.get_name()} cleanup finished.",
                                alt=f"[magenta]{t.get_name()}[/magenta] cleanup finished.",
                            )
                        )
                    await asyncio.gather(*tasks)
            logger.success("cleanup finished.", style="green bold")
            logger.warning("exiting...", style="red bold")

    def launch_blocking(self, *, loop: Optional[asyncio.AbstractEventLoop] = None):
        import functools
        import signal
        import threading

        loop = loop or asyncio.new_event_loop()
        launch_task = loop.create_task(self.launch(), name="amnesia-launch")
        if (
            threading.current_thread() is threading.main_thread()
            and signal.getsignal(signal.SIGINT) is signal.default_int_handler
        ):
            sigint_handler = functools.partial(self._on_sigint, main_task=launch_task)
            try:
                signal.signal(signal.SIGINT, sigint_handler)
            except ValueError:
                # `signal.signal` may throw if `threading.main_thread` does
                # not support signals
                signal_handler = None
        else:
            sigint_handler = None
        loop.run_until_complete(launch_task)

        if sigint_handler is not None and signal.getsignal(signal.SIGINT) is sigint_handler:
            signal.signal(signal.SIGINT, signal.default_int_handler)

    def _on_sigint(self, _, __, main_task: asyncio.Task):
        if not main_task.done():
            main_task.cancel()
            # wakeup loop if it is blocked by select() with long timeout
            main_task._loop.call_soon_threadsafe(lambda: None)
            logger.info("Ctrl-C triggered by user.", style="dark_orange bold")
        self.sigexit.set()
