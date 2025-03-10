import asyncio 
import os
import uvicorn
import numpy as np
import pandas as pd
import json
import time

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
from tabulate import tabulate

load_dotenv()
settings = Settings()


#load env variable from .env
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
logger.info(f"check_ema: {settings.check_ema}")
logger.info(f"check_macd: {settings.check_macd}")
logger.info(f"check_bbm: {settings.check_bbm}")
logger.info(f"check_rsi: {settings.check_rsi}")
logger.info(f"screen_refresh_interval: {settings.screen_refresh_interval}")
logger.info(f"signal_interval: {settings.signal_interval}")
logger.info(f"api_interval: {settings.api_interval}")
logger.info(f"verbose_logging: {settings.verbose_logging}")
logger.info(f"autoTrade: {settings.autoTrade}")


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
        await self.bitunixSignal.restart_jobs()
        
    async def send_message_to_websocket(self,message):
        async def send_to_all():
            for ws in self.bitunixSignal.websocket_connections:
                await ws.send_text(message)
        asyncio.run(send_to_all())

    async def send_async_message_to_websocket(self,message):
            for ws in self.bitunixSignal.websocket_connections:
                await ws.send_text(message)
     
def apply_colors(row):
    return [
        f'background-color: {row["1m_barcolor"]}' if col == '1m_cb' else
        f'background-color: {row["5m_barcolor"]}' if col == '5m_cb' else
        f'background-color: {row["15m_barcolor"]}' if col == '15m_cb' else
        f'background-color: {row["1h_barcolor"]}' if col == '1h_cb' else 
        f'background-color: {row["1d_barcolor"]}' if col == '1d_cb' else 
        f'background-color: {row["lastcolor"]}' if col == 'last' else 
        f'background-color: {row["bidcolor"]}' if col == 'bid' else 
        f'background-color: {row["askcolor"]}' if col == 'ask' else ''
        for col in row.index
    ]


app = FastAPI()
templates = Jinja2Templates(directory="templates")
SECRET=os.getenv('SECRET')
manager = LoginManager(SECRET, token_url="/auth/login", use_cookie=True)
manager.cookie_name = "auth_token"


@app.post("/auth/login")
async def login(data: OAuth2PasswordRequestForm = Depends()):
    username = data.username
    password = data.password
    user = load_user(username, some_callable_object)
    if not user or password != user["password"]:
        raise InvalidCredentialsException
    access_token = manager.create_access_token(data={"sub": username})
    response = RedirectResponse(url="/main", status_code=302)
    manager.set_cookie(response, access_token)
    return response

@app.get("/main", response_class=HTMLResponse)
async def main_page(request: Request,  user=Depends(manager)):
    return templates.TemplateResponse({"request": request, "user": user}, "main.html")

#load inital states for html
def get_server_states(bitunix, app):
    app.state.element_states = {}
    app.state.element_states['autoTrade']=bitunix.bitunixSignal.autoTrade
    app.state.element_states['optionMovingAverage']=bitunix.bitunixSignal.option_moving_average
    app.state.element_states['profitAmount']=bitunix.bitunixSignal.profit_amount
    app.state.element_states['lossAmount']=bitunix.bitunixSignal.loss_amount
    app.state.element_states['maxAutoTrades']=bitunix.bitunixSignal.max_auto_trades

def set_server_states():
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
    
@app.on_event("startup")  
async def startup_event():
    get_server_states(bitunix, app)
    await bitunix.start()

