import asyncio
import threading
import time
import logging # Using standard logging for demonstration

class AsyncThreadRunner:
    def __init__(self, async_func, logger, interval, *args, **kwargs):
        self.async_func = async_func
        self.interval = interval
        self.args = args
        self.kwargs = kwargs
        self.loop = asyncio.new_event_loop()
        self._stop_event = threading.Event()
        self.thread = threading.Thread(target=self.thread_function)
        self.task = None
        self.logger = logger
        self.exception_occurred = False # New flag to indicate if an unhandled exception occurred

    def thread_function(self):
        """This function runs in the separate thread."""
        asyncio.set_event_loop(self.loop)
        self.exception_occurred = False # Reset on thread start

        try:
            if self.interval == 0:
                # For one-off tasks, run it and then stop the loop
                self.task = asyncio.run_coroutine_threadsafe(
                    self.run_once(), self.loop
                )
            else:
                # For periodic tasks, schedule the periodic_run
                self.task = asyncio.run_coroutine_threadsafe(
                    self.periodic_run(), self.loop
                )
            
            # This will run until loop.stop() is called
            self.logger.info(f"Thread '{self.thread.name}' event loop started.")
            self.loop.run_forever()
        except Exception as e:
            # This catches exceptions that bubble up from run_forever,
            # which usually means a serious issue or the loop being stopped unexpectedly.
            self.logger.error(f"Async Thread '{self.thread.name}' main function error: {type(e).__name__} - {e}", exc_info=True)
            self.exception_occurred = True # Mark as failed
        finally:
            self.logger.info(f"Thread '{self.thread.name}' event loop stopping.")
            # Clean up pending tasks
            pending = asyncio.all_tasks(self.loop)
            for task in pending:
                task.cancel()
                try:
                    self.loop.run_until_complete(task)
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    self.logger.error(f"Error during task cancellation in thread '{self.thread.name}': {e}")
            
            # Shutdown async generators and close the loop
            self.loop.run_until_complete(self.loop.shutdown_asyncgens())
            self.loop.close()
            self.logger.info(f"Thread '{self.thread.name}' event loop closed.")

    async def run_once(self):
        """Helper for one-off tasks."""
        try:
            await self.async_func(*self.args, **self.kwargs)
            self.logger.info(f"Thread '{self.thread.name}' one-off task completed.")
        except Exception as e:
            self.logger.error(f"Error in one-off task for thread '{self.thread.name}': {type(e).__name__} - {e}", exc_info=True)
            self.exception_occurred = True # Mark as failed if the one-off task itself fails
        finally:
            # Stop the event loop after a one-off task completes or fails
            self.loop.call_soon_threadsafe(self.loop.stop)


    async def periodic_run(self):
        """Runs the async function periodically."""
        try:
            while not self._stop_event.is_set():
                try:
                    await self.async_func(*self.args, **self.kwargs)
                except Exception as e:
                    # Log the error but continue the loop for periodic tasks,
                    # assuming the next run might succeed.
                    self.logger.error(f"Error in periodic_run for thread '{self.thread.name}': {type(e).__name__} - {e}", exc_info=True)
                    # If you want a critical failure here to stop the thread entirely for restart,
                    # you would set self.exception_occurred = True and then break the loop.
                    # For now, we'll just log and continue, allowing the manager to detect if the thread dies from other reasons.
                
                # Check stop event again before sleeping to allow immediate stopping
                if self._stop_event.is_set():
                    break
                
                # Use asyncio.sleep to allow graceful cancellation
                try:
                    await asyncio.sleep(self.interval)
                except asyncio.CancelledError:
                    self.logger.info(f"Periodic sleep for '{self.thread.name}' cancelled.")
                    break # Exit loop if sleep is cancelled
            
            self.logger.info(f"Periodic run for '{self.thread.name}' loop stopped.")
        except asyncio.CancelledError:
            self.logger.info(f"Periodic run for '{self.thread.name}' task cancelled.")
        except Exception as e:
            self.logger.error(f"Unexpected error in periodic_run for thread '{self.thread.name}': {type(e).__name__} - {e}", exc_info=True)
            self.exception_occurred = True # Mark as failed if periodic_run itself has an unhandled error

    def start_thread(self, thread_name=None):
        """Starts the underlying threading.Thread."""
        self.thread.name = thread_name if thread_name else f"AsyncRunner-{id(self)}"
        self.logger.info(f"Starting background thread '{self.thread.name}'.")
        self.thread.start()

    def stop_thread(self):
        """Gracefully signals the async thread to stop."""
        self.logger.info(f"Signaling thread '{self.thread.name}' to stop.")
        self._stop_event.set() # Signal the periodic task to stop

        # If it's a one-off task, the loop will stop itself.
        # If it's a periodic task, we need to cancel its main task to unblock run_forever.
        if self.task and not self.task.done():
            self.loop.call_soon_threadsafe(self.task.cancel)
        
        # Stop the event loop if it's running
        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)

        # Wait for the thread to actually finish its execution
        self.thread.join(timeout=10) # Give it some time to clean up
        if self.thread.is_alive():
            self.logger.warning(f"Thread '{self.thread.name}' did not terminate gracefully after join timeout.")
        else:
            self.logger.info(f"Thread '{self.thread.name}' successfully stopped.")
