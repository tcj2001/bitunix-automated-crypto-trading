import asyncio 
import os
import uvicorn
import numpy as np
import pandas as pd
import json
import time
from datetime import datetime
import pytz
from ThreadManager import ThreadManager
from BitunixApi import BitunixApi
from BitunixSignal import BitunixSignal
from NotificationManager import NotificationManager

from logger import Logger
logger = Logger(__name__).get_logger()

from fastapi import FastAPI, Request, Form, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import HTMLResponse , JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from fastapi.security import OAuth2PasswordRequestForm
from fastapi_login import LoginManager
from fastapi_login.exceptions import InvalidCredentialsException
from DataFrameHtmlRenderer import DataFrameHtmlRenderer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from dotenv import load_dotenv, dotenv_values, set_key
from config import Settings
from pydantic import ValidationError

ENV_FILE = ".env"
CONFIG_FILE = "config.txt"
LOG_FILE = "app.log"

#load environment variables
load_dotenv(ENV_FILE)
API_KEY = os.getenv('API_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')
SECRET = os.getenv('SECRET')
PASSWORD = os.getenv('PASSWORD')
HOST = os.getenv('HOST')

#load config variables using setting class in config.py validating using pydantic
settings = Settings()

class bitunix():
    def __init__(self, password, api_key, secret_key, settings):
        self.screen_refresh_interval =settings.SCREEN_REFRESH_INTERVAL
        
        self.autoTrade=settings.AUTOTRADE
        
        self.threadManager = ThreadManager()
        self.notifications = NotificationManager()
        self.bitunixApi = BitunixApi(api_key, secret_key, settings)
        self.bitunixSignal = BitunixSignal(api_key, secret_key, settings, self.threadManager, self.notifications, self.bitunixApi)
        
        self.websocket_connections = set()
        self.DB = {"admin": {"password": password}}
        
    async def update_settings(self, settings):
        self.settings = settings
        await self.bitunixSignal.update_settings(settings)
        await self.bitunixApi.update_settings(settings)

    async def start(self): 
        await asyncio.create_task(self.bitunixSignal.load_tickers())
        await asyncio.create_task(self.bitunixSignal.start_jobs())
        
    async def restart(self): 
       await asyncio.create_task(self.bitunixSignal.restart_jobs())
        
    async def send_message_to_websocket(self,message):
        async def send_to_all():
            for ws in self.bitunixSignal.websocket_connections:
                await ws.send_text(message)
        asyncio.run(send_to_all())

    async def send_async_message_to_websocket(self,message):
            for ws in self.bitunixSignal.websocket_connections:
                await ws.send_text(message)
     
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
templates = Jinja2Templates(directory="templates")
SECRET=os.getenv('SECRET')
login_manager = LoginManager(SECRET, token_url="/auth/login", use_cookie=True)
login_manager.cookie_name = "auth_token"


@app.post("/auth/login")
async def login(data: OAuth2PasswordRequestForm = Depends()):
    start=time.time()
    username = data.username
    password = data.password
    
    user = load_user(username, some_callable_object)
    if not user or password != user["password"]:
        raise InvalidCredentialsException
    access_token = login_manager.create_access_token(data={"sub": username})
    response = RedirectResponse(url="/main", status_code=302)
    login_manager.set_cookie(response, access_token)
    logger.info(f"/auth/login: elapsed time {time.time()-start}")
    return response

@app.get("/main", response_class=HTMLResponse)
async def main_page(request: Request,  user=Depends(login_manager)):
    return templates.TemplateResponse({"request": request, "user": user}, "main.html")

  
@app.on_event("startup")  
async def startup_event():
    await asyncio.create_task(get_server_states(app, settings))
    await bitunix.start()

#load inital states for html
async def get_server_states(app, settings):
    app.state.element_states = {}
    app.state.element_states['autoTrade']=settings.AUTOTRADE
    app.state.element_states['optionMovingAverage']=settings.OPTION_MOVING_AVERAGE
    app.state.element_states['maxAutoTrades']=settings.MAX_AUTO_TRADES

