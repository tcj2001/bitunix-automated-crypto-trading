#usage
#start threads
#self.threadManager.start_thread("GetportfolioData", 1, self.GetportfolioData) 
#self.threadManager.start_thread("GetPendingPositionData", 0, self.GetPendingPositionData) 
#self.threadManager.start_thread("GetOrderData", 1, self.GetPendingOrderData) 
#self.threadManager.start_thread("GetTradeHistoryData", 1, self.GetTradeHistoryData) 
#self.threadManager.start_thread("BuySellList", 60, self.BuySellList) 
#self.threadManager.start_thread("AutoTradeProcess", 60, self.AutoTradeProcess) 

import time
import threading
from logger import Logger
logger = Logger(__name__).get_logger()

def job_func(*args, **kwargs):
    print(f"Job running with arguments: {args}, {kwargs}")        
        
def run_threaded(job_func, args):
    job_thread = threading.Thread(target=job_func, args=args)
    job_thread.start()

class ManagedThread(threading.Thread):
    def __init__(self, interval, target, *args, **kwargs):
        super().__init__()
        self.target = target
        self.interval = interval
        self.args = args
        self.kwargs = kwargs
        self._stop_event = threading.Event()

    def run(self):
        while not self._stop_event.is_set():
            stime=time.time()
            try:
                self.target(self, *self.args, **self.kwargs)
            except Exception as e:
                logger.info(f"error in thread {self.name}, {e}, {e.args}, {type(e).__name__}")  
            elapsed_time = time.time() - stime
            if self.interval==0:
                break
            time_to_wait = max(0.05, self.interval - elapsed_time)
            time.sleep(time_to_wait)

    def stop(self):
        self._stop_event.set()
        
    def should_stop(self): 
        return self._stop_event.is_set()        

class ThreadManager:
    def __init__(self):
        self.threads = []

    def start_thread(self, name, interval, thread, *args, **kwargs):
        thread = ManagedThread(interval, thread, *args, **kwargs)
        thread.name = name
        thread.start()
        self.threads.append(thread)
        thread.join(interval)
        return thread

    def stop_all_threads(self):
        for thread in self.threads:
            thread.stop()
        for thread in self.threads:
            thread.join()
        self.threads = []

threadManager = ThreadManager()