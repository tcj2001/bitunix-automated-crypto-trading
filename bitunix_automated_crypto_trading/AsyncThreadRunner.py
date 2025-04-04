import asyncio
import threading
from logger import Logger
import os
logger = Logger(__name__).get_logger()

class AsyncThreadRunner:
    def __init__(self, async_func, interval, *args, **kwargs):
        self.async_func = async_func
        self.interval = interval
        self.args = args
        self.kwargs = kwargs
        self.loop = asyncio.new_event_loop()
        self._stop_event = threading.Event()
        self.thread = threading.Thread(target=self.thread_function)
        self.task = None

    def thread_function(self):
        asyncio.set_event_loop(self.loop)
        try:
            if self.interval == 0:
                self.task = asyncio.run_coroutine_threadsafe(
                                self.async_func(*self.args, **self.kwargs), self.loop
                            )                
            else:
                self.task = asyncio.run_coroutine_threadsafe(
                                self.periodic_run(), self.loop
                            )
            self.loop.run_forever()
        except Exception as e:
            logger.info(f"Async Thread function error: {e}")
        finally:
            pending = asyncio.all_tasks(self.loop)
            for task in pending:
                task.cancel()
                try:
                    self.loop.run_until_complete(task)
                except asyncio.CancelledError:
                    pass
            self.loop.run_until_complete(self.loop.shutdown_asyncgens())
            self.loop.close()

    async def periodic_run(self):
        try:
            while not self._stop_event.is_set():
                try:
                    await self.async_func(*self.args, **self.kwargs)
                except Exception as e:
                    logger.info(f"error in periodic_run async thread {self.thread.name} {e}")
                    os._exit(1)  # Exit the program if the thread is stopped
                await asyncio.sleep(self.interval)
            logger.info(f"periodic {self.thread.name} Thread stopped, exiting app.")
            os._exit(1)  # Exit the program if the thread is stopped
        except asyncio.CancelledError:
            pass

    def start_thread(self, thread_name=None):
        self.thread.name = thread_name
        self.thread.start()

    async def stop_thread(self):
        """Gracefully stop the async thread."""
        # Signal any periodic task to stop
        self._stop_event.set()

        # Cancel and await the running task
        if self.task:
            self.task.cancel()
            try:
                await asyncio.wrap_future(self.task)  # Wait for the cancellation to propagate
            except asyncio.CancelledError:
                logger.info(f"{self.thread.name} Task cancelled successfully.")
            except Exception as e:
                logger.error(f"Unexpected error while cancelling the task {self.thread.name}: {e}")

        # Stop the event loop safely
        self.loop.call_soon_threadsafe(self.loop.stop)

        # Wait for the thread to join
        self.thread.join()
        logger.info(f"{self.thread.name} Thread stopped and event loop cleaned up.")
