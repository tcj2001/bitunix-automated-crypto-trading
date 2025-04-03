import websockets
import json
import time
import hashlib
import asyncio
import random
import string
from typing import Callable
import threading
from logger import Logger
logger = Logger(__name__).get_logger()
import gc

class BitunixPublicWebSocketClient:
    def __init__(self, api_key, secret_key, type):
        self.api_key = api_key
        self.secret_key = secret_key
        self.type = type
        self.url = "wss://fapi.bitunix.com/public/"
        self.websocket = None
        self.running=False
        self.loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=self.start_loop)
        self.loop_thread.daemon = True  # Ensure the thread closes with the program
        self.loop_thread.start()


    def start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def stop_loop(self):
        # Stop the loop in a thread-safe way
        self.loop.call_soon_threadsafe(self.loop.stop)

        # Wait for the thread to finish
        self.loop_thread.join()
        logger.info("Event loop stopped cleanly")
                            

    async def run_websocket(self, process_func: Callable):
        self.running = True
        while self.running:
            try:
                async with websockets.connect(self.url, ping_interval=None, open_timeout=30) as self.websocket:
                    connect_response = await self.websocket.recv()
                    logger.info(f"{self.url} {self.type} websocket connect Response: {connect_response}")

                    self.heartbeat_task =  asyncio.create_task(self.send_heartbeat(self.websocket))

                    for ticker in self.tickerList:
                        subscribe_message = self.create_subscription_message(ticker)
                        if subscribe_message:
                            await self.websocket.send(subscribe_message)     
                                               
                    self.recv_task = asyncio.create_task(self.receive_messages(process_func))
                    await self.recv_task                    
            except websockets.exceptions.ConnectionClosedError as e:
                logger.warning(f"{self.url} {self.type}  WebSocket connection closed. Retrying in 5 seconds: {e}")
                await asyncio.sleep(5)  # Delay before retrying
            except Exception as e:
                logger.error(f"{self.url} {self.type} Unexpected error during WebSocket operation: {e}")
                await asyncio.sleep(5)  # Delay before retrying
    
    def create_subscription_message(self, ticker):
        if self.type == 'depth':
            dep = {"symbol": ticker, "ch": "depth_book1"}
            return json.dumps({"op": "subscribe", "args": [dep]})
        elif self.type == 'kline':
            kli = {"symbol": ticker, "ch": "market_kline_1min"}
            return json.dumps({"op": "subscribe", "args": [kli]})
        elif self.type == 'ticker':
            tic = {"symbol": ticker, "ch": "ticker"}
            return json.dumps({"op": "subscribe", "args": [tic]})
        return None
    
    async def receive_messages(self, process_func: Callable):
        try:
            while self.running:
                message = await self.websocket.recv()
                await process_func(message)
            logger.warning(f"{self.url} {self.type}  WebSocket connection closed")
        except asyncio.CancelledError:
            logger.info(f"{self.url} {self.type}  WebSocket receive task cancelled")
            self.running = False                        
        except websockets.exceptions.ConnectionClosedError as e:
            logger.info(f"{self.url} {self.type}  Websocket: Connection closed: {e}")
        except Exception as e:
            logger.info(f"{self.url} {self.type}  Websocket: Unexpected error: {e}")
            pass
        del message, process_func
        gc.collect()

    async def send_heartbeat(self, websocket):
        try:
            while True:
                await websocket.send(json.dumps({"op": "ping", "ping": int(time.time())}))
                await asyncio.sleep(30)
        except asyncio.CancelledError:
            logger.info(f"{self.url} {self.type}  WebSocket hearbeat task cancelled")
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"{self.url} {self.type}  WebSocket connection for heartbeat is closed")
        except Exception as e:
            logger.info(f"{self.url} {self.type}  Websocket for heartbeat: Unexpected error: {e}")
            pass       
  
    async def stop_websocket(self):
        try:
            self.running = False
            # Cancel the receive task
            if hasattr(self, "recv_task") and self.recv_task:
                self.loop.call_soon_threadsafe(self.recv_task.cancel)  # Schedule cancellation

            # Cancel the heartbeat task
            if hasattr(self, "heartbeat_task") and self.heartbeat_task:
                self.loop.call_soon_threadsafe(self.heartbeat_task.cancel)  # Schedule cancellation
            
            # Close the WebSocket
            if self.websocket is not None:
               self.loop.call_soon_threadsafe(self.websocket.close)  # 
 
        except Exception as e:
            logger.error(f"{self.url} {self.type} Unexpected error during WebSocket shutdown: {e}")
        finally:
            # Stop the event loop
            self.loop.call_soon_threadsafe(self.loop.stop)
            logger.info(f"{self.url} {self.type} WebSocket thread stopped and resources cleaned up.")