@app.post("/reload")
async def refresh_detected():
    bitunix.bitunixSignal.notifications.add_notification("Reload detected!")
    await asyncio.create_task(bitunix.restart())

@app.post("/save_states")
async def save_states(states: dict):
    app.state.element_states.update(states)
    return {"message": "States saved"}

@app.post("/get_states")
async def get_states(payload: dict):
    element_ids = payload.get("element_ids", [])
    states = {element_id: app.state.element_states.get(element_id, "No state found") for element_id in element_ids}
    return {"states": states}

async def set_server_states():
    settings.AUTOTRADE = True if app.state.element_states['autoTrade']=='true' else False

    if settings.AUTOTRADE:
        settings.OPTION_MOVING_AVERAGE = app.state.element_states['optionMovingAverage']
        settings.notifications.add_notification(f"optionMovingAverage: {settings.OPTION_MOVING_AVERAGE}")  

        settings.PROFIT_AMOUNT = app.state.element_states['profitAmount']
        settings.notifications.add_notification(f"profitAmount: {settings.PROFIT_AMOUNT}")  

        settings.LOSS_AMOUNT = app.state.element_states['lossAmount']
        settings.notifications.add_notification(f"lossAmount: {settings.LOSS_AMOUNT}")  

        settings.MAX_AUTO_TRADES = app.state.element_states['maxAutoTrades']
        settings.notifications.add_notification(f"maxAutoTrades: {settings.MAX_AUTO_TRADES}")

    settings.notifications.add_notification(" AutoTrade activated" if settings.AUTOTRADE else "AutoTrade de-activated")  

def some_callable_object():
    logger.info("called")

@app.post("/autotrade")
async def handle_autotrade():
    await asyncio.create_task(set_server_states())
    return {"status":settings.AUTOTRADE}


@login_manager.user_loader(some_callable=some_callable_object)
def load_user(username, some_callable=some_callable_object):
    user = bitunix.DB.get(username)
    return user

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse({"request": request}, "login.html")


@app.websocket("/wsmain")
async def websocket_endpoint(websocket: WebSocket):
    await asyncio.create_task(wsmain(websocket))

async def wsmain(websocket):
    query_params = websocket.query_params
    
    try:
        logger.info("local main page WebSocket connection opened")
        
        await websocket.accept()
        bitunix.websocket_connections.add(websocket)

        queue = asyncio.Queue()
        queueTask = asyncio.create_task(send_data_queue(websocket, queue))    
        while True:
            stime=time.time()
            data={}
            try:
                
                # Handle incoming ping messages
                await asyncio.create_task(send_pong(websocket,queue))

                #combined data
                dataframes={
                    "portfolio" : bitunix.bitunixSignal.portfoliodfStyle, 
                    "positions" : bitunix.bitunixSignal.positiondfStyle, 
                    "orders" : bitunix.bitunixSignal.orderdfStyle,
                    "signals" : bitunix.bitunixSignal.signaldfStyle,
                    "study" : bitunix.bitunixSignal.allsignaldfStyle,
                    "positionHistory" : bitunix.bitunixSignal.positionHistorydfStyle
                }
                notifications=bitunix.bitunixSignal.notifications.get_notifications()          

                utc_time = datetime.fromtimestamp(bitunix.bitunixSignal.lastAutoTradeTime, tz=pytz.UTC)
                atctime = utc_time.astimezone(pytz.timezone('US/Central')).strftime('%Y-%m-%d %H:%M:%S')
                utc_time = datetime.fromtimestamp(bitunix.bitunixSignal.lastTickerDataTime, tz=pytz.UTC)
                tdctime = utc_time.astimezone(pytz.timezone('US/Central')).strftime('%Y-%m-%d %H:%M:%S')

                data = {
                    "dataframes": dataframes,
                    "profit" : bitunix.bitunixSignal.profit,
                    "atctime": atctime,
                    "tdctime": tdctime,
                    "status_messages": [] if len(notifications)==0 else notifications
                }

                await queue.put(json.dumps(data))

            except WebSocketDisconnect:
                bitunix.websocket_connections.remove(websocket)
                logger.info("local main page WebSocket connection closed")
                break
            except Exception as e:
                logger.info(f"local main page websocket unexpected error1: {e}") 
                break      

            elapsed_time = time.time() - stime
            
            if settings.VERBOSE_LOGGING:
                logger.info(f"wsmain: elapsed time {elapsed_time}")
            time_to_wait = max(0.01, bitunix.screen_refresh_interval - elapsed_time)
            
            await asyncio.sleep(time_to_wait)
            
    except Exception as e:
        logger.info(f"local main page websocket unexpected error2: {e}")       
    finally:
        queueTask.cancel()
        try:
            await queueTask
        except asyncio.CancelledError:
            pass
       
        
