import asyncio 
import os
import uvicorn
import numpy as np
import pandas as pd
import json
import time
from datetime import datetime, timezone, timedelta
import pytz
from ThreadManager import ThreadManager
from BitunixApi import BitunixApi
from BitunixSignal import BitunixSignal
from NotificationManager import NotificationManager
from config import Settings

from logger import Logger
logger = Logger(__name__).get_logger()

from dotenv import load_dotenv

from fastapi import FastAPI, Request, Form, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import HTMLResponse , JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from fastapi.security import OAuth2PasswordRequestForm
from fastapi_login import LoginManager
from fastapi_login.exceptions import InvalidCredentialsException
import gc
from DataFrameHtmlRenderer import DataFrameHtmlRenderer
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
settings = Settings()

class bitunix():
    def __init__(self, settings):
        self.settings=settings
        self.bars=self.settings.bars
        self.screen_refresh_interval =self.settings.screen_refresh_interval
        
        self.autoTrade=self.settings.autoTrade
        
        self.password=self.settings.password.get_secret_value()

        self.threadManager = ThreadManager()
        self.notifications = NotificationManager()
        self.bitunixApi = BitunixApi(self.settings)
        self.bitunixSignal = BitunixSignal(self.settings, self.threadManager, self.notifications, self.bitunixApi)
        
        self.websocket_connections = set()
        self.DB = {"admin": {"password": self.password}}

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
templates = Jinja2Templates(directory="templates")
SECRET=os.getenv('SECRET')
manager = LoginManager(SECRET, token_url="/auth/login", use_cookie=True)
manager.cookie_name = "auth_token"


@app.post("/auth/login")
async def login(data: OAuth2PasswordRequestForm = Depends()):
    start=time.time()
    username = data.username
    password = data.password
    
    user = load_user(username, some_callable_object)
    if not user or password != user["password"]:
        raise InvalidCredentialsException
    access_token = manager.create_access_token(data={"sub": username})
    response = RedirectResponse(url="/main", status_code=302)
    manager.set_cookie(response, access_token)
    logger.info(f"/auth/login: elapsed time {time.time()-start}")
    return response

@app.get("/main", response_class=HTMLResponse)
async def main_page(request: Request,  user=Depends(manager)):
    return templates.TemplateResponse({"request": request, "user": user}, "main.html")

  
@app.on_event("startup")  
async def startup_event():
    await asyncio.create_task(get_server_states(bitunix, app))
    await bitunix.start()

#load inital states for html
async def get_server_states(bitunix, app):
    app.state.element_states = {}
    app.state.element_states['autoTrade']=settings.autoTrade
    app.state.element_states['optionMovingAverage']=settings.option_moving_average
    app.state.element_states['profitAmount']=settings.profit_amount
    app.state.element_states['lossAmount']=settings.loss_amount
    app.state.element_states['maxAutoTrades']=settings.max_auto_trades

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

@app.post("/autotrade")
async def handle_autotrade():
    await asyncio.create_task(set_server_states())
    return {"status":bitunix.bitunixSignal.autoTrade}

async def set_server_states():
    bitunix.bitunixSignal.autoTrade = True if app.state.element_states['autoTrade']=='true' else False

    if bitunix.bitunixSignal.autoTrade:
        bitunix.bitunixSignal.option_moving_average = app.state.element_states['optionMovingAverage']
        bitunix.bitunixSignal.notifications.add_notification(f"optionMovingAverage: {bitunix.bitunixSignal.option_moving_average}")  

        bitunix.bitunixSignal.profit_amount = app.state.element_states['profitAmount']
        bitunix.bitunixSignal.notifications.add_notification(f"profitAmount: {bitunix.bitunixSignal.profit_amount}")  

        bitunix.bitunixSignal.loss_amount = app.state.element_states['lossAmount']
        bitunix.bitunixSignal.notifications.add_notification(f"lossAmount: {bitunix.bitunixSignal.loss_amount}")  

        bitunix.bitunixSignal.max_auto_trades = app.state.element_states['maxAutoTrades']
        bitunix.bitunixSignal.notifications.add_notification(f"maxAutoTrades: {bitunix.bitunixSignal.max_auto_trades}")  

    bitunix.bitunixSignal.notifications.add_notification(" AutoTrade activated" if bitunix.bitunixSignal.autoTrade else "AutoTrade de-activated")  

def some_callable_object():
    logger.info("called")

@manager.user_loader(some_callable=some_callable_object)
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
            
            if settings.verbose_logging:
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
                    bars=bitunix.bars
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
            if settings.verbose_logging:
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
async def get_private_endpoint(user=Depends(manager)):
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
    qty= str(balance * float(bitunix.bitunixSignal.orderAmountPercentage) / float(close) * int(bitunix.bitunixSignal.leverage))
    datajs = await bitunix.bitunixApi.PlaceOrder(symbol,qty,close,'BUY')
    bitunix.bitunixSignal.notifications.add_notification(f'Buying {qty} {symbol} @ {close} ({datajs["code"]} {datajs["msg"]})')

