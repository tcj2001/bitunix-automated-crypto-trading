import numpy as np
import pandas as pd
import json
import asyncio
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import traceback
import time
import pytz
from concurrent.futures import ProcessPoolExecutor
from BitunixWebSocket import BitunixPrivateWebSocketClient, BitunixPublicWebSocketClient
from AsyncThreadRunner import AsyncThreadRunner
from TickerManager import Tickers, Ticker, Interval
from DataFrameHtmlRenderer import DataFrameHtmlRenderer
from logger import Logger, Colors
colors = Colors()
import gc
import os
from concurrent.futures import ProcessPoolExecutor
import sqlite3
import queue
from collections import deque
import threading


cst = pytz.timezone('US/Central')

class BitunixSignal:
    def __init__(self, api_key, secret_key, settings, threadManager, notifications, bitunixApi, logger):
        self.api_key = api_key
        self.secret_key = secret_key
        self.settings=settings
        self.threadManager = threadManager
        self.notifications = notifications
        self.bitunixApi = bitunixApi
        self.logger = logger
              
        #Ticker object
        self.tickerObjects = Tickers(self.settings, self.logger)
        
        #these are used for html rendering as well as storing
        self.signaldf= pd.DataFrame()
        self.positiondf= pd.DataFrame()
        self.positiondf2= pd.DataFrame()
        self.portfoliodf=pd.DataFrame()
        self.orderdf=pd.DataFrame()
        self.tickerdf=pd.DataFrame()
        self.inspectdf=pd.DataFrame()
        self.tradesdf=pd.DataFrame() 
        self.positionHistorydf=pd.DataFrame() 
        
        self.portfoliodfrenderer=None
        self.positiondfrenderer=None
        self.orderdfrenderer=None
        self.signaldfrenderer=None
        self.allsignaldfrenderer=None
        self.positionHistorydfrenderer=None
        
        self.portfoliodfStyle=None
        self.positiondfStyle=None   
        self.orderdfStyle=None
        self.signaldfStyle=None
        self.allsignaldfStyle=None
        self.positionHistorydfStyle=None
        
        #postion, order, etc
        self.pendingOrders=None
        self.pendingPositions=None
        self.portfolioData=None
        self.tradeHistoryData=None
        self.positionHistoryData=None
        
        #this contain all data
        self.signaldf_full = pd.DataFrame()
        self.signaldf_filtered = pd.DataFrame()

        #websockets
        self.bitunixPrivateWebSocketClient = BitunixPrivateWebSocketClient(self.api_key, self.secret_key, logger)
        
        if self.settings.USE_PUBLIC_WEBSOCKET:
            self.bitunixPublicDepthWebSocketClient = BitunixPublicWebSocketClient(self.api_key, self.secret_key, "depth", logger)
            self.bitunixPublicTickerWebSocketClient = BitunixPublicWebSocketClient(self.api_key, self.secret_key, "ticker", logger)

        self.tickerList=[]

        self.green="#A5DFDF"
        self.red="#FFB1C1"
        
        self.profit=0
        
        self.lastAutoTradeTime = time.time()
        self.lastTickerDataTime = time.time()
        
        #sqllite database connection
        self.connection = sqlite3.connect(self.settings.DATABASE) 
        
    async def update_settings(self, settings):
        self.settings = settings
        self.tickerObjects.update_settings(settings)
        
    async def load_tickers(self):
        if self.settings.TICKERS=="":
            symbols = await self.bitunixApi.GetTickerList(float(self.settings.THRESHOLD), float(self.settings.MIN_VOLUME))
            self.pendingPositions= await self.bitunixApi.GetPendingPositionData()
            self.pendingOrders= await self.bitunixApi.GetPendingOrderData()
            olist=[]
            plist=[]
            if self.pendingPositions:
                plist = [entry['symbol'] for entry in self.pendingPositions]
            if self.pendingOrders['orderList']:
                olist = [entry['symbol'] for entry in self.pendingOrders['orderList']]
            newlist=olist+plist+list(set(symbols))
            self.tickerList=newlist[:300]
            self.tickerList.remove("STMXUSDT")
            #self.tickerList=['POLUSDT']
        else:
            self.tickerList = self.settings.TICKERS.split(",")
            self.tickerList = [sym.strip().upper() for sym in self.tickerList if sym.strip()]

        [await self.add_ticker_to_tickerObjects(sym) for sym in self.tickerList]
        self.notifications.add_notification(f"{len(self.tickerList)} ticker list loaded") 
        
    async def add_ticker_to_tickerObjects(self, symbol):
        if not self.tickerObjects.get(symbol):
            self.tickerObjects.add(symbol)
            
    async def start_jobs(self):
        #setup renderers
        await asyncio.create_task(self.DefinehtmlRenderers())

        #async thread that runs forever jobs
        self.GetportfolioDataTask = AsyncThreadRunner(self.GetportfolioData, self.logger, interval=int(self.settings.PORTFOLIO_API_INTERVAL))
        self.GetportfolioDataTask.start_thread(thread_name="GetportfolioData")

        self.GetPendingPositionDataTask = AsyncThreadRunner(self.GetPendingPositionData, self.logger, interval=int(self.settings.PENDING_POSITIONS_API_INTERVAL))
        self.GetPendingPositionDataTask.start_thread(thread_name="GetPendingPositionData")

        self.GetPendingOrderDataTask = AsyncThreadRunner(self.GetPendingOrderData, self.logger, interval=int(self.settings.PENDING_ORDERS_API_INTERVAL))
        self.GetPendingOrderDataTask.start_thread(thread_name="GetPendingOrderData")

        self.GetTradeHistoryDataTask = AsyncThreadRunner(self.GetTradeHistoryData, self.logger, interval=int(self.settings.TRADE_HISTORY_API_INTERVAL))
        self.GetTradeHistoryDataTask.start_thread(thread_name="GetTradeHistoryData")
       
        self.GetPositionHistoryDataTask = AsyncThreadRunner(self.GetPositionHistoryData, self.logger, interval=int(self.settings.POSITION_HISTORY_API_INTERVAL))
        self.GetPositionHistoryDataTask.start_thread(thread_name="GetPositionHistoryData")
       
        self.ProcessPrivateDataTask = AsyncThreadRunner(self.bitunixPrivateWebSocketClient.run_websocket, self.logger, 0, self.ProcessPrivateData)
        self.ProcessPrivateDataTask.start_thread(thread_name="ProcessPrivateData")

        if self.settings.USE_PUBLIC_WEBSOCKET:
            self.bitunixPublicDepthWebSocketClient.tickerList = self.tickerList
            self.StoreDepthDataTask = AsyncThreadRunner(self.bitunixPublicDepthWebSocketClient.run_websocket, self.logger, 0, self.StoreDepthData)
            self.StoreDepthDataTask.start_thread(thread_name="StoreDepthData")
            self.depth_que = asyncio.Queue()
            self.ProcessDepthDataTask = AsyncThreadRunner(self.ProcessDepthData, self.logger, interval=0) # run only once
            self.ProcessDepthDataTask.start_thread(thread_name="ProcessDepthData")

            self.bitunixPublicTickerWebSocketClient.tickerList = self.tickerList
            self.StoreTickerDataTask = AsyncThreadRunner(self.bitunixPublicTickerWebSocketClient.run_websocket, self.logger, 0, self.StoreTickerData)
            self.StoreTickerDataTask.start_thread(thread_name="StoreTickerData")
            self.ticker_que = asyncio.Queue()
            self.ProcessTickerDataTask = AsyncThreadRunner(self.ProcessTickerData, self.logger, interval=0) # run only once
            self.ProcessTickerDataTask.start_thread(thread_name="ProcessTickerData")
            

        #normal processes
        self.LoadKlineHistoryTask = AsyncThreadRunner(self.LoadKlineHistory, self.logger, interval=0) # run only once
        self.LoadKlineHistoryTask.start_thread(thread_name="LoadKlineHistory")

        self.AutoTradeProcessTask = AsyncThreadRunner(self.AutoTradeProcess, self.logger, interval=int(self.settings.SIGNAL_CHECK_INTERVAL))
        self.AutoTradeProcessTask.start_thread(thread_name="AutoTradeProcess")

        self.checkTickerAndAutotradeStatusTask = AsyncThreadRunner(self.checkTickerAndAutotradeStatus, self.logger, interval=0)
        self.checkTickerAndAutotradeStatusTask.start_thread(thread_name="checkTickerAndAutotradeStatus")

        if not self.settings.USE_PUBLIC_WEBSOCKET:
            self.GetTickerDataTask = AsyncThreadRunner(self.GetTickerData, self.logger, interval=int(self.settings.TICKER_DATA_API_INTERVAL))
            self.GetTickerDataTask.start_thread(thread_name="GetTickerData")



    ###########################################################################################################
    async def DefinehtmlRenderers(self):
        period = self.settings.OPTION_MOVING_AVERAGE
        #html rendering setup
        self.portfoliodfrenderer = DataFrameHtmlRenderer()
        self.positiondfrenderer = DataFrameHtmlRenderer(hide_columns=["positionId", "lastcolor","bidcolor","askcolor",f"{period}_barcolor"], \
                                                color_column_mapping={"bid": "bidcolor",
                                                                        "last": "lastcolor",
                                                                        "ask": "askcolor",
                                                                    f"{period}_cb": f"{period}_barcolor"
                                                            })
        self.orderdfrenderer = DataFrameHtmlRenderer()
        self.signaldfrenderer = DataFrameHtmlRenderer(hide_columns=["1d_barcolor","1h_barcolor","15m_barcolor","5m_barcolor","1m_barcolor","lastcolor","bidcolor","askcolor"], \
                                                color_column_mapping={"bid": "bidcolor",
                                                                    "last": "lastcolor",
                                                                    "ask": "askcolor",
                                                                    "1d_cb": "1d_barcolor",
                                                                    "1h_cb": "1h_barcolor",
                                                                    "15m_cb": "15m_barcolor",
                                                                    "5m_cb": "5m_barcolor",
                                                                    "1m_cb": "1m_barcolor"
                                                            })

        #html rendering setup
        self.allsignaldfrenderer = DataFrameHtmlRenderer(hide_columns=["1d_barcolor","1h_barcolor","15m_barcolor","5m_barcolor","1m_barcolor","lastcolor","bidcolor","askcolor"], \
                                                color_column_mapping={"bid": "bidcolor",
                                                                    "last": "lastcolor",
                                                                    "ask": "askcolor",
                                                                    "1d_cb": "1d_barcolor",
                                                                    "1h_cb": "1h_barcolor",
                                                                    "15m_cb": "15m_barcolor",
                                                                    "5m_cb": "5m_barcolor",
                                                                    "1m_cb": "1m_barcolor"
                                                            })        
        self.positionHistorydfrenderer = DataFrameHtmlRenderer()
        

    ###########################################################################################################
    #load kline history
    async def LoadKlineHistory(self):
        start = time.time()
        intervals = self.tickerObjects.get_intervalIds()
        for ticker in self.tickerList:
            for intervalId in intervals:
                data = await self.bitunixApi.GetKlineHistory(ticker, intervalId, self.settings.BARS, int(time.time()))
                if data is not None:
                   self.tickerObjects.load_kline_history(ticker, intervalId, self.settings.BARS, data)
        if self.settings.VERBOSE_LOGGING:
            self.logger.info(f"kline_history: elapsed time {time.time()-start}")
        self.notifications.add_notification("Kline history loaded")

    #api data       
    async def GetTickerData(self):
        if not self.settings.USE_PUBLIC_WEBSOCKET:
            start=time.time()
            # Get the current time and set the seconds and microseconds to zero
            current_time = datetime.now()
            current_minute = current_time.replace(second=0, microsecond=0)
            ts = int(current_minute.timestamp())*1000

            #api used insted of websocket
            data = await self.bitunixApi.GetTickerData()
            self.tickerdf = pd.DataFrame()
            if data:
                
                # Create a DataFrame from the data
                self.tickerdf = pd.DataFrame(data, columns=["symbol", "last"])
                
                #remove not required symbols
                self.tickerdf.loc[~self.tickerdf['symbol'].isin(self.tickerObjects.symbols()), :] = None
                self.tickerdf.dropna(inplace=True)
                
                self.tickerdf['ts']=ts
                self.tickerdf["tickerObj"] = self.tickerdf["symbol"].map(self.tickerObjects.get_tickerDict())
                self.tuples_list = list(zip(self.tickerdf["tickerObj"],  self.tickerdf["last"].astype(float), self.tickerdf["ts"]))
                self.tickerObjects.form_candle(self.tuples_list)

            self.lastTickerDataTime = time.time()
            if self.settings.VERBOSE_LOGGING:
                self.logger.info(f"GetTickerData: elapsed time {time.time()-start}")
            if self.settings.BENCHMARK:
                self.connection = sqlite3.connect(self.settings.DATABASE) 
                self.cursor = self.connection.cursor()
                self.cursor.execute("INSERT INTO benchmark (process_name, time) VALUES (?, ?)", ("GetTickerData", time.time()-start))
                self.connection.commit()
    
    async def drain_queue(self, queue):
        items = []
        while not queue.empty():
            items.append(await queue.get())
        return deque(items[::-1][:self.settings.BATCH_PROCESS_SIZE])  # Reverse items    

    #websocket data to update ticker lastprice and other relavent data
    # Function to add data to the last price deque
    async def StoreTickerData(self, message):
        if self.settings.USE_PUBLIC_WEBSOCKET and message:
            await self.ticker_que.put(message)

    # Function to process the last price deque
    async def ProcessTickerData(self):
        while True:
            try:
                latest_data = {}
                reversed_items = await self.drain_queue(self.ticker_que)
                while reversed_items:
                    message = reversed_items.popleft()
                    data = json.loads(message)
                    if data.get('symbol') and data.get('ch') == 'ticker':
                        symbol = data["symbol"]
                        ts = data["ts"]
                        if symbol not in latest_data or ts > latest_data[symbol]['ts']:
                            latest_data[symbol] = {'ts': ts, 'last': float(data['data']['la'])}
                    await asyncio.sleep(0.01)
                # Convert to DataFrame
                self.tickerdf = pd.DataFrame.from_dict(latest_data, orient="index")
                if not self.tickerdf.empty:
                    self.tickerdf["tickerObj"] = self.tickerdf.index.map(self.tickerObjects.get_tickerDict())
                    self.tuples_list = list(zip(self.tickerdf["tickerObj"],  self.tickerdf["last"].astype(float), self.tickerdf["ts"]))
                    self.tickerObjects.form_candle(self.tuples_list)
                    self.lastTickerDataTime = time.time()
            except Exception as e:
                self.logger.info(f"Function: ProcessTickerData, {e}, {e.args}, {type(e).__name__}")
                self.logger.info(traceback.print_exc())
            await asyncio.sleep(0.01)
        self.logger.info(f"ProcessTickerData: exitied out of the loop, exiting app")
        os._exit(1)  # Exit the program 
            

    #websocket data to update bid and ask
    async def StoreDepthData(self, message):
        if self.settings.USE_PUBLIC_WEBSOCKET and message:
            await self.depth_que.put(message)
 
    # Function to process the bid, ask
    async def ProcessDepthData(self):
        while True:
            try:
                latest_data = {}
                reversed_items = await self.drain_queue(self.depth_que)
                while reversed_items:
                    message = reversed_items.popleft()
                    data = json.loads(message)
                    if data.get('symbol') and data.get('ch') == 'depth_book1':
                        symbol = data["symbol"]
                        ts = data["ts"]
                        if symbol not in latest_data or ts > latest_data[symbol]['ts']:
                            latest_data[symbol] = {'ts': ts, 'bid': float(data['data']['b'][0][0]), 'ask': float(data['data']['a'][0][0])}
                    await asyncio.sleep(0.01)
                # Convert to DataFrame
                self.depthdf = pd.DataFrame.from_dict(latest_data, orient="index")
                if not self.depthdf.empty:
                    self.depthdf["tickerObj"] = self.depthdf.index.map(self.tickerObjects.get_tickerDict())
                    self.depthdf.apply(self.apply_depth_data2, axis=1)
            except Exception as e:
                self.logger.info(f"Function: ProcessTickerData, {e}, {e.args}, {type(e).__name__}")
                self.logger.info(traceback.print_exc())
            await asyncio.sleep(0.01)
        self.logger.info(f"ProcessDepthData: exitied out of the loop, exiting app")
        os._exit(1)  # Exit the program 

    def apply_depth_data2(self, row):
        row["tickerObj"].set_ask(row["ask"])
        row["tickerObj"].set_bid(row["bid"])
        return row
        
    # non websocket method
    # this is called to update last price, as the websocket is lagging
    # this is only called for the tickers in the pendingpositions
    # and for first few records in the signaldf    
    async def apply_last_data(self, symbols):
        start=time.time()
        try:
            # Get the current time and set the seconds and microseconds to zero
            current_time = datetime.now()
            current_minute = current_time.replace(second=0, microsecond=0)
            ts = int(current_minute.timestamp())*1000
            
            data= await self.bitunixApi.GetTickerslastPrice(symbols)
            if data is None:
                return
            tickerdf = pd.DataFrame(data, columns=["symbol", "markPrice", "lastPrice", "open", "last", "quoteVol", "baseVol", "high", "low"])
            tickerdf['ts']=ts
            tickerdf["tickerObj"] = tickerdf["symbol"].map(self.tickerObjects.get_tickerDict())
            tuples_list = list(zip(tickerdf["tickerObj"],  tickerdf["last"].astype(float), tickerdf["ts"]))
            self.tickerObjects.form_candle(tuples_list)
            del data, tickerdf, tuples_list
            gc.collect()
        except Exception as e:
            self.logger.info(e)
        if self.settings.VERBOSE_LOGGING:
            self.logger.info(f"apply_last_data: elapsed time {time.time()-start}")
        
    # non websocket method
    # this is called to update bid and ask, 
    # as it is time consuming to call the api for each ticker, 
    # this is only called for the tickers in the pendingpositions
    # and for first few records in the signaldf    
    async def apply_depth_data(self, ticker):
        ddata = await self.bitunixApi.GetDepthData(ticker,"1")
        if ddata is not None and 'bids' in ddata:
            bid = float(ddata['bids'][0][0])
            ask = float(ddata['asks'][0][0])
            tickerObj=self.tickerObjects.get(ticker)
            if tickerObj:
                tickerObj.set_bid(bid)
                tickerObj.set_ask(ask)
                del tickerObj
                gc.collect()
            await asyncio.sleep(0)
        del ddata
        gc.collect()
                
    ###########################################################################################################
    async def checkTickerAndAutotradeStatus(self):
        while True:
            if self.lastAutoTradeTime + 300 < time.time()  or self.lastTickerDataTime + 300 < time.time():
                self.notifications.add_notification("AutoTradeProcess or GetTickerData is not running")
                os._exit(1) 
                break
            await asyncio.sleep(300)

    async def GetportfolioData(self):
        start=time.time()
        try:
            self.portfolioData = await self.bitunixApi.GetportfolioData()
            if self.portfolioData:
                self.portfoliodf=pd.DataFrame(self.portfolioData,index=[0])[["marginCoin","available","margin","crossUnrealizedPNL"]]
                self.portfoliodf = self.portfoliodf.astype({"marginCoin": str, "available": float, "margin": float, "crossUnrealizedPNL": float})
                self.portfoliodf['Value'] =round(self.portfoliodf['margin'] + self.portfoliodf['crossUnrealizedPNL'] + self.portfoliodf['available'],2)
            else:
                self.portfolioData = pd.DataFrame()
            self.portfoliodfStyle= self.portfoliodfrenderer.render_html(self.portfoliodf[["Value", "marginCoin", "available", "margin", "crossUnrealizedPNL"]])
            
        except Exception as e:
            self.logger.info(f"Function: GetportfolioData, {e}, {e.args}, {type(e).__name__}")
        if self.settings.VERBOSE_LOGGING:
            self.logger.info(f"GetportfolioData: elapsed time {time.time()-start}")
                
    async def GetPendingPositionData(self):
        start=time.time()
        try:
            self.pendingPositions = await self.bitunixApi.GetPendingPositionData()
            if self.pendingPositions:
                self.positiondf = pd.DataFrame(self.pendingPositions, columns=["positionId", "symbol", "side", "unrealizedPNL", "realizedPNL",  "qty", "ctime", "avgOpenPrice"])
                self.positiondf['bid']=0.0
                self.positiondf['bidcolor']=""
                self.positiondf['last']=0.0
                self.positiondf['lastcolor']=""
                self.positiondf['ask']=0.0
                self.positiondf['askcolor']=""
                self.positiondf['ctime']=pd.to_datetime(self.positiondf['ctime'].astype(float), unit='ms').dt.tz_localize('UTC').dt.tz_convert(cst).dt.strftime('%Y-%m-%d %H:%M:%S')

                try:
                    self.positiondf = self.positiondf.assign(
                        bid=self.positiondf['symbol'].map(lambda sym: self.tickerObjects.get(sym).get_bid()),
                        bidcolor=self.positiondf['symbol'].map(lambda sym: self.tickerObjects.get(sym).bidcolor),
                        last=self.positiondf['symbol'].map(lambda sym: self.tickerObjects.get(sym).get_last()),
                        lastcolor=self.positiondf['symbol'].map(lambda sym: self.tickerObjects.get(sym).lastcolor),
                        ask=self.positiondf['symbol'].map(lambda sym: self.tickerObjects.get(sym).get_ask()),
                        askcolor=self.positiondf['symbol'].map(lambda sym: self.tickerObjects.get(sym).askcolor)
                    )
                except Exception as e:
                    pass

                self.positiondf['markprice']= (self.positiondf['bid'] + self.positiondf['ask']) / 2
                self.positiondf = self.positiondf.astype({"unrealizedPNL": float, "realizedPNL": float, "markprice": float, "last": float, "qty": float, "avgOpenPrice": float})
                self.positiondf['ROI'] = self.positiondf.apply(
                    lambda row: round((row['unrealizedPNL'] / (row['qty'] * row['avgOpenPrice'])) * 100 * self.settings.LEVERAGE,2), 
                    axis=1
                )
                #print(self.positiondf[['symbol', 'ROI','markprice', 'qty', 'avgOpenPrice']].head())
                
                self.positiondf['charts'] = self.positiondf.apply(self.add_charts_button, axis=1)
                self.positiondf['bitunix'] = self.positiondf.apply(self.add_bitunix_button, axis=1)
                self.positiondf['action'] = self.positiondf.apply(self.add_close_button, axis=1)
                self.positiondf['add'] = self.positiondf.apply(self.add_add_button, axis=1)
                self.positiondf['reduce'] = self.positiondf.apply(self.add_reduce_button, axis=1)

                self.positiondf['bid'] = self.positiondf['bid'].astype('float64')
                self.positiondf['last'] = self.positiondf['last'].astype('float64')
                self.positiondf['ask'] = self.positiondf['ask'].astype('float64')
            else:
                self.positiondf = pd.DataFrame()
                self.positiondfStyle= self.positiondfrenderer.render_html(self.positiondf)    

            #if not self.settings.USE_PUBLIC_WEBSOCKET:                    
            #get bid las ask using api for the symbols in pending psotion
            if not self.positiondf.empty:
                if not self.settings.USE_PUBLIC_WEBSOCKET:
                    await asyncio.create_task(self.apply_last_data(','.join(self.positiondf['symbol'].astype(str).tolist())))                                                
                    await asyncio.gather(
                        *[
                            asyncio.create_task(self.apply_depth_data(row['symbol']))
                            for index, row in self.positiondf.iterrows()
                        ]
                    )                
                    

        except Exception as e:
            self.logger.info(f"Function: GetPendingPositionData, {e}, {e.args}, {type(e).__name__}")
        if self.settings.VERBOSE_LOGGING:
            self.logger.info(f"GetPendingPositionData: elapsed time {time.time()-start}")

    async def GetPendingOrderData(self):
        start=time.time()
        try:
            self.pendingOrders = await self.bitunixApi.GetPendingOrderData()
            if self.pendingOrders and 'orderList' in self.pendingOrders:
                self.orderdf = pd.DataFrame(self.pendingOrders['orderList'], columns=["orderId", "symbol", "qty", "side", "price", "ctime", "status", "reduceOnly"])
                self.orderdf['rtime']=pd.to_datetime(self.orderdf['ctime'].astype(float), unit='ms').dt.tz_localize('UTC').dt.tz_convert(cst).dt.strftime('%Y-%m-%d %H:%M:%S')
                self.orderdf['charts'] = self.orderdf.apply(self.add_charts_button, axis=1)
                self.orderdf['bitunix'] = self.orderdf.apply(self.add_bitunix_button, axis=1)
                self.orderdf['action'] = self.orderdf.apply(self.add_order_close_button, axis=1)
            else:
                self.orderdf = pd.DataFrame()
            self.orderdfStyle= self.orderdfrenderer.render_html(self.orderdf)                
            
        except Exception as e:
            self.logger.info(f"Function: GetPendingOrderData, {e}, {e.args}, {type(e).__name__}")
        if self.settings.VERBOSE_LOGGING:
            self.logger.info(f"GetPendingOrderData: elapsed time {time.time()-start}")

    async def GetPositionHistoryData(self):
        start=time.time()
        try:
            self.positionHistoryData = await self.bitunixApi.GetPositionHistoryData()
            if self.positionHistoryData and 'positionList' in self.positionHistoryData:
                self.positionHistorydf = pd.DataFrame(self.positionHistoryData['positionList'], columns=["symbol", "side","realizedPNL", "ctime", "mtime","maxQty", "closePrice","fee", "funding"])
                self.positionHistorydf = self.positionHistorydf.astype({"realizedPNL": float, "maxQty": float, "closePrice": float})
                self.positionHistorydf['ROI'] = self.positionHistorydf.apply(
                    lambda row: round((row['realizedPNL'] / (row['maxQty'] * row['closePrice'])) * 100 * self.settings.LEVERAGE,2), 
                    axis=1
                )
                
                self.positionHistorydf['ctime'] = pd.to_datetime(self.positionHistorydf['ctime'].astype(float), unit='ms').dt.tz_localize('UTC').dt.tz_convert(cst).dt.strftime('%Y-%m-%d %H:%M:%S')
                self.positionHistorydf['mtime'] = pd.to_datetime(self.positionHistorydf['mtime'].astype(float), unit='ms').dt.tz_localize('UTC').dt.tz_convert(cst).dt.strftime('%Y-%m-%d %H:%M:%S')
                self.positionHistorydf['charts'] = self.positionHistorydf.apply(self.add_charts_button, axis=1)
                self.positionHistorydf['bitunix'] = self.positionHistorydf.apply(self.add_bitunix_button, axis=1)

            else:
                self.positionHistorydf = pd.DataFrame()
            self.positionHistorydfStyle= self.positionHistorydfrenderer.render_html(self.positionHistorydf[["symbol", "side", "ROI", "realizedPNL", "ctime", "mtime", "maxQty", "closePrice", "fee", "funding",  "charts", "bitunix"]])
            
        except Exception as e:
            self.logger.info(f"Function: GetPositionHistoryData, {e}, {e.args}, {type(e).__name__}")
        if self.settings.VERBOSE_LOGGING:
            self.logger.info(f"GetPositionHistoryData: elapsed time {time.time()-start}")

    async def GetTradeHistoryData(self):
        start=time.time()
        try:
            self.tradeHistoryData = await self.bitunixApi.GetTradeHistoryData()
            if self.tradeHistoryData and 'tradeList' in self.tradeHistoryData:
                self.tradesdf = pd.DataFrame(self.tradeHistoryData['tradeList'], columns=["symbol", "ctime", "qty", "side", "price","realizedPNL","reduceOnly"])
                self.tradesdf['rtime'] = pd.to_datetime(self.tradesdf['ctime'].astype(float), unit='ms').dt.tz_localize('UTC').dt.tz_convert(cst).dt.strftime('%Y-%m-%d %H:%M:%S')
                grouped_trades = self.tradesdf.groupby("symbol")
                for symbol, tickerObj in self.tickerObjects.get_tickerDict().items():
                    if symbol in grouped_trades.groups:
                        # Filter trades for the current symbol and convert them to a list of dicts
                        tickerObj.trades = grouped_trades.get_group(symbol).to_dict("records")                
        except Exception as e:
            self.logger.info(f"Function: GetTradeHistoryData, {e}, {e.args}, {type(e).__name__}")
        if self.settings.VERBOSE_LOGGING:
            self.logger.info(f"GetTradeHistoryData: elapsed time {time.time()-start}")

        
    ###########################################################################################################

    async def BuySellList(self, period):
        try:
            #ticker in positions and orders
            inuse1=[] 
            inuse2=[] 
            if not self.positiondf.empty: 
                inuse1 = self.positiondf['symbol'].to_list() 
            if not self.orderdf.empty: 
                inuse2 = self.orderdf['symbol'].to_list() 
            inuseTickers = set(inuse1 + inuse2)
            
            # Extract buy/sell ticker data
            self.signaldf_filtered = pd.DataFrame();
            self.tickerObjects.getCurrentData(period)

            self.signaldf_full = self.tickerObjects.signaldf_full

            if self.signaldf_full.empty:
                self.positiondf2 = self.positiondf
                self.positiondfStyle= self.positiondfrenderer.render_html(self.positiondf)           
                return

            self.signaldf_full['charts'] = self.signaldf_full.apply(self.add_charts_button, axis=1)
            self.signaldf_full['bitunix'] = self.signaldf_full.apply(self.add_bitunix_button, axis=1)
            

            self.allsignaldfStyle= self.allsignaldfrenderer.render_html(self.signaldf_full)
            
            self.signaldf_filtered = self.tickerObjects.signaldf_filtered

            if not self.positiondf.empty and not self.signaldf_full.empty:
                    columns=['symbol', f"{period}_trend", f"{period}_cb", f"{period}_barcolor", 
                             f"{period}_bos",
                             f"{period}_ema_open", f"{period}_ema_close", f"{period}_macd", f"{period}_bbm", f"{period}_rsi", f"{period}_trendline", f"{period}_candle_trend", f"{period}_open", f"{period}_close", f"{period}_high", f"{period}_low"]
                    columns2=["qty", "side", "unrealizedPNL", "realizedPNL", "ctime", "avgOpenPrice", "bid", "bidcolor", "last", "lastcolor", "ask", "askcolor", "charts", "bitunix", "action", "add", "reduce"]
                    if set(columns).issubset(self.signaldf_full.columns) and set(columns2).issubset(self.positiondf.columns):
                        columnOrder= ['symbol', "side", "ROI", "unrealizedPNL", "realizedPNL", f"{period}_trend", f"{period}_cb", f"{period}_barcolor", 
                                      f"{period}_bos",
                                      f"{period}_ema_open", f"{period}_ema_close", f"{period}_macd", f"{period}_bbm", f"{period}_rsi", f"{period}_trendline", f"{period}_adx", f"{period}_candle_trend", f"{period}_open", f"{period}_close", f"{period}_high", f"{period}_low", "qty", "ctime", "avgOpenPrice", "bid", "bidcolor", "last", "lastcolor", "ask", "askcolor", "charts", "bitunix", "action", "add", "reduce"]                
                        self.positiondf2 = pd.merge(self.positiondf, self.signaldf_full[["symbol", f"{period}_open", f"{period}_close", f"{period}_high", f"{period}_low", 
                                f"{period}_bos",                                                               
                                f"{period}_ema_open", f"{period}_ema_close", f"{period}_macd", f"{period}_bbm", f"{period}_rsi", f"{period}_trendline", f"{period}_adx", f"{period}_candle_trend",
                                f"{period}_trend",f"{period}_cb", f"{period}_barcolor"]], left_on="symbol", right_index=True, how="left")[columnOrder]    
                        self.positiondfStyle= self.positiondfrenderer.render_html(self.positiondf2)
            else:
                self.positiondf2 = pd.DataFrame()
                
            if not self.signaldf_filtered.empty:
                #remove those that are in positon and orders
                self.signaldf_filtered = self.signaldf_filtered[~(self.signaldf_filtered['symbol'].isin(inuseTickers))]

                if not self.signaldf_filtered.empty:
                    # Assign to self.signaldf for HTML rendering
                    self.signaldf = self.signaldf_filtered[[
                        "symbol", f"{period}_trend",f"{period}_cb", f"{period}_barcolor",
                        f"{period}_bos",
                        f"{period}_ema_open", f"{period}_ema_close", f"{period}_macd", f"{period}_bbm", f"{period}_rsi", f"{period}_trendline",f"{period}_adx",f"{period}_candle_trend",
                        'lastcolor', 'bidcolor', 'askcolor', 'bid', 'last', 'ask',
                        f"{period}_open", f"{period}_close", f"{period}_high", f"{period}_low", 
                    ]].sort_values(by=[f'{period}_cb'], ascending=[False])

                    # Add buttons
                    self.signaldf['charts'] = self.signaldf.apply(self.add_charts_button, axis=1)
                    self.signaldf['bitunix'] = self.signaldf.apply(self.add_bitunix_button, axis=1)
                    self.signaldf['buy'] = self.signaldf.apply(self.add_buy_button, axis=1)
                    self.signaldf['sell'] = self.signaldf.apply(self.add_sell_button, axis=1)
                else:
                    self.signaldf = pd.DataFrame()
                self.signaldfStyle= self.signaldfrenderer.render_html(self.signaldf)

                #if not self.settings.USE_PUBLIC_WEBSOCKET:                    
                #get bid las ask using api for max_auto_trades rows
                if not self.signaldf.empty:
                    m = min(self.signaldf.shape[0], int(self.settings.MAX_AUTO_TRADES))
                    if not self.settings.USE_PUBLIC_WEBSOCKET:
                        await asyncio.create_task(self.apply_last_data(','.join(self.signaldf['symbol'][:m].astype(str).tolist())))                 
                        await asyncio.gather(
                            *[
                                asyncio.create_task(self.apply_depth_data(row['symbol']))
                                for index, row in self.signaldf[:m].iterrows()
                            ]
                        )  

        except Exception as e:
            self.logger.info(f"Function: BuySellList, {e}, {e.args}, {type(e).__name__}")
            self.logger.info(traceback.print_exc())
        del inuse1, inuse2, inuseTickers
        gc.collect()

    async def AutoTradeProcess(self):
        if self.settings.VERBOSE_LOGGING:
            self.logger.info(f"AutoTradeProcess started")
        start=time.time()
        
        period = self.settings.OPTION_MOVING_AVERAGE
        try:
            
            #calulate current data at selected period, this create signaldf
            await self.BuySellList(period)
            
            if not self.settings.AUTOTRADE:
                return
            ##############################################################################################################################
            # open long or short postition
            ##############################################################################################################################
            count=0
            self.pendingPositions = await self.bitunixApi.GetPendingPositionData({})
            if self.pendingPositions:
                count=count+len(self.pendingPositions)
            self.pendingOrders = await self.bitunixApi.GetPendingOrderData({})
            if self.pendingOrders:
                count=count+len(self.pendingOrders['orderList'])

            if count < int(self.settings.MAX_AUTO_TRADES):
                if not self.signaldf.empty:
                    #open position upto a max of max_auto_trades from the signal list
                    df=self.signaldf.copy(deep=False)
                    for index, row in df.iterrows():
                        side = "BUY" if row[f'{period}_barcolor'] == self.green and row[f'{period}_trend'] == "BUY"  else "SELL" if row[f'{period}_barcolor'] == self.red and row[f'{period}_trend'] == "SELL" else ""
                        if side != "":
                            select = True
                            self.pendingPositions = await self.bitunixApi.GetPendingPositionData({'symbol': row.symbol})
                            if self.pendingPositions and len(self.pendingPositions) == 1:
                                select = False
                            self.pendingOrders = await self.bitunixApi.GetPendingOrderData({'symbol': row.symbol})
                            if self.pendingOrders and len(self.pendingOrders['orderList']) == 1:
                                select = False
                            if select:
                                last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                price = (bid if side == "BUY" else ask if side == "SELL" else last) if bid<=last<=ask else last
                                balance = float(self.portfoliodf["available"].iloc[0]) + float(self.portfoliodf["crossUnrealizedPNL"].iloc[0])
                                qty= str(max(balance * (float(self.settings.ORDER_AMOUNT_PERCENTAGE) / 100) / price * int(self.settings.LEVERAGE),mtv))

                                self.notifications.add_notification(
                                    f'{colors.YELLOW} Opening {"long" if side=="BUY" else "short"} position for {row.symbol} with {qty} qty @ {price})'
                                )
                                datajs = await self.bitunixApi.PlaceOrder(row.symbol, qty, price, side)
                                count=count+1
                        if count >= int(self.settings.MAX_AUTO_TRADES):
                            break
                        await asyncio.sleep(0)
                    del df
                    gc.collect()

            ##############################################################################################################################
            # close long or short postition
            ##############################################################################################################################

            # Close orders that are open for a while
            current_time = time.time() * 1000
            df=self.orderdf.copy(deep=False)
            for index, row in df.iterrows():
                if current_time - int(row.ctime) > 60000:
                    self.notifications.add_notification(
                        f'{colors.LBLUE} Canceling order {row.orderId}, {row.symbol} {row.qty} created at {row.rtime} '
                    )
                    datajs = await self.bitunixApi.CancelOrder(row.symbol, row.orderId)
                await asyncio.sleep(0)

            if not self.positiondf.empty:
                df=self.positiondf.copy(deep=False)
                for index, row in df.iterrows():
                    unrealized_pnl = float(row.unrealizedPNL)
                    realized_pnl = float(row.realizedPNL)
                    total_pnl = unrealized_pnl + realized_pnl
                    side=row['side']

                    requiredCols=[f'{period}_open', f'{period}_close', f'{period}_high', f'{period}_low', f'{period}_ema_open', f"{period}_ema_close", f'{period}_macd', f'{period}_bbm', f'{period}_rsi', f'{period}_trendline', f'{period}_candle_trend', f'{period}_trend', f'{period}_cb', f'{period}_barcolor']    
                    required_cols = set(requiredCols)

                    # Close position that fall the below criteria
                    if not self.signaldf_full.columns.empty and self.signaldf_full['symbol'].isin([row.symbol]).any() and required_cols.issubset(set(self.signaldf_full.columns)):
                        
                        # Check orders
                        select = True
                        self.pendingOrders = await self.bitunixApi.GetPendingOrderData({'symbol': row.symbol})
                        if self.pendingOrders and len(self.pendingOrders['orderList']) == 1:
                            select = False
                            
                        if select and int(self.settings.MAX_AUTO_TRADES)!=0:
                        
                            # check take profit amount or accept loss amount
                            if float(self.settings.LOSS_AMOUNT) > 0 and total_pnl < -float(self.settings.LOSS_AMOUNT):
                                last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                price = (ask if row['side'] == "BUY" else bid if row['side'] == "SELL" else last) if bid<=last<=ask else last

                                self.notifications.add_notification(
                                    f'{colors.CYAN} Closing {"long" if side=="BUY" else "short"} position due to stop loss amount for {row.symbol} with {row.qty} qty @ {price})'
                                )
                                datajs = await self.bitunixApi.PlaceOrder(
                                    positionId=row.positionId,
                                    ticker=row.symbol,
                                    qty=row.qty,
                                    price=price,
                                    side=row.side,
                                    tradeSide="CLOSE"
                                )
                                continue

                            if float(self.settings.PROFIT_AMOUNT) > 0 and total_pnl > float(self.settings.PROFIT_AMOUNT):
                                last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                price = (ask if row['side'] == "BUY" else bid if row['side'] == "SELL" else last) if bid<=last<=ask else last

                                self.notifications.add_notification(
                                    f'{colors.CYAN} Closing {"long" if side=="BUY" else "short"} position  due to take profit amount for {row.symbol} with {row.qty} qty @ {price})'
                                )
                                datajs = await self.bitunixApi.PlaceOrder(
                                    positionId=row.positionId,
                                    ticker=row.symbol,
                                    qty=row.qty,
                                    price=price,
                                    side=row.side,
                                    tradeSide="CLOSE"
                                )
                                continue

                            # check take profit percentage or accept loss percentage
                            if float(self.settings.LOSS_PERCENTAGE) > 0 and row['ROI'] < -float(self.settings.LOSS_PERCENTAGE):
                                last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                price = (ask if row['side'] == "BUY" else bid if row['side'] == "SELL" else last) if bid<=last<=ask else last

                                self.notifications.add_notification(
                                    f'{colors.CYAN} Closing {"long" if side=="BUY" else "short"} position due to stop loss percentage for {row.symbol} with {row.qty} qty @ {price})'
                                )
                                datajs = await self.bitunixApi.PlaceOrder(
                                    positionId=row.positionId,
                                    ticker=row.symbol,
                                    qty=row.qty,
                                    price=price,
                                    side=row.side,
                                    tradeSide="CLOSE"
                                )
                                continue

                            if float(self.settings.PROFIT_PERCENTAGE) > 0 and row['ROI'] > float(self.settings.PROFIT_PERCENTAGE):
                                last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                price = (ask if row['side'] == "BUY" else bid if row['side'] == "SELL" else last) if bid<=last<=ask else last

                                self.notifications.add_notification(
                                    f'{colors.CYAN} Closing {"long" if side=="BUY" else "short"} position  due to take profit percentage for {row.symbol} with {row.qty} qty @ {price})'
                                )
                                datajs = await self.bitunixApi.PlaceOrder(
                                    positionId=row.positionId,
                                    ticker=row.symbol,
                                    qty=row.qty,
                                    price=price,
                                    side=row.side,
                                    tradeSide="CLOSE"
                                )
                                continue

                            # Moving average comparison between fast and medium or medium and slow
                            if self.settings.EMA_STUDY and self.settings.EMA_CHECK_ON_CLOSE: 
                                if row.side == 'BUY' and self.signaldf_full.at[row.symbol, f'{period}_ema_close'] == "SELL":
                                    last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                    price = (ask if row['side'] == "BUY" else bid if row['side'] == "SELL" else last) if bid<=last<=ask else last

                                    self.notifications.add_notification(
                                        f'{colors.CYAN} Closing {"long" if side=="BUY" else "short"} position due to MA {period} crossover for {row.symbol} with {row.qty} qty @ {price})'
                                    )
                                    datajs = await self.bitunixApi.PlaceOrder(
                                        positionId=row.positionId,
                                        ticker=row.symbol,
                                        qty=row.qty,
                                        price=price,
                                        side=row.side,
                                        tradeSide="CLOSE"
                                    )
                                    continue

                                if row.side == 'SELL' and self.signaldf_full.at[row.symbol, f'{period}_ema_close'] == "BUY":
                                    last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                    price = (ask if row['side'] == "BUY" else bid if row['side'] == "SELL" else last) if bid<=last<=ask else last
                                    self.notifications.add_notification(
                                        f'{colors.CYAN} Closing {"long" if side=="BUY" else "short"} position due to MA {period} crossover for {row.symbol} with {row.qty} qty @ {price})'
                                    )
                                    datajs = await self.bitunixApi.PlaceOrder(
                                        positionId=row.positionId,
                                        ticker=row.symbol,
                                        qty=row.qty,
                                        price=price,
                                        side=row.side,
                                        tradeSide="CLOSE"
                                    )
                                    continue

                            # MACD comparison between MACD and Signal
                            if self.settings.MACD_STUDY and self.settings.MACD_CHECK_ON_CLOSE:
                                if row.side == 'BUY' and self.signaldf_full.at[row.symbol, f'{period}_macd'] == "SELL":
                                    last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                    price = (ask if row['side'] == "BUY" else bid if row['side'] == "SELL" else last) if bid<=last<=ask else last
                                    self.notifications.add_notification(
                                        f'{colors.CYAN} Closing {"long" if side=="BUY" else "short"} position due to MACD {period} crossover for {row.symbol} with {row.qty} qty @ {price})'
                                    )
                                    datajs = await self.bitunixApi.PlaceOrder(
                                        positionId=row.positionId,
                                        ticker=row.symbol,
                                        qty=row.qty,
                                        price=price,
                                        side=row.side,
                                        tradeSide="CLOSE"
                                    )
                                    continue

                                if row.side == 'SELL'  and self.signaldf_full.at[row.symbol, f'{period}_macd'] == "BUY":
                                    last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                    price = (ask if row['side'] == "BUY" else bid if row['side'] == "SELL" else last) if bid<=last<=ask else last
                                    self.notifications.add_notification(
                                        f'{colors.CYAN} Closing {"long" if side=="BUY" else "short"} position due to MACD {period} crossover for {row.symbol} with {row.qty} qty @ {price})'
                                    )
                                    datajs = await self.bitunixApi.PlaceOrder(
                                        positionId=row.positionId,
                                        ticker=row.symbol,
                                        qty=row.qty,
                                        price=price,
                                        side=row.side,
                                        tradeSide="CLOSE"
                                    )
                                    continue

                            # Bollinger Band comparison between open and BBM
                            if self.settings.BBM_STUDY and self.settings.BBM_CHECK_ON_CLOSE:
                                if row.side == 'BUY' and self.signaldf_full.at[row.symbol, f'{period}_bbm'] == "SELL":
                                    last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                    price = (ask if row['side'] == "BUY" else bid if row['side'] == "SELL" else last) if bid<=last<=ask else last
                                    self.notifications.add_notification(
                                        f'{colors.CYAN} Closing {"long" if side=="BUY" else "short"} position due to BBM {period} crossover for {row.symbol} with {row.qty} qty @ {price})'
                                    )
                                    datajs = await self.bitunixApi.PlaceOrder(
                                        positionId=row.positionId,
                                        ticker=row.symbol,
                                        qty=row.qty,
                                        price=price,
                                        side=row.side,
                                        tradeSide="CLOSE"
                                    )
                                    continue

                                if row.side == 'SELL' and self.signaldf_full.at[row.symbol, f'{period}_bbm'] == "BUY":
                                    last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                    price = (ask if row['side'] == "BUY" else bid if row['side'] == "SELL" else last) if bid<=last<=ask else last
                                    self.notifications.add_notification(
                                        f'{colors.CYAN} Closing {"long" if side=="BUY" else "short"} position due to BBM {period} crossover for {row.symbol} with {row.qty} qty @ {price})'
                                    )
                                    datajs = await self.bitunixApi.PlaceOrder(
                                        positionId=row.positionId,
                                        ticker=row.symbol,
                                        qty=row.qty,
                                        price=price,
                                        side=row.side,
                                        tradeSide="CLOSE"
                                    )
                                    continue
                            
                            # RSI comparison
                            if self.settings.RSI_STUDY and self.settings.RSI_CHECK_ON_CLOSE:
                                if row.side == 'BUY' and self.signaldf_full.at[row.symbol, f'{period}_rsi'] == "SELL":
                                    last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                    price = (ask if row['side'] == "BUY" else bid if row['side'] == "SELL" else last) if bid<=last<=ask else last
                                    self.notifications.add_notification(
                                        f'{colors.CYAN} Closing {"long" if side=="BUY" else "short"} position due to RSI {period} crossover for {row.symbol} with {row.qty} qty @ {price})'
                                    )
                                    datajs = await self.bitunixApi.PlaceOrder(
                                        positionId=row.positionId,
                                        ticker=row.symbol,
                                        qty=row.qty,
                                        price=price,
                                        side=row.side,
                                        tradeSide="CLOSE"
                                    )
                                    continue

                                if row.side == 'SELL' and self.signaldf_full.at[row.symbol, f'{period}_rsi'] == "BUY":
                                    last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                    price = (ask if row['side'] == "BUY" else bid if row['side'] == "SELL" else last) if bid<=last<=ask else last
                                    self.notifications.add_notification(
                                        f'{colors.CYAN} Closing {"long" if side=="BUY" else "short"} position due to RSI {period} crossover for {row.symbol} with {row.qty} qty @ {price})'
                                    )
                                    datajs = await self.bitunixApi.PlaceOrder(
                                        positionId=row.positionId,
                                        ticker=row.symbol,
                                        qty=row.qty,
                                        price=price,
                                        side=row.side,
                                        tradeSide="CLOSE"
                                    )
                                    continue

                            # BOS
                            if self.settings.BOS_STUDY and self.settings.BOS_CHECK_ON_CLOSE: 
                                if row.side == 'BUY' and self.signaldf_full.at[row.symbol, f'{period}_bos'] == "SELL" and total_pnl < 0:
                                    last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                    price = (ask if row['side'] == "BUY" else bid if row['side'] == "SELL" else last) if bid<=last<=ask else last

                                    self.notifications.add_notification(
                                        f'{colors.CYAN} Closing {"long" if side=="BUY" else "short"} position due to {period} bos revrsal for {row.symbol} with {row.qty} qty @ {price})'
                                    )
                                    datajs = await self.bitunixApi.PlaceOrder(
                                        positionId=row.positionId,
                                        ticker=row.symbol,
                                        qty=row.qty,
                                        price=price,
                                        side=row.side,
                                        tradeSide="CLOSE"
                                    )
                                    continue

                                if row.side == 'SELL' and self.signaldf_full.at[row.symbol, f'{period}_bos'] == "BUY" and total_pnl <0:
                                    last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                    price = (ask if row['side'] == "BUY" else bid if row['side'] == "SELL" else last) if bid<=last<=ask else last
                                    self.notifications.add_notification(
                                        f'{colors.CYAN} Closing {"long" if side=="BUY" else "short"} position due to {period} bos reversal for {row.symbol} with {row.qty} qty @ {price})'
                                    )
                                    datajs = await self.bitunixApi.PlaceOrder(
                                        positionId=row.positionId,
                                        ticker=row.symbol,
                                        qty=row.qty,
                                        price=price,
                                        side=row.side,
                                        tradeSide="CLOSE"
                                    )
                                    continue

                            # TrendLine
                            if self.settings.TRENDLINE_STUDY and self.settings.TRENDLINE_CHECK_ON_CLOSE: 
                                if row.side == 'BUY' and self.signaldf_full.at[row.symbol, f'{period}_trendline'] == "SELL" and total_pnl < 0:
                                    last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                    price = (ask if row['side'] == "BUY" else bid if row['side'] == "SELL" else last) if bid<=last<=ask else last

                                    self.notifications.add_notification(
                                        f'{colors.CYAN} Closing {"long" if side=="BUY" else "short"} position due to {period} trendline reversalfor {row.symbol} with {row.qty} qty @ {price})'
                                    )
                                    datajs = await self.bitunixApi.PlaceOrder(
                                        positionId=row.positionId,
                                        ticker=row.symbol,
                                        qty=row.qty,
                                        price=price,
                                        side=row.side,
                                        tradeSide="CLOSE"
                                    )
                                    continue

                                if row.side == 'SELL' and self.signaldf_full.at[row.symbol, f'{period}_trendline'] == "BUY" and total_pnl < 0:
                                    last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                    price = (ask if row['side'] == "BUY" else bid if row['side'] == "SELL" else last) if bid<=last<=ask else last
                                    self.notifications.add_notification(
                                        f'{colors.CYAN} Closing {"long" if side=="BUY" else "short"} position due to {period} trendline reversal for {row.symbol} with {row.qty} qty @ {price})'
                                    )
                                    datajs = await self.bitunixApi.PlaceOrder(
                                        positionId=row.positionId,
                                        ticker=row.symbol,
                                        qty=row.qty,
                                        price=price,
                                        side=row.side,
                                        tradeSide="CLOSE"
                                    )
                                    continue

                            # Close on weak trend after open
                            if self.settings.ADX_STUDY and self.settings.ADX_CHECK_ON_CLOSE:
                                if row.side == 'BUY' and self.signaldf_full.at[row.symbol, f'{period}_adx'] == "WEAK":
                                    last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                    price = (ask if row['side'] == "BUY" else bid if row['side'] == "SELL" else last) if bid<=last<=ask else last
                                    self.notifications.add_notification(
                                        f'{colors.CYAN} Closing {"long" if side=="BUY" else "short"} position due to WEAK ADX for {row.symbol} with {row.qty} qty @ {price})'
                                    )
                                    datajs = await self.bitunixApi.PlaceOrder(
                                        positionId=row.positionId,
                                        ticker=row.symbol,
                                        qty=row.qty,
                                        price=price,
                                        side=row.side,
                                        tradeSide="CLOSE"
                                    )
                                    continue

                                if row.side == 'SELL' and self.signaldf_full.at[row.symbol, f'{period}_adx'] == "WEAK":
                                    last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                    price = (ask if row['side'] == "BUY" else bid if row['side'] == "SELL" else last) if bid<=last<=ask else last
                                    self.notifications.add_notification(
                                        f'{colors.CYAN} Closing {"long" if side=="BUY" else "short"} position due to WEAK ADX for {row.symbol} with {row.qty} qty @ {price})'
                                    )
                                    datajs = await self.bitunixApi.PlaceOrder(
                                        positionId=row.positionId,
                                        ticker=row.symbol,
                                        qty=row.qty,
                                        price=price,
                                        side=row.side,
                                        tradeSide="CLOSE"
                                    )
                                    continue

                            # candle reversed
                            if self.settings.CANDLE_TREND_STUDY and self.settings.CANDLE_TREND_REVERSAL_CHECK_ON_CLOSE:
                                if row.side == 'BUY' and self.signaldf_full.at[row.symbol, f'{period}_barcolor'] == self.red and self.signaldf_full.at[row.symbol, f'{period}_cb'] > 1 and self.signaldf_full.at[row.symbol, f'{period}_candle_trend'] == "BEARISH" and total_pnl < 0:
                                    last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                    price = (ask if row['side'] == "BUY" else bid if row['side'] == "SELL" else last) if bid<=last<=ask else last

                                    self.notifications.add_notification(
                                        f'{colors.CYAN} Closing {"long" if side=="BUY" else "short"} position due to bearish candle reversal for {row.symbol} with {row.qty} qty @ {price})'
                                    )
                                    datajs = await self.bitunixApi.PlaceOrder(
                                        positionId=row.positionId,
                                        ticker=row.symbol,
                                        qty=row.qty,
                                        price=price,
                                        side=row.side,
                                        tradeSide="CLOSE"
                                    )
                                    continue

                                if row.side == 'SELL' and self.signaldf_full.at[row.symbol, f'{period}_barcolor'] == self.green and self.signaldf_full.at[row.symbol, f'{period}_cb'] > 1 and self.signaldf_full.at[row.symbol, f'{period}_candle_trend'] == "BULLISH" and total_pnl < 0:
                                    last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                    price = (ask if row['side'] == "BUY" else bid if row['side'] == "SELL" else last) if bid<=last<=ask else last

                                    self.notifications.add_notification(
                                        f'{colors.CYAN} Closing {"long" if side=="BUY" else "short"} position due to bullish candle reversal for {row.symbol} with {row.qty} qty @ {price})'
                                    )
                                    datajs = await self.bitunixApi.PlaceOrder(
                                        positionId=row.positionId,
                                        ticker=row.symbol,
                                        qty=row.qty,
                                        price=price,
                                        side=row.side,
                                        tradeSide="CLOSE"
                                    )
                                    continue

                    await asyncio.sleep(0)
            
            self.lastAutoTradeTime = time.time()
        except Exception as e:
            stack = traceback.extract_stack()
            function_name = stack[-1].name
            self.logger.info(f"Function: {function_name}, {e}, {e.args}, {type(e).__name__}")
            self.logger.info(traceback.print_exc())
                
        if self.settings.VERBOSE_LOGGING:
            self.logger.info(f"AutoTradeProcess: elapsed time {time.time()-start}")
        if self.settings.BENCHMARK:
            self.connection = sqlite3.connect(self.settings.DATABASE) 
            self.cursor = self.connection.cursor()
            self.cursor.execute("INSERT INTO benchmark (process_name, time) VALUES (?, ?)", ("AutoTradeProcess", time.time()-start))
            self.connection.commit()

        del df
        gc.collect()
            
            
    async def GetTickerBidLastAsk(self, symbol):
        tdata = await self.bitunixApi.GetTickerslastPrice(symbol)
        if tdata:
            last=float(tdata[0]['lastPrice'])
        else:
            last=0.0
        ddata = await self.bitunixApi.GetDepthData(symbol,"1")
        if tdata:
            bid = float(ddata['bids'][0][0])
            ask = float(ddata['asks'][0][0])
        else:
            bid=0.0
            ask=0.0 
        pdata = await self.bitunixApi.GetTickersPair(symbol)
        if pdata:
            mtv=float(pdata[0]['minTradeVolume'])
        else:
            mtv=0.0
        tickerObj = self.tickerObjects.get(symbol)
        if tickerObj:
            tickerObj.set_last(last)
            tickerObj.set_bid(bid)
            tickerObj.set_ask(ask)        
            tickerObj.set_mtv(mtv)        
            del tdata, ddata, pdata, tickerObj
            gc.collect()
        return last,bid,ask,mtv

    async def ProcessPrivateData(self, message):
        if message=="":
            return
        try:
            feed = json.loads(message)
            if 'ch' not in feed:
                return

            channel = feed['ch']
            data = feed['data']

            if channel == 'order':
                
                symbol = data['symbol']
                qty = data['qty']
                side = data['side']
                price = data['price']
                event = data['event']
                orderStatus = data['orderStatus']
                self.notifications.add_notification(
                     f'{colors.LBLUE} {orderStatus} {"short" if side=="Sell" else "long"} order for {symbol} with {qty} qty (event: {event})'
                )

            elif channel == 'balance':
                
                self.available = data['available']
                self.margin = data['margin']
                # self.logger.info(feed)

            elif channel == 'position':
                
                ts = int(feed['ts'])
                symbol = data['symbol']
                qty = float(data['qty'])
                side = data['side']
                positionId = data['positionId']
                event = data['event']
                if 'entryValue' in data:
                    entryValue = float(data['entryValue'])
                else:
                    entryValue = 0
                price = entryValue / qty if entryValue != 0 and qty != 0 else 0

                if event == "OPEN":
                    self.notifications.add_notification(
                        f'{colors.PURPLE} Opened {side} position for {symbol} with {qty} qty @ {price}'
                    )

                elif event == "CLOSE":
                    datajs = await self.bitunixApi.GetPositionHistoryData({'positionId': positionId})
                    if datajs and len(datajs['positionList']) == 1:
                        position = datajs['positionList'][0]
                        profit = float(position['realizedPNL'])
                        price = float(position['closePrice'])
                        qty = float(position['maxQty'])
                        self.profit += profit
                        self.notifications.add_notification(
                            f'{colors.GREEN if profit>0 else colors.RED} Closed {side} position for {symbol} with {qty} qty @ {price} and {"profit" if profit>0 else "loss"} of {profit}'
                        )
                    del datajs
                    gc.collect()
                self.tickerObjects.get(symbol).trades.append({'ctime': ts, 'symbol': symbol, 'qty': qty, 'side': side, 'price': price})
            del feed
            gc.collect()
        except Exception as e:
            self.logger.info(f"Function: ProcessPrivateData, {e}, {e.args}, {type(e).__name__}")
            
    def color_cells(val, color):
        return f'background-color: {color}' if val else ''

    def add_charts_button(self, row):
        return f'<button onclick="handleChartsButton(\'{row["symbol"]}\')">charts</button>'

    def add_bitunix_button(self, row):
        return f'<button onclick="handleBitunixButton(\'{row["symbol"]}\')">show</button>'

    def add_buy_button(self, row):
        return f'<button onclick="handleBuyButton(\'{row["symbol"]}\',\'{row["last"]}\')">buy</button>'

    def add_add_button(self, row):
        return f'<button onclick="handleAddButton(\'{row["symbol"]}\',\'{row["last"]}\')">add</button>'

    def add_reduce_button(self, row):
        return f'<button onclick="handleReduceButton(\'{row["symbol"]}\',\'{row["positionId"]}\',\'{row["qty"]}\',\'{row["last"]}\')">reduce</button>'

    def add_sell_button(self, row):
        return f'<button onclick="handleSellButton(\'{row["symbol"]}\',\'{row["last"]}\')">sell</button>'

    def add_close_button(self, row):
        return f'<button onclick="handleCloseButton(\'{row["symbol"]}\',\'{row["positionId"]}\',\'{row["qty"]}\',\'{row["unrealizedPNL"]}\',\'{row["realizedPNL"]}\')">FlashClose</button>'

    def add_order_close_button(self, row):
        return f'<button onclick="handleOrderCloseButton(\'{row["symbol"]}\',\'{row["orderId"]}\')">close</button>'

    async def send_message_to_websocket(self,message):
        async def send_to_all():
            for ws in self.websocket_connections:
                await ws.send_text(message)
        asyncio.run(send_to_all())
        
    async def get_portfolio_tradable_balance(self):
        return float(self.portfoliodf["available"])+float(self.portfoliodf["crossUnrealizedPNL"])   
         
    async def convert_defaultdict_to_dict(self, d):
        if isinstance(d, defaultdict):
            d = {k: self.convert_defaultdict_to_dict(v) for k, v in d.items()}
        return d
    
 
    
