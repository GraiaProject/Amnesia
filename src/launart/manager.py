import asyncio
from typing import Dict, Optional

from loguru import logger
from rich.console import Console
from rich.theme import Theme

from graia.amnesia.status.standalone import AbstractStandaloneStatus
from graia.amnesia.utilles import priority_strategy
from launart.component import Launchable, U_Stage, resolve_requirements
from launart.interface import ExportInterface
from launart.service import Service, TInterface


class ManagerStatus(AbstractStandaloneStatus):
    id = ".launart.manager"  # type: ignore
    stage: Optional[U_Stage] = None

    def __init__(self) -> None:
        ...

    @property
    def preparing(self) -> bool:
        return self.stage == "prepare"

    @property
    def blocking(self) -> bool:
        return self.stage == "blocking"

    @property
    def cleaning(self) -> bool:
        return self.stage == "cleanup"

    def unset(self) -> None:
        self.stage = None

    def set_prepare(self) -> None:
        if self.stage is not None:
            raise ValueError("this component cannot prepare twice.")
        self.update("prepare")

    def set_blocking(self) -> None:
        if self.stage != "prepare":
            raise ValueError("this component cannot be blocking before prepare nor after cleanup.")
        self.update("blocking")

    def set_cleanup(self) -> None:
        if self.stage != "blocking":
            raise ValueError("this component cannot cleanup before blocking.")
        self.update("cleanup")

    def frame(self):
        instance = ManagerStatus()
        instance.stage = self.stage
        return instance

    def update(self, stage: U_Stage) -> None:
        past = self.frame()
        self.stage = stage
        self.notify(past)

    async def wait_for_prepared(self):
        while self.stage == "prepare" or self.stage is None:
            await self.wait_for_update()

    async def wait_for_completed(self):
        while self.stage != "cleanup":
            await self.wait_for_update()

    async def wait_for_sigexit(self):
        while self.stage in {"prepare", "blocking"}:
            await self.wait_for_update()


class Launart:
    launchables: Dict[str, Launchable]
    status: ManagerStatus
    blocking_task: Optional[asyncio.Task] = None
    rich_console: Console

    def __init__(self, rich_console: Optional[Console] = None):
        self.launchables = {}
        self.status = ManagerStatus()
        self.rich_console = rich_console or Console(
            theme=Theme(
                {
                    "logging.level.success": "green",
                    "logging.level.trace": "bright_black",
                }
            )
        )

    # TODO: CRUD for Launchables

    async def launch(self):
        logger.info(f"launchable components count: {len(self.launchables)}")
        logger.info(f"launch all components...")

        if self.status.stage is not None:
            logger.error("detect existed ownership, launart may already running.")
            return

        _bind = {_id: _component for _id, _component in self.launchables.items()}
        tasks = {
            _id: asyncio.create_task(_component.launch(self), name=_id) for _id, _component in self.launchables.items()
        }

        def task_done_cb(t: asyncio.Task):
            exc = t.exception()
            if exc:
                logger.opt(exception=exc).error(
                    f"mainline {t.get_name()} failed.",
                    alt=f"[red bold]mainline [magenta]{t.get_name()}[/magenta] failed.",
                )
            else:
                component = _bind[t.get_name()]
                if self.status.preparing:
                    if "prepare" in component.stages:
                        if component.status.prepared:
                            logger.info(f"component {t.get_name()} prepared.")
                        else:
                            logger.error(
                                f"component {t.get_name()} defined preparing, but exited before status updating."
                            )
                elif self.status.blocking:
                    if "cleanup" in component.stages:
                        logger.warning(f"component {t.get_name()} exited before cleanup in blocking.")
                    else:
                        logger.info(f"component {t.get_name()} finished.")
                elif self.status.cleaning:
                    if "cleanup" in component.stages:
                        if component.status.finished:
                            logger.info(f"component {t.get_name()} finished.")
                        else:
                            logger.error(
                                f"component {t.get_name()} defined cleanup, but task completed before finished(may forget stat set?)."
                            )
                logger.success(
                    f"mainline {t.get_name()} completed.",
                    alt=f"mainline [magenta]{t.get_name()}[/magenta] completed.",
                )

        for task in tasks.values():
            task.add_done_callback(task_done_cb)

        self.status.set_prepare()
        upper = set()
        for layer, components in enumerate(resolve_requirements(set(self.launchables.values()))):
            await asyncio.wait([i.status.wait_for_prepared() for i in components if "prepare" in i.required])
            logger.info(f"layer#{layer} completed.", alt=f"layer#[magenta]{layer}[/] completed.")
            for component in components:
                component_req = upper.intersection(component.required)
                if component_req:
                    component.on_require_prepared(component_req)
            upper = {i.id for i in components}

        logger.info("all components prepared, blocking start.", style="green bold")

        self.status.set_blocking()
        loop = asyncio.get_running_loop()
        self.blocking_task = loop.create_task(
            asyncio.wait([i.status.wait_for_completed() for i in self.launchables.values()])
        )
        try:
            await asyncio.shield(self.blocking_task)
        except asyncio.CancelledError:
            logger.info("cancelled by user.", style="red bold")
            self.status.set_cleanup()
        finally:
            logger.info("application's sigexit detected, start cleanup", style="red bold")

            upper = set()
            for layer, components in enumerate(reversed(resolve_requirements(set(self.launchables.values())))):
                await asyncio.wait([i.status.wait_for_finished() for i in components if "cleanup" in i.required])
                logger.info(f"layer#{layer} completed.", alt=f"layer#[magenta]{layer}[/] completed.")
                for component in components:
                    component_req = upper.intersection(component.required)
                    if component_req:
                        component.on_require_exited(component_req)
                upper = {i.id for i in components}
            logger.success("cleanup stage finished, now waits for tasks' finale.", style="green bold")
            await asyncio.wait([i for i in tasks.values() if not i.done()])
            logger.warning("all done.", style="red bold")

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
        self.status.set_cleanup()