class BitunixPrivateWebSocketClient:
    def __init__(self, api_key, secret_key):
        self.api_key = api_key
        self.secret_key = secret_key
        self.url = "wss://fapi.bitunix.com/private/"
        self.websocket = None
        self.running=False
        self.loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=self.start_loop)
        self.loop_thread.daemon = True  # Ensure the thread closes with the program
        self.loop_thread.start()


    def start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def stop_loop(self):
        # Stop the loop in a thread-safe way
        self.loop.call_soon_threadsafe(self.loop.stop)

        # Wait for the thread to finish
        self.loop_thread.join()
        logger.info("Event loop stopped cleanly")

    async def run_websocket(self, process_func: Callable):
        self.running = True
        while self.running:
            try:
                async with websockets.connect(self.url, ping_interval=None, open_timeout=30) as self.websocket:
                    connect_response = await self.websocket.recv()
                    logger.info(f"{self.url} websocket connect Response: {connect_response}")

                    self.heartbeat_task = asyncio.create_task(self.send_heartbeat(self.websocket))

                    nonce = await self.generate_nonce(32)
                    sign, timestamp = await self.generate_signature(self.api_key, self.secret_key, nonce)
                    login_request = {
                        "op": "login",
                        "args": [
                            {
                                "apiKey": self.api_key,
                                "timestamp": timestamp,
                                "nonce": nonce,
                                "sign": sign,
                            }
                        ],
                    }
                    await self.websocket.send(json.dumps(login_request))
                    login_response = await self.websocket.recv()
                    logger.info(f"{self.url} Login Response: {login_response}")

                    self.recv_task = asyncio.create_task(self.receive_messages(process_func))
                    await self.recv_task                    

            except websockets.exceptions.ConnectionClosedError as e:
                logger.warning(f"{self.type} WebSocket connection closed. Retrying in 5 seconds: {e}")
                await asyncio.sleep(5)  # Delay before retrying
            except Exception as e:
                logger.error(f"Unexpected error during {self.type} WebSocket operation: {e}")
                await asyncio.sleep(5)  # Delay before retrying

    async def receive_messages(self, process_func: Callable):
        try:
            while self.running:
                message = await self.websocket.recv()
                await process_func(message)
            logger.warning(f"{self.type} WebSocket connection closed")
        except asyncio.CancelledError:
            logger.info(f"{self.url} WebSocket receive task cancelled")
            self.running = False                        
        except websockets.exceptions.ConnectionClosedError as e:
            logger.info(f"{self.url} Websocket: Connection closed: {e}")
        except Exception as e:
            logger.info(f"{self.url} Websocket: Unexpected error: {e}")
            pass
        del message, process_func
        gc.collect()

    async def send_heartbeat(self, websocket):
        try:
            while True:
                await websocket.send(json.dumps({"op": "ping", "ping": int(time.time())}))
                await asyncio.sleep(30)
        except asyncio.CancelledError:
            logger.info(f"{self.url} WebSocket hearbeat task cancelled")
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"{self.url} WebSocket connection for heartbeat is closed")
        except Exception as e:
            logger.info(f"{self.url} Websocket for heartbeat: Unexpected error: {e}")
            pass            

    async def stop_websocket(self):
        try:
            self.running = False
            # Cancel the receive task
            if hasattr(self, "recv_task") and self.recv_task:
                self.loop.call_soon_threadsafe(self.recv_task.cancel)  # Schedule cancellation

            # Cancel the heartbeat task
            if hasattr(self, "heartbeat_task") and self.heartbeat_task:
                self.loop.call_soon_threadsafe(self.heartbeat_task.cancel)  # Schedule cancellation
            
            # Close the WebSocket
            if self.websocket is not None:
               self.loop.call_soon_threadsafe(self.websocket.close)  # 
 
        except Exception as e:
            logger.error(f"Unexpected error during {self.url} WebSocket shutdown: {e}")
        finally:
            # Stop the event loop
            self.loop.call_soon_threadsafe(self.loop.stop)
            logger.info(f"{self.url} WebSocket thread stopped and resources cleaned up.")
       

    async def generate_signature(self, api_key, secret_key, nonce):
        timestamp = int(time.time())
        pre_sign = f"{nonce}{timestamp}{api_key}"
        sign = hashlib.sha256(pre_sign.encode()).hexdigest()
        final_sign = hashlib.sha256((sign + secret_key).encode()).hexdigest()
        return final_sign, timestamp

    async def generate_nonce(self, length=32):
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

        