@app.post("/reload")
async def refresh_detected():
    bitunix.bitunixSignal.notifications.add_notification("Reload detected!")
    await bitunix.restart()

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
    set_server_states()
    return {"status":bitunix.bitunixSignal.autoTrade}

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
    query_params = websocket.query_params

    await websocket.accept()
    bitunix.websocket_connections.add(websocket)
    try:
        while True:
            stime=time.time()
            #portfolio data
            data={}
            try:
                #portfolio data
                df=pd.DataFrame()
                if not bitunix.bitunixSignal.portfoliodf.empty:
                    df=bitunix.bitunixSignal.portfoliodf.copy(deep=True)
                #portfoliodfStyle = tabulate(df, headers='keys', tablefmt='html')
                portfoliodfStyle=df.style.set_table_attributes('class="dataframe"').to_html()
                    
                #position data
                df=pd.DataFrame()
                dfcols=["symbol","qty","side","unrealizedPNL","realizedPNL","ctime","avgOpenPrice","bid","bidcolor","last","lastcolor","ask","askcolor","bitunix","action","add","reduce"]
                if not bitunix.bitunixSignal.positiondf.empty and all(col in bitunix.bitunixSignal.positiondf.columns for col in dfcols):
                    df=bitunix.bitunixSignal.positiondf[dfcols].copy(deep=True)
                #positiondfStyle = tabulate(df, headers='keys', tablefmt='html')
                positiondfStyle=df.style.apply(apply_colors,axis=1).hide(["lastcolor","bidcolor","askcolor"],axis=1).set_table_attributes('class="dataframe"').to_html()
                    
                #order data
                df=pd.DataFrame()
                dfcols=["symbol","qty","side","price","ctime","status","reduceOnly","bitunix","action"]
                if not bitunix.bitunixSignal.orderdf.empty and all(col in bitunix.bitunixSignal.orderdf.columns for col in dfcols):
                    df=bitunix.bitunixSignal.orderdf[dfcols].copy(deep=True)
                #orderdfStyle = tabulate(df, headers='keys', tablefmt='html')
                orderdfStyle=df.style.set_table_attributes('class="dataframe"').to_html()
                    
                #signal data
                df=pd.DataFrame()
                dfcols=["symbol","1d_cb","1d_trend","1h_cb","1h_trend","15m_cb","15m_trend","5m_cb","5m_trend","1m_cb","1m_trend","bid","last","ask","bitunix","buy","sell","1d_barcolor","1h_barcolor","15m_barcolor","5m_barcolor","1m_barcolor","lastcolor","bidcolor","askcolor"]
                if not bitunix.bitunixSignal.signaldf.empty and all(col in bitunix.bitunixSignal.signaldf.columns for col in dfcols):
                    df=bitunix.bitunixSignal.signaldf[dfcols].copy(deep=True)
                #signaldfStyle = tabulate(df, headers='keys', tablefmt='html')
                signaldfStyle=df.style.apply(apply_colors,axis=1).hide(["1d_barcolor","1h_barcolor","15m_barcolor","5m_barcolor","1m_barcolor","lastcolor","bidcolor","askcolor"],axis=1).set_table_attributes('class="dataframe"').to_html()

                del df,dfcols
                gc.collect()
                
                #combined data
                dataframes={
                    "portfolio" : portfoliodfStyle, 
                    "positions" : positiondfStyle, 
                    "orders" : orderdfStyle,
                    "signals" : signaldfStyle
                }
                notifications=bitunix.bitunixSignal.notifications.get_notifications()          
                data = {
                    "dataframes": dataframes,
                    "profit" : bitunix.bitunixSignal.profit,
                    "status_messages": [] if len(notifications)==0 else notifications
                }
                await websocket.send_text(json.dumps(data))
                del data
                gc.collect()
            except Exception as e:
                logger.info(f"error gathering data for main page, {e}, {e.args}, {type(e).__name__}")

            elapsed_time = time.time() - stime
            if settings.verbose_logging:
                logger.info(f"wsmain: elapsed time {elapsed_time}")
            time_to_wait = max(0.01, bitunix.screen_refresh_interval - elapsed_time)
            await asyncio.sleep(time_to_wait)
            
    except WebSocketDisconnect:
        bitunix.websocket_connections.remove(websocket)
        logger.info("local main page WebSocket connection closed")
    except Exception as e:
        logger.info(f"local main page websocket unexpected error: {e}")        


@app.websocket("/wschart")
async def websocket_endpoint(websocket: WebSocket):
    query_params = websocket.query_params
    ticker = query_params.get("ticker")
    
    await websocket.accept()
    bitunix.websocket_connections.add(websocket)
    try:
        while True:
            stime=time.time()
            try:
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
                    await websocket.send_text(json.dumps(data))
                    
                    del data, chart1m, chart5m, chart15m, chart1h, chart1d, buysell
                    gc.collect()

            except Exception as e:
                logger.info(f"error gathering data for chart page, {e}, {e.args}, {type(e).__name__}")

            elapsed_time = time.time() - stime
            if settings.verbose_logging:
                logger.info(f"wschart: elapsed time {elapsed_time}")
            time_to_wait = max(0.01, bitunix.screen_refresh_interval - elapsed_time)
            await asyncio.sleep(time_to_wait)
            
    except WebSocketDisconnect:
        bitunix.websocket_connections.remove(websocket)
        logger.info("local chart page WebSocket connection closed")
    except Exception as e:
        logger.info(f"local chart page websocket unexpected error: {e}")        
    
@app.get("/send-message/{msg}")
async def send_message(msg: str):
    await bitunix.send_message_to_websocket(msg)
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

#when chart page opens
@app.get("/charts", response_class=HTMLResponse) 
async def show_detail(request: Request, symbol: str): 
    return templates.TemplateResponse({"request": request, "data": symbol}, "charts.html")
    
if __name__ == '__main__': 
    bitunix = bitunix(settings)

    import uvicorn
    host = os.getenv("host")
    config1 = uvicorn.Config(app, host=host, port=8000)
    server = uvicorn.Server(config1)
    server.run()
else: 
    bitunix = bitunix(settings)