@app.post("/handle_add_click") 
async def handle_click(symbol: str = Form(...), close: str = Form(...)):
    row = bitunix.bitunixSignal.positiondf.loc[bitunix.bitunixSignal.positiondf['symbol'] == symbol]
    if not row.empty:
        balance = float(bitunix.bitunixSignal.portfoliodf["available"])+float(bitunix.bitunixSignal.portfoliodf["crossUnrealizedPNL"])
        qty= str(balance * float(bitunix.bitunixSignal.orderAmountPercentage) / float(close) * int(bitunix.bitunixSignal.leverage))
        datajs = await bitunix.bitunixApi.PlaceOrder(symbol,qty,close,row['side'].values[0])
        bitunix.bitunixSignal.notifications.add_notification(f'adding {row["side"].values[0]} {qty} {symbol} @ {close} ({datajs["code"]} {datajs["msg"]})')

@app.post("/handle_sell_click") 
async def handle_click(symbol: str = Form(...), close: str = Form(...)):
    balance = bitunix.bitunixSignal.get_portfolio_tradable_balance()
    qty= str(balance * float(bitunix.bitunixSignal.orderAmountPercentage) / float(close) * int(bitunix.bitunixSignal.leverage))
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
async def show_detail(request: Request, symbol: str): 
    return templates.TemplateResponse({"request": request, "data": symbol}, "charts.html")
    
@app.post("/get_study")
async def trades_detected():
    study_url = f"/study"
    return JSONResponse(content={"message": study_url})                                      

#when trades page detected
@app.get("/study", response_class=HTMLResponse) 
async def show_detail(request: Request): 
    return templates.TemplateResponse({"request": request}, "study.html")

if __name__ == '__main__': 
    print(pd.__version__)
    exit()
    
    bitunix = bitunix(settings)

    #load env variable from .env
    logger.info(f"autoTrade: {settings.autoTrade}")
    logger.info(f"leverage: {settings.leverage}")
    logger.info(f"threshold: {settings.threshold}")
    logger.info(f"min_volume: {settings.min_volume}")
    logger.info(f"order_amount_percentage: {settings.order_amount_percentage}")
    logger.info(f"max_auto_trades: {settings.max_auto_trades}")
    logger.info(f"profit_amount: {settings.profit_amount}")
    logger.info(f"loss_amount: {settings.loss_amount}")
    logger.info(f"option_moving_average: {settings.option_moving_average}")
    logger.info(f"bars: {settings.bars}")
    logger.info(f"ma_fast: {settings.ma_fast}")
    logger.info(f"ma_medium: {settings.ma_medium}")
    logger.info(f"ma_slow: {settings.ma_slow}")
    logger.info(f"ema_study: {settings.ema_study}")
    logger.info(f"macd_study: {settings.macd_study}")
    logger.info(f"bbm_study: {settings.bbm_study}")
    logger.info(f"rsi_study: {settings.rsi_study}")
    logger.info(f"candle_trend_study: {settings.candle_trend_study}")
    logger.info(f"ema_check_on_open: {settings.ema_check_on_open}")
    logger.info(f"ema_check_on_close: {settings.ema_check_on_close}")
    logger.info(f"macd_check_on_open: {settings.macd_check_on_open}")
    logger.info(f"macd_check_on_close: {settings.macd_check_on_close}")
    logger.info(f"bbm_check_on_open: {settings.bbm_check_on_open}")
    logger.info(f"bbm_check_on_close: {settings.bbm_check_on_close}")
    logger.info(f"rsi_check_on_open: {settings.rsi_check_on_open}")
    logger.info(f"rsi_check_on_close: {settings.rsi_check_on_close}")
    logger.info(f"candle_trend_check_on_open: {settings.candle_trend_check_on_open}")
    logger.info(f"candle_trend_check_on_close: {settings.candle_trend_check_on_close}")
    logger.info(f"close_on_reverse: {settings.close_on_reverse}")
    logger.info(f"screen_refresh_interval: {settings.screen_refresh_interval}")
    logger.info(f"signal_check_interval: {settings.signal_check_interval}")
    logger.info(f"portfolio_api_interval: {settings.portfolio_api_interval}")
    logger.info(f"pending_positions_api_interval: {settings.pending_positions_api_interval}")
    logger.info(f"pending_orders_api_interval: {settings.pending_orders_api_interval}")
    logger.info(f"trade_history_api_interval: {settings.trade_history_api_interval}")
    logger.info(f"position_history_api_interval: {settings.position_history_api_interval}")
    logger.info(f"ticker_data_api_interval: {settings.ticker_data_api_interval}")
    logger.info(f"public_websocket_restart_interval: {settings.public_websocket_restart_interval}")
    logger.info(f"use_public_websocket: {settings.use_public_websocket}")
    logger.info(f"verbose_logging: {settings.verbose_logging}")
    logger.info(f"benchmark: {settings.benchmark}")


    import uvicorn
    host = os.getenv("host")
    if settings.verbose_logging:
        llevel = "debug"
    else:
        llevel = "error"  
    config1 = uvicorn.Config(app, host=host, port=8000, log_level=llevel, reload=False)
    server = uvicorn.Server(config1)
    server.run()