@app.websocket("/wschart")
async def websocket_endpoint(websocket: WebSocket):
    await asyncio.create_task(wschart(websocket))

async def wschart(websocket):    
    query_params = websocket.query_params
    ticker = query_params.get("ticker")
    
    try:
        logger.info("local chart page WebSocket connection opened")

        await websocket.accept()
        bitunix.websocket_connections.add(websocket)

        queue = asyncio.Queue()
        queueTask = asyncio.create_task(send_data_queue(websocket, queue))    

        while True:
            stime=time.time()
            try:

                # Handle incoming ping messages
                await asyncio.create_task(send_pong(websocket,queue))
                
                if ticker in bitunix.bitunixSignal.tickerObjects.symbols():
                    bars=settings.BARS
                    chart1m=list(bitunix.bitunixSignal.tickerObjects.get(ticker).get_interval_ticks('1m').get_data()[-bars:])
                    chart5m=list(bitunix.bitunixSignal.tickerObjects.get(ticker).get_interval_ticks('5m').get_data()[-bars:])
                    chart15m=list(bitunix.bitunixSignal.tickerObjects.get(ticker).get_interval_ticks('15m').get_data()[-bars:])
                    chart1h=list(bitunix.bitunixSignal.tickerObjects.get(ticker).get_interval_ticks('1h').get_data()[-bars:])
                    chart1d=list(bitunix.bitunixSignal.tickerObjects.get(ticker).get_interval_ticks('1d').get_data()[-bars:])
                    buysell=list(bitunix.bitunixSignal.tickerObjects.get(ticker).trades)
                    close=bitunix.bitunixSignal.tickerObjects.get(ticker).get_last()
                    notifications=bitunix.bitunixSignal.notifications.get_notifications()          

                    data = {
                        "symbol": ticker,
                        "close":close,
                        "chart1m":chart1m,
                        "chart5m":chart5m,
                        "chart15m":chart15m,
                        "chart1h":chart1h,
                        "chart1d":chart1d,
                        "buysell": buysell,
                        "status_messages": [] if len(notifications)==0 else notifications
                    }
                
                    await queue.put(json.dumps(data))

            except WebSocketDisconnect:
                bitunix.websocket_connections.remove(websocket)
                logger.info("local chart page WebSocket connection closed")
                break
            except Exception as e:
                logger.info(f"local chart page websocket unexpected error1: {e}")
                break        

            
            elapsed_time = time.time() - stime
            if settings.VERBOSE_LOGGING:
                logger.info(f"wschart: elapsed time {elapsed_time}")
            time_to_wait = max(0.01, bitunix.screen_refresh_interval - elapsed_time)
            await asyncio.sleep(time_to_wait)
    except Exception as e:
        logger.info(f"local chart page websocket unexpected error2: {e}")     
    finally:
        queueTask.cancel()
        try:
            await queueTask
        except asyncio.CancelledError:
            pass
            
