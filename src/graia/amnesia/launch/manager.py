import asyncio
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set, Type

from loguru import logger
from rich.console import Console
from rich.logging import RichHandler
from rich.status import Status as RichStatus

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
        self.rich_console = rich_console or Console()

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
        logger.configure(
            handlers=[
                {
                    "sink": RichHandler(console=self.rich_console, markup=True),
                    "format": "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | "
                    "<cyan>{name}</cyan>: <cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
                }
            ]
        )

        for service in self.services:
            logger.info(f"using service: {service.__class__.__name__}")

        logger.info(f"launch components count: {len(self.launch_components)}")

        with RichStatus("[orange bold]preparing components...", console=self.rich_console) as status:
            for component_layer in resolve_requirements(set(self.launch_components.values())):
                tasks = [
                    asyncio.create_task(component.prepare(self), name=component.id)  # type: ignore
                    for component in component_layer
                    if component.prepare
                ]
                for task in tasks:
                    task.add_done_callback(lambda t: status.update(f"{t.get_name()} prepared."))
                if tasks:
                    await asyncio.wait(tasks)
            status.update("all launch components prepared.")
            await asyncio.sleep(1)

        logger.info("[green bold]components prepared, switch to mainlines and block main thread.")

        loop = asyncio.get_running_loop()
        tasks = [
            loop.create_task(component.mainline(self), name=component.id)  # type: ignore
            for component in self.launch_components.values()
            if component.mainline
        ]
        for task in tasks:
            task.add_done_callback(lambda t: logger.success(f"mainline {t.get_name()} completed."))

        logger.info(f"mainline count: {len(tasks)}")
        try:
            if tasks:
                self.maintask = loop.create_task(asyncio.wait(tasks))
                await asyncio.shield(self.maintask)
        except asyncio.CancelledError:
            logger.info("[red bold]cancelled by user.")
            if not self.sigexit.is_set():
                self.sigexit.set()
        finally:
            logger.info("[red bold]all mainlines exited, cleanup start.")
            for component_layer in reversed(resolve_requirements(set(self.launch_components.values()))):
                tasks = [
                    asyncio.create_task(component.cleanup(self), name=component.id)  # type: ignore
                    for component in component_layer
                    if component.cleanup
                ]
                if tasks:
                    for task in tasks:
                        task.add_done_callback(lambda t: logger.success(f"{t.get_name()} cleanup finished."))
                    await asyncio.gather(*tasks)
            logger.info("[green bold]cleanup finished.")
            logger.warning("[red bold]exiting...")

    def launch_blocking(self, *, loop: Optional[asyncio.AbstractEventLoop] = None):
        loop = loop or asyncio.new_event_loop()
        self.sigexit = asyncio.Event(loop=loop)
        launch_task = loop.create_task(self.launch(), name="amnesia-launch")
        try:
            loop.run_until_complete(launch_task)
        except KeyboardInterrupt:
            self.sigexit.set()
            launch_task.cancel()
            loop.run_until_complete(launch_task)
