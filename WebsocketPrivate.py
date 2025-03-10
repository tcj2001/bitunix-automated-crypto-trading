import asyncio
import websockets
import hashlib
import time
import json
import random
import string
import os
from dotenv import load_dotenv

import logging
logger = logging.getLogger(__name__)

load_dotenv()

def generate_signature(api_key, secret_key, nonce):
    timestamp = int(time.time())
    pre_sign = f"{nonce}{timestamp}{api_key}"
    sign = hashlib.sha256(pre_sign.encode()).hexdigest()
    final_sign = hashlib.sha256((sign + secret_key).encode()).hexdigest()
    return final_sign, timestamp


def generate_nonce(length=32):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


async def send_heartbeat(websocket):
    while True:
        await websocket.send(json.dumps({"op": "ping", "ping": int(time.time())}))
        await asyncio.sleep(30)


async def monitor_balance(api_key, secret_key):
    ws_url = "wss://fapi.bitunix.com/private/"
    nonce = generate_nonce()
    sign, timestamp = generate_signature(api_key, secret_key, nonce)

    async with websockets.connect(ws_url, ping_interval=None) as websocket:
        login_response = await websocket.recv()
        #logger.info("Login Response:", login_response)

        login_request = {
            "op": "login",
            "args": [
                {
                    "apiKey": api_key,
                    "timestamp": timestamp,
                    "nonce": nonce,
                    "sign": sign,
                }
            ],
        }
        await websocket.send(json.dumps(login_request))
        login_response = await websocket.recv()
        #logger.info("Login Response:", login_response)

        asyncio.create_task(send_heartbeat(websocket))

        listen_loop = True
        try:
            while listen_loop:
                message = await websocket.recv()
                logger.info("Balance Update:", message)
        except websockets.exceptions.ConnectionClosedError as e:
            logger.info(f"Connection closed: {e}")
        except Exception as e:
            logger.info(f"Unexpected error: {e}")


# Replace with your API Key and Secret Key
API_KEY=os.getenv('api_key')
SECRET_KEY=os.getenv('secret_key')
# Start the WebSocket connection and monitor balance
asyncio.run(monitor_balance(API_KEY, SECRET_KEY))