async def send_pong(websocket, queue):
    # Handle incoming ping messages
    try:
        message = await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
        if message == "ping":
            await queue.put("pong")
    except asyncio.TimeoutError:
        pass

async def send_data_queue(websocket, queue):
    while True:
        try:
            data = await queue.get()
            await websocket.send_text(data)
        except Exception as e:
            pass

@app.get("/send-message/{msg}")
async def send_message(msg: str):
    await asyncio.create_task(bitunix.send_message_to_websocket(msg))
    return {"message": f"Sent: {msg}"}        


@app.get("/private")
async def get_private_endpoint(user=Depends(login_manager)):
    return "You are an authenticated user"
   
@app.post("/handle_bitunix_click") 
async def handle_click(symbol: str = Form(...)):
    # Handle the row click event here 
    message = f"https://www.bitunix.com/contract-trade/{symbol}" 
    return {"message": message}                                                   

@app.post("/handle_order_close_click") 
async def handle_click(symbol: str = Form(...), orderId: str = Form(...)):
    datajs = await bitunix.bitunixApi.CancelOrder(symbol, orderId)
    bitunix.bitunixSignal.notifications.add_notification(f'closing pending order for {symbol} {datajs["msg"]}')

@app.post("/handle_close_click") 
async def handle_click(symbol: str = Form(...), positionId: str = Form(...), qty: str = Form(...), unrealizedPNL: str = Form(...), realizedPNL: str = Form(...)):
    datajs = await bitunix.bitunixApi.FlashClose(positionId)
    pnl=float(unrealizedPNL)+float(realizedPNL)
    bitunix.bitunixSignal.notifications.add_notification(f'closing {qty} {symbol} with a profit/loss of {pnl} ({datajs["code"]} {datajs["msg"]}')

@app.post("/handle_buy_click") 
async def handle_click(symbol: str = Form(...), close: str = Form(...)):
    balance = bitunix.bitunixSignal.get_portfolio_tradable_balance()
    qty= str(balance * float(settings.ORDER_AMOUNT_PERCENTAGE) / float(close) * int(settings.LEVERAGE))
    datajs = await bitunix.bitunixApi.PlaceOrder(symbol,qty,close,'BUY')
    bitunix.bitunixSignal.notifications.add_notification(f'Buying {qty} {symbol} @ {close} ({datajs["code"]} {datajs["msg"]})')

@app.post("/handle_add_click") 
async def handle_click(symbol: str = Form(...), close: str = Form(...)):
    row = bitunix.bitunixSignal.positiondf.loc[bitunix.bitunixSignal.positiondf['symbol'] == symbol]
    if not row.empty:
        balance = float(bitunix.bitunixSignal.portfoliodf["available"])+float(bitunix.bitunixSignal.portfoliodf["crossUnrealizedPNL"])
        qty= str(balance * float(settings.ORDER_AMOUNT_PERCENTAGE) / float(close) * int(settings.LEVERAGE))
        datajs = await bitunix.bitunixApi.PlaceOrder(symbol,qty,close,row['side'].values[0])
        bitunix.bitunixSignal.notifications.add_notification(f'adding {row["side"].values[0]} {qty} {symbol} @ {close} ({datajs["code"]} {datajs["msg"]})')

@app.post("/handle_sell_click") 
async def handle_click(symbol: str = Form(...), close: str = Form(...)):
    balance = bitunix.bitunixSignal.get_portfolio_tradable_balance()
    qty= str(balance * float(settings.ORDER_AMOUNT_PERCENTAGE) / float(close) * int(settings.LEVERAGE))
    datajs = await bitunix.bitunixApi.PlaceOrder(symbol,qty,close,'SELL')
    bitunix.bitunixSignal.notifications.add_notification(f'Selling {qty} {symbol} @ {close} ({datajs["code"]} {datajs["msg"]})')

@app.post("/handle_reduce_click") 
async def handle_click(symbol: str = Form(...), positionId: str = Form(...), qty: str = Form(...),  close: str = Form(...)):
    row = bitunix.bitunixSignal.positiondf.loc[bitunix.bitunixSignal.positiondf['symbol'] == symbol]
    if not row.empty:
        balance = bitunix.bitunixSignal.get_portfolio_tradable_balance()
        qty= str(float(qty) / 2)
        datajs = await bitunix.bitunixApi.PlaceOrder(symbol,qty,close,'BUY' if row['side'].values[0]=='SELL' else 'SELL',positionId=positionId, reduceOnly=True)
        bitunix.bitunixSignal.notifications.add_notification(f'reducing {row["side"]} {qty} {symbol} @ {close} ({datajs["code"]} {datajs["msg"]})')

#called by the click even on the symbol and then open the chart page with query parm symbol
@app.post("/get_charts", response_class=HTMLResponse) 
async def handle_chart_data(symbol: str = Form(...)):
    chart_url = f"/charts?symbol={symbol}"
    return JSONResponse(content={"message": chart_url})                                      

#when chart page detected
@app.get("/charts", response_class=HTMLResponse) 
async def show_charts(request: Request, symbol: str): 
    return templates.TemplateResponse({"request": request, "data": symbol}, "charts.html")

@app.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    return templates.TemplateResponse("config.html", {"request": request})

@app.get("/get-config")
async def get_env_variables():
    config = read_config(CONFIG_FILE)  # Load .env variables
    return JSONResponse(content=config)

# Save updated environment variables
@app.post("/save-config")
async def save_env_variable(key: str = Form(...), value: str = Form(...)):
    # Read the existing configuration
    config = read_config(CONFIG_FILE)
    # Temporarily update the config dictionary for validation
    config[key] = value
    try:
        # Test the new configuration using the Settings class
        temp_settings = Settings(**config)
        # Write the valid configuration back to the file
        write_config(CONFIG_FILE, config)
        settings = temp_settings
        await bitunix.update_settings(settings)
        await asyncio.create_task(get_server_states(app, settings))
        return {"message": f"Updated {key} = {value} successfully"}
    except ValidationError as e:
        return {"error": "Validation failed", "details": e.errors()}

def read_config(file_path):
    """Read the config file into a dictionary."""
    config = {}
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            for line in file:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    config[key] = value
    return config

def write_config(file_path, config):
    """Write the dictionary back to the config file."""
    with open(file_path, "w") as file:
        for key, value in config.items():
            file.write(f"{key}={value}\n")

@app.get("/logs", response_class=HTMLResponse)
async def config_page(request: Request):
    return templates.TemplateResponse("logs.html", {"request": request})

@app.websocket("/wslogs")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()  # Accept the WebSocket connection
    await stream_log_file(websocket)

async def stream_log_file(websocket: WebSocket):
    try:
        with open(LOG_FILE, "r") as log_file:
            # Read all lines into memory
            lines = log_file.readlines()
            # Determine starting point: offset_from_end
            start_index = max(len(lines) - 100, 0)
            for line in lines[start_index:]:  # Yield existing lines from offset
                await websocket.send_text(line) 
            # Stream new lines added to the file
            log_file.seek(0, 2)  # Go to the end of the file
            while True:
                line = log_file.readline()
                if not line:
                    await asyncio.sleep(0.1)  # Wait briefly if no new line is added
                    continue
                await websocket.send_text(line) 
    except WebSocketDisconnect:
        print("log Client disconnected. Stopping the log stream.")

def log_settings():
    #load env variable from .env
    logger.info(f"autoTrade: {settings.AUTOTRADE}")
    logger.info(f"leverage: {settings.LEVERAGE}")
    logger.info(f"threshold: {settings.THRESHOLD}")
    logger.info(f"min_volume: {settings.MIN_VOLUME}")
    logger.info(f"order_amount_percentage: {settings.ORDER_AMOUNT_PERCENTAGE}")
    logger.info(f"max_auto_trades: {settings.MAX_AUTO_TRADES}")
    logger.info(f"profit_amount: {settings.PROFIT_AMOUNT}")
    logger.info(f"loss_amount: {settings.LOSS_AMOUNT}")
    logger.info(f"option_moving_average: {settings.OPTION_MOVING_AVERAGE}")
    logger.info(f"bars: {settings.BARS}")
    logger.info(f"ma_fast: {settings.MA_FAST}")
    logger.info(f"ma_medium: {settings.MA_MEDIUM}")
    logger.info(f"ma_slow: {settings.MA_SLOW}")
    logger.info(f"ema_study: {settings.EMA_STUDY}")
    logger.info(f"macd_study: {settings.MACD_STUDY}")
    logger.info(f"bbm_study: {settings.BBM_STUDY}")
    logger.info(f"rsi_study: {settings.RSI_STUDY}")
    logger.info(f"adx_study: {settings.ADX_STUDY}")
    logger.info(f"candle_trend_study: {settings.CANDLE_TREND_STUDY}")
    logger.info(f"ema_check_on_open: {settings.EMA_CHECK_ON_OPEN}")
    logger.info(f"ema_check_on_close: {settings.EMA_CHECK_ON_CLOSE}")
    logger.info(f"macd_check_on_open: {settings.MACD_CHECK_ON_OPEN}")
    logger.info(f"macd_check_on_close: {settings.MACD_CHECK_ON_CLOSE}")
    logger.info(f"bbm_check_on_open: {settings.BBM_CHECK_ON_OPEN}")
    logger.info(f"bbm_check_on_close: {settings.BBM_CHECK_ON_CLOSE}")
    logger.info(f"rsi_check_on_open: {settings.RSI_CHECK_ON_OPEN}")
    logger.info(f"rsi_check_on_close: {settings.RSI_CHECK_ON_CLOSE}")
    logger.info(f"candle_trend_check_on_open: {settings.CANDLE_TREND_CHECK_ON_OPEN}")
    logger.info(f"candle_trend_check_on_close: {settings.CANDLE_TREND_CHECK_ON_CLOSE}")
    logger.info(f"adx_check_on_open: {settings.ADX_CHECK_ON_OPEN}")
    logger.info(f"adx_check_on_close: {settings.ADX_CHECK_ON_CLOSE}")
    logger.info(f"screen_refresh_interval: {settings.SCREEN_REFRESH_INTERVAL}")
    logger.info(f"signal_check_interval: {settings.SIGNAL_CHECK_INTERVAL}")
    logger.info(f"portfolio_api_interval: {settings.PORTFOLIO_API_INTERVAL}")
    logger.info(f"pending_positions_api_interval: {settings.PENDING_POSITIONS_API_INTERVAL}")
    logger.info(f"pending_orders_api_interval: {settings.PENDING_ORDERS_API_INTERVAL}")
    logger.info(f"trade_history_api_interval: {settings.TRADE_HISTORY_API_INTERVAL}")
    logger.info(f"position_history_api_interval: {settings.POSITION_HISTORY_API_INTERVAL}")
    logger.info(f"ticker_data_api_interval: {settings.TICKER_DATA_API_INTERVAL}")
    logger.info(f"public_websocket_restart_interval: {settings.PUBLIC_WEBSOCKET_RESTART_INTERVAL}")
    logger.info(f"use_public_websocket: {settings.USE_PUBLIC_WEBSOCKET}")
    logger.info(f"VERBOSE_LOGGING: {settings.VERBOSE_LOGGING}")
    logger.info(f"benchmark: {settings.BENCHMARK}")         
    
if __name__ == '__main__': 
    
    bitunix = bitunix(PASSWORD, API_KEY, SECRET_KEY, settings)
    
    log_settings()
    
    import uvicorn
    if settings.VERBOSE_LOGGING:
        llevel = "debug"
    else:
        llevel = "error"  
    config1 = uvicorn.Config(app, host=HOST, port=8000, log_level=llevel, reload=False)
    server = uvicorn.Server(config1)
    server.run()

