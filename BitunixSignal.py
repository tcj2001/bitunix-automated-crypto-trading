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
from config import Settings
from logger import Logger, Colors
logger = Logger(__name__).get_logger()
colors = Colors()
import gc

cst = pytz.timezone('US/Central')

class BitunixSignal:
    def __init__(self, settings : Settings, threadManager, notifications, bitunixApi):
        self.settings=settings
        self.threadManager = threadManager
        self.notifications = notifications
        self.bitunixApi = bitunixApi
              
        self.api_key = self.settings.api_key.get_secret_value()
        self.secret_key = self.settings.secret_key.get_secret_value()
        self.option_moving_average = self.settings.option_moving_average
        self.profit_amount = self.settings.profit_amount
        self.loss_amount = self.settings.loss_amount
        self.max_auto_trades = self.settings.max_auto_trades
        self.threshold = self.settings.threshold
        self.minVolume = self.settings.min_volume
        self.verbose_logging = self.settings.verbose_logging
        self.leverage = self.settings.leverage
        
        self.signal_interval = self.settings.signal_interval
        self.api_interval = self.settings.api_interval
        
        self.autoTrade = self.settings.autoTrade
              
        #Ticker object
        self.tickerObjects = Tickers(self.settings)
        
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
        self.bitunixPrivateWebSocketClient = BitunixPrivateWebSocketClient(self.api_key, self.secret_key)
        if self.settings.use_public_websocket:
            self.bitunixPublicDepthWebSocketClient = BitunixPublicWebSocketClient(self.api_key, self.secret_key, "depth")
            self.bitunixPublicTickerWebSocketClient = BitunixPublicWebSocketClient(self.api_key, self.secret_key, "ticker")
            self.bitunixPublicKlineWebSocketClient = BitunixPublicWebSocketClient(self.api_key, self.secret_key, "kline")

        self.tickerList=[]

        self.green="#A5DFDF"
        self.red="#FFB1C1"
        
        self.profit=0
        
        self.bars = settings.bars
        self.check_ema = settings.check_ema
        self.check_macd = settings.check_macd
        self.check_bbm = settings.check_bbm
        self.check_rsi = settings.check_rsi
        
        self.lastAutoTradeTime = time.time()
        
      
    async def load_tickers(self):
        symbols = await self.bitunixApi.GetTickerList(self.threshold, self.minVolume)
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
        #self.tickerList=['SOLUSDT']

        [await self.add_ticker_to_tickerObjects(sym) for sym in self.tickerList]
        self.notifications.add_notification(f"{len(self.tickerList)} ticker list loaded") 
        
    async def add_ticker_to_tickerObjects(self, symbol):
        if not self.tickerObjects.get(symbol):
            self.tickerObjects.add(symbol)
            
    async def start_jobs(self):
        #async thread that runs forever jobs
        self.GetportfolioDataTask = AsyncThreadRunner(self.GetportfolioData, interval=self.api_interval)
        self.GetportfolioDataTask.start_thread(thread_name="GetportfolioData")

        self.GetPendingPositionDataTask = AsyncThreadRunner(self.GetPendingPositionData, interval=self.api_interval)
        self.GetPendingPositionDataTask.start_thread(thread_name="GetPendingPositionData")

        self.GetPendingOrderDataTask = AsyncThreadRunner(self.GetPendingOrderData, interval=self.api_interval)
        self.GetPendingOrderDataTask.start_thread(thread_name="GetPendingOrderData")

        self.GetTradeHistoryDataTask = AsyncThreadRunner(self.GetTradeHistoryData, interval=self.api_interval)
        self.GetTradeHistoryDataTask.start_thread(thread_name="GetTradeHistoryData")
       
        self.GetPositionHistoryDataTask = AsyncThreadRunner(self.GetPositionHistoryData, interval=self.api_interval)
        self.GetPositionHistoryDataTask.start_thread(thread_name="GetPositionHistoryData")
       
        #run restartable asynch thread
        await self.restartable_jobs()

    async def restart_jobs(self):

        #stop websocket async thread jobs
        await self.bitunixPrivateWebSocketClient.stop_websocket()
        await self.ProcessPrivateDataTask.stop_thread()
        
        if self.settings.use_public_websocket:
            await self.bitunixPublicDepthWebSocketClient.stop_websocket()
            await self.UpdateDepthDataTask.stop_thread()
            
            await self.bitunixPublicTickerWebSocketClient.stop_websocket()
            await self.UpdateTickerDataTask.stop_thread()

            await self.bitunixPublicKlineWebSocketClient.stop_websocket()
            await self.UpdateKlineDataTask.stop_thread()

            #kill the loop to restart public websocket
            #not using for now
            #await self.restartPublicWebsocketTask.stop_thread()

        #stop onetime / periodic async thread jobs
        await self.LoadKlineHistoryTask.stop_thread()
        await self.GetCandleDataTask.stop_thread()
        await self.BuySellListTask.stop_thread()
        await self.AutoTradeProcessTask.stop_thread()   

        #start jobs
        await self.load_tickers()
        await self.restartable_jobs()

    async def restartable_jobs(self):
        #start cancelable async jobs
        #websocket jobs
        self.ProcessPrivateDataTask = AsyncThreadRunner(self.bitunixPrivateWebSocketClient.run_websocket, 0, self.ProcessPrivateData)
        self.ProcessPrivateDataTask.start_thread(thread_name="ProcessPrivateData")

        if self.settings.use_public_websocket:

            self.bitunixPublicDepthWebSocketClient.tickerList = self.tickerList
            self.UpdateDepthDataTask = AsyncThreadRunner(self.bitunixPublicDepthWebSocketClient.run_websocket, 0, self.UpdateDepthData)
            self.UpdateDepthDataTask.start_thread(thread_name="UpdateDepthData")

            self.bitunixPublicTickerWebSocketClient.tickerList = self.tickerList
            self.UpdateTickerDataTask = AsyncThreadRunner(self.bitunixPublicTickerWebSocketClient.run_websocket, 0, self.UpdateTickerData)
            self.UpdateTickerDataTask.start_thread(thread_name="UpdateTickerData")

            self.bitunixPublicKlineWebSocketClient.tickerList = self.tickerList
            self.UpdateKlineDataTask = AsyncThreadRunner(self.bitunixPublicKlineWebSocketClient.run_websocket, 0, self.UpdateKlineData)
            self.UpdateKlineDataTask.start_thread(thread_name="UpdateKlineData")

        #normal processes
        self.LoadKlineHistoryTask = AsyncThreadRunner(self.LoadKlineHistory, interval=0)
        self.LoadKlineHistoryTask.start_thread(thread_name="LoadKlineHistory")

        self.GetCandleDataTask = AsyncThreadRunner(self.GetCandleData, interval=self.api_interval)
        self.GetCandleDataTask.start_thread(thread_name="GetCandleData")

        self.BuySellListTask = AsyncThreadRunner(self.BuySellList, interval=self.signal_interval)
        self.BuySellListTask.start_thread(thread_name="BuySellList")

        self.AutoTradeProcessTask = AsyncThreadRunner(self.AutoTradeProcess, interval=self.signal_interval)
        self.AutoTradeProcessTask.start_thread(thread_name="AutoTradeProcess")

        #start the loop to restart public websocket
        #if self.settings.use_public_websocket:
        #    self.restartPublicWebsocketTask = AsyncThreadRunner(self.restartPublicWebsocket, interval=0)
        #    self.restartPublicWebsocketTask.start_thread(thread_name="restartPublicWebsocket")

    #this is a normal task runing in a async thread, that can be cancelled
    # this runs in a async thread to stop and start the public websocket, as we found some lagging when it runs continously
    #not used now
    async def restartPublicWebsocket(self): 
        while True:
            await asyncio.sleep(self.settings.public_websocket_restart_interval)
            
            if self.verbose_logging:
                self.notifications.add_notification('Restarting public websocket')
                logger.info(f"Restarting public websocket")
            
            if self.settings.use_public_websocket:
                await self.UpdateDepthDataTask.stop_thread()
                await self.UpdateTickerDataTask.stop_thread() 
                await self.UpdateKlineDataTask.stop_thread() 
            
            await asyncio.sleep(30)

            if self.settings.use_public_websocket:
                self.bitunixPublicDepthWebSocketClient.tickerList = self.tickerList
                self.UpdateDepthDataTask = AsyncThreadRunner(self.bitunixPublicDepthWebSocketClient.run_websocket, 0, self.UpdateDepthData)
                self.UpdateDepthDataTask.start_thread(thread_name="UpdateDepthData")

                self.bitunixPublicTickerWebSocketClient.tickerList = self.tickerList
                self.UpdateTickerDataTask = AsyncThreadRunner(self.bitunixPublicTickerWebSocketClient.run_websocket, 0, self.UpdateTickerData)
                self.UpdateTickerDataTask.start_thread(thread_name="UpdateTickerData")

                self.bitunixPublicKlineWebSocketClient.tickerList = self.tickerList
                self.UpdateKlineDataTask = AsyncThreadRunner(self.bitunixPublicKlineWebSocketClient.run_websocket, 0, self.UpdateKlineData)
                self.UpdateKlineDataTask.start_thread(thread_name="UpdateKlineData")

            if self.verbose_logging:
                self.notifications.add_notification('Restared public websocket')

    ###########################################################################################################
    async def LoadKlineHistory(self):
        intervals = ["1m", "5m", "15m", "1h", "1d"]
        for ticker in self.tickerList:
            start = time.time()
            for intervalId in intervals:
                await self.kline_history(ticker, intervalId, self.bars)
                await asyncio.sleep(0)
            if self.verbose_logging:
                logger.info(f"kline_history for a interval: elapsed time {ticker} {time.time()-start}")
        self.notifications.add_notification("Kline history loaded")

    async def kline_history(self, ticker, intervalId, bars):
        try:
            data = await self.bitunixApi.GetKlineHistory(ticker, intervalId, bars)
            await self.processklinehistory(ticker, intervalId, bars, data)
            del data
            gc.collect()
        except Exception as e:
            logger.info(f"Function: kline_history, {e}, {e.args}, {type(e).__name__}")

    async def processklinehistory(self, symbol, intervalId, bars, data=None):
        if data:
            tickerObj=self.tickerObjects.get(symbol)
            if tickerObj:
                intervalObj = tickerObj.get_interval_ticks(intervalId)
                ticks_interval=[]

                for item in data:
                    item["barcolor"] = self.green if item['open'] <= item['close'] else self.red
                    item.update({
                            'open': float(item['open']),
                            'high': float(item['high']),
                            'low': float(item['low']),
                            'close': float(item['close']),
                            'last': 0,
                            'quoteVol': float(item['quoteVol']),
                            'baseVol': float(item['baseVol']),
                            'time': int(item["time"])
                        })
                    ticks_interval.append(item)

                empty_item = {
                        "barcolor": "",
                        'open': 0.0,
                        'high': 0.0,
                        'low': 0.0,
                        'close': 0.0,
                        'last': 0,
                        'quoteVol': 0.0,
                        'baseVol': 0.0,
                        'time': 0
                    }
                ticks_interval.extend([empty_item] * (bars - len(ticks_interval)))

                # Reverse the list of dictionaries in ascending
                ticks_interval = ticks_interval[::-1]
                
                loop = asyncio.get_event_loop()     
                loop.run_in_executor(None, intervalObj.set_data, ticks_interval)
                del ticks_interval, empty_item, intervalObj, tickerObj, loop
                gc.collect()
        del data
        gc.collect()
            
    async def GetCandleData(self):
        start=time.time()
        current_time = int(time.time() * 1000)
        next_minute = (current_time // 1000 + 1) * 1000
        sleep_duration = (next_minute - current_time) / 1000
        await asyncio.sleep(sleep_duration)
        ts = next_minute
        #api used insted of websocket
        #if self.settings.use_public_websocket:
        #    await self.apply_last_data_to_form_candle(ts)
        #else:
        data = await self.bitunixApi.GetTickerData()
        tickerdf = pd.DataFrame()
        if data:
            tickerdf = pd.DataFrame(data, columns=["symbol", "markPrice", "lastPrice", "open", "last", "quoteVol", "baseVol", "high", "low"])
            
            #remove not required symbols
            tickerdf.loc[~tickerdf['symbol'].isin(self.tickerObjects.symbols()), :] = None
            tickerdf.dropna(inplace=True)
            
            tickerdf['ts']=ts
            await self.process_candle_data(tickerdf)
            if self.verbose_logging:
                logger.info(f"GetTickerData: elapsed time {time.time()-start}")
        del tickerdf, data, sleep_duration, next_minute, current_time
        gc.collect()
    
    async def process_candle_data(self, tickerdf=None):
        tasks = []
        for _, row in tickerdf.iterrows():
            symbol = row['symbol']
            last = float(row['lastPrice'])
            ts=row['ts']
            tasks.append(self.apply_candle_data(symbol, last, ts))
            await asyncio.sleep(0)            
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            # Cancel all pending tasks in case of an exception
            for task in tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            logger.info(f"process_candle_data: Error occurred: {e}")
        del tasks, tickerdf
        gc.collect()  

    async def apply_candle_data(self, symbol, last, ts):
        tickerObj=self.tickerObjects.get(symbol)
        if tickerObj:
            tickerObj.form_candle(last, ts)
        del tickerObj
        gc.collect()  

    async def apply_last_data_to_form_candle(self, ts):
        tasks = []
        for tickerObjDict in self.tickerObjects._tickerObjects: 
            for symbol, tickerObj in tickerObjDict.items():
                last = tickerObj.get_last()
                tasks.append(self.apply_candle_data(symbol, last, ts))
                await asyncio.sleep(0)     
        await asyncio.gather(*tasks) 
        del tasks
        gc.collect()  

    async def UpdateDepthData(self, message):
        if message=="":
            return
        try:
            data = json.loads(message)
            if 'symbol' in data and data['ch'] in ['depth_book1']:
                symbol = data['symbol']
                ts = data['ts']
                bid = float(data['data']['b'][0][0])
                ask = float(data['data']['a'][0][0])
                tickerObj = self.tickerObjects.get(symbol)
                if tickerObj:
                    tickerObj.set_bid(bid)
                    tickerObj.set_ask(ask)
                del tickerObj
                gc.collect()
            del data
            gc.collect()    
        except Exception as e:
            logger.info(f"Function: UpdateDepthData, {e}, {e.args}, {type(e).__name__}")
        if self.verbose_logging:
            logger.info(f"Function: UpdateDepthData, time:{ts}, symbol:{symbol}, bid:{bid}, ask:{ask}")

    async def UpdateTickerData(self, message):
        if message=="":
            return
        try:
            data = json.loads(message)
            if 'symbol' in data and data['ch'] in ['ticker']:
                symbol = data['symbol']
                ts = data['ts']
                highest= float(data['data']['h'])
                lowest= float(data['data']['l'])
                volume= float(data['data']['b'])
                volumeInCurrency= float(data['data']['q'])
                tickerObj = self.tickerObjects.get(symbol)
                if tickerObj:
                    tickerObj.set_24hrData(highest,lowest,volume,volumeInCurrency)
                del tickerObj
                gc.collect()
            del data  
            gc.collect()
        except Exception as e:
            logger.info(f"Function: UpdateTickerData, {e}, {e.args}, {type(e).__name__}")
        if self.verbose_logging:
            logger.info(f"Function: UpdateTickerData, time:{ts}, symbol:{symbol}, highest:{highest}, lowest:{lowest}, volume:{volume}, volumeInCurrency:{volumeInCurrency}")

    async def UpdateKlineData(self, message):
        if message=="":
            return
        try:
            data = json.loads(message)
            if 'symbol' in data and data['ch'] in ['market_kline_1min']:
                symbol = data['symbol']
                ts = data['ts']
                last = float(data['data']['c'])
                tickerObj = self.tickerObjects.get(symbol)
                if tickerObj:
                    tickerObj.set_last(last)
            del data
            gc.collect()
        except Exception as e:
            logger.info(f"Function: UpdateKlineData, {e}, {e.args}, {type(e).__name__}")
        if self.verbose_logging:
            logger.info(f"Function: UpdateKlineData, time:{ts}, symbol:{symbol}, last:{last}")

    async def GetportfolioData(self):
        start=time.time()
        try:
            self.portfolioData = await self.bitunixApi.GetportfolioData()
            if self.portfolioData:
                self.portfoliodf=pd.DataFrame(self.portfolioData,index=[0])[["marginCoin","available","margin","crossUnrealizedPNL"]]
        except Exception as e:
            logger.info(f"Function: GetportfolioData, {e}, {e.args}, {type(e).__name__}")
        if self.verbose_logging:
            logger.info(f"GetportfolioData: elapsed time {time.time()-start}")
                
    async def GetPendingPositionData(self):
        start=time.time()
        try:
            self.pendingPositions = await self.bitunixApi.GetPendingPositionData()
            if self.pendingPositions:
                self.positiondf = pd.DataFrame(self.pendingPositions, columns=["positionId", "symbol", "side", "unrealizedPNL", "realizedPNL",  "qty", "ctime", "avgOpenPrice"])
                 
                if not self.settings.use_public_websocket:                    
                    #get bid las ask using api for the symbols in pending psotion
                    await asyncio.create_task(self.apply_last_data(','.join(self.positiondf['symbol'].astype(str).tolist())))    
                    tasks = [
                        asyncio.create_task(self.apply_depth_data(row))
                        for _, row in self.positiondf.iterrows()
                    ]                
                    await asyncio.gather(*tasks)                
                    del tasks
                    gc.collect()
                    
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
                self.positiondf['bitunix'] = self.positiondf.apply(self.add_bitunix_button, axis=1)
                self.positiondf['action'] = self.positiondf.apply(self.add_close_button, axis=1)
                self.positiondf['add'] = self.positiondf.apply(self.add_add_button, axis=1)
                self.positiondf['reduce'] = self.positiondf.apply(self.add_reduce_button, axis=1)

                self.positiondf['bid'] = self.positiondf['bid'].astype('float64')
                self.positiondf['last'] = self.positiondf['last'].astype('float64')
                self.positiondf['ask'] = self.positiondf['ask'].astype('float64')
            else:
                self.positiondf = pd.DataFrame()

        except Exception as e:
            logger.info(f"Function: GetPendingPositionData, {e}, {e.args}, {type(e).__name__}")
        if self.verbose_logging:
            logger.info(f"GetPendingPositionData: elapsed time {time.time()-start}")

    async def GetPendingOrderData(self):
        start=time.time()
        try:
            self.pendingOrders = await self.bitunixApi.GetPendingOrderData()
            if self.pendingOrders and 'orderList' in self.pendingOrders:
                self.orderdf = pd.DataFrame(self.pendingOrders['orderList'], columns=["orderId", "symbol", "qty", "side", "price", "ctime", "status", "reduceOnly"])
                self.orderdf['rtime']=pd.to_datetime(self.orderdf['ctime'].astype(float), unit='ms').dt.tz_localize('UTC').dt.tz_convert(cst).dt.strftime('%Y-%m-%d %H:%M:%S')
                self.orderdf['bitunix'] = self.orderdf.apply(self.add_bitunix_button, axis=1)
                self.orderdf['action'] = self.orderdf.apply(self.add_order_close_button, axis=1)
            else:
                self.orderdf = pd.DataFrame()
        except Exception as e:
            logger.info(f"Function: GetPendingOrderData, {e}, {e.args}, {type(e).__name__}")
        if self.verbose_logging:
            logger.info(f"GetPendingOrderData: elapsed time {time.time()-start}")

    async def GetTradeHistoryData(self):
        start=time.time()
        try:
            self.tradeHistoryData = await self.bitunixApi.GetTradeHistoryData()
            if self.tradeHistoryData and 'tradeList' in self.tradeHistoryData:
                self.tradesdf = pd.DataFrame(self.tradeHistoryData['tradeList'], columns=["symbol", "ctime", "qty", "side", "price","realizedPNL","reduceOnly"])
                self.tradesdf['ctime'] = pd.to_datetime(self.tradesdf['ctime'].astype(float), unit='ms').dt.tz_localize('UTC').dt.tz_convert(cst).dt.strftime('%Y-%m-%d %H:%M:%S')
                df=self.tickerObjects.symbols().copy()
                for symbol in df:
                    thdf = self.tradesdf[self.tradesdf['symbol'] == symbol]
                    if not thdf.empty:
                        self.tickerObjects.setTrades(symbol,thdf.to_dict(orient='records'))
                    await asyncio.sleep(0)                                
            del df, thdf
            gc.collect()
        except Exception as e:
            logger.info(f"Function: GetTradeHistoryData, {e}, {e.args}, {type(e).__name__}")
        if self.verbose_logging:
            logger.info(f"GetTradeHistoryData: elapsed time {time.time()-start}")

    async def GetPositionHistoryData(self):
        start=time.time()
        try:
            self.positionHistoryData = await self.bitunixApi.GetPositionHistoryData()
            if self.positionHistoryData and 'positionList' in self.positionHistoryData:
                self.positionHistorydf = pd.DataFrame(self.positionHistoryData['positionList'], columns=["symbol", "side","realizedPNL", "ctime", "maxQty", "closePrice","fee", "funding"])
                self.positionHistorydf['ctime'] = pd.to_datetime(self.positionHistorydf['ctime'].astype(float), unit='ms').dt.tz_localize('UTC').dt.tz_convert(cst).dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            logger.info(f"Function: GetPositionHistoryData, {e}, {e.args}, {type(e).__name__}")
        if self.verbose_logging:
            logger.info(f"GetPositionHistoryData: elapsed time {time.time()-start}")


    async def apply_last_data(self, symbols):
        try:
            tdata= await self.bitunixApi.GetTickerslastPrice(symbols)
            _ = [
                (tickerObj.set_bidlastask(float(item['lastPrice']),float(item['lastPrice']),float(item['lastPrice'])))
                for item in tdata
                if (tickerObj := self.tickerObjects.get(item['symbol'])) is not None
            ]
        except Exception as e:
            logger.info(e)
        del _, tdata
        gc.collect()
        
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
                
    async def BuySellList(self):
        start=time.time()
        period = self.option_moving_average
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
            self.tickerObjects.getCurrentData(period)
            self.signaldf_full = self.tickerObjects.signaldf_full
            self.signaldf_filtered = self.tickerObjects.signaldf_filtered

            if not self.positiondf.empty and not self.signaldf_full.empty:
                columns=['symbol', f"{period}_trend", f"{period}_cb", f"{period}_barcolor", f"{period}_ema", f"{period}_macd", f"{period}_bbm", f"{period}_rsi", f"{period}_close_proximity", f"{period}_open", f"{period}_close", f"{period}_high", f"{period}_low"]
                columns2=["qty", "side", "unrealizedPNL", "realizedPNL", "ctime", "avgOpenPrice", "bid", "bidcolor", "last", "lastcolor", "ask", "askcolor", "bitunix", "action", "add", "reduce"]
                if set(columns).issubset(self.signaldf_full.columns) and set(columns2).issubset(self.positiondf.columns):
                    columnOrder= ['symbol', "side", "unrealizedPNL", "realizedPNL", f"{period}_trend", f"{period}_cb", f"{period}_barcolor", f"{period}_ema", f"{period}_macd", f"{period}_bbm", f"{period}_rsi", f"{period}_close_proximity", f"{period}_open", f"{period}_close", f"{period}_high", f"{period}_low", "qty", "ctime", "avgOpenPrice", "bid", "bidcolor", "last", "lastcolor", "ask", "askcolor", "bitunix", "action", "add", "reduce"]                
                    self.positiondf2 = pd.merge(self.positiondf, self.signaldf_full[["symbol", f"{period}_open", f"{period}_close", f"{period}_high", f"{period}_low", 
                            f"{period}_ema", f"{period}_macd", f"{period}_bbm", f"{period}_rsi", f"{period}_close_proximity",
                            f"{period}_trend",f"{period}_cb", f"{period}_barcolor"]], left_on="symbol", right_index=True, how="left")[columnOrder]    
            else:
                self.positiondf2 = pd.DataFrame()
            
            if not self.signaldf_filtered.empty:
                #remove those that are in positon and orders
                self.signaldf_filtered = self.signaldf_filtered[~(self.signaldf_filtered['symbol'].isin(inuseTickers))]

                if not self.signaldf_filtered.empty:
                    # Assign to self.signaldf for HTML rendering
                    self.signaldf = self.signaldf_filtered[[
                        "symbol", f"{period}_trend",f"{period}_cb", f"{period}_barcolor",
                        f"{period}_ema", f"{period}_macd", f"{period}_bbm", f"{period}_rsi",f"{period}_close_proximity",
                        'lastcolor', 'bidcolor', 'askcolor', 'bid', 'ask', 'last',
                        f"{period}_open", f"{period}_close", f"{period}_high", f"{period}_low", 
                    ]].sort_values(by=[f'{period}_cb'], ascending=[False])

                    # Add buttons
                    self.signaldf['bitunix'] = self.signaldf.apply(self.add_bitunix_button, axis=1)
                    self.signaldf['buy'] = self.signaldf.apply(self.add_buy_button, axis=1)
                    self.signaldf['sell'] = self.signaldf.apply(self.add_sell_button, axis=1)

                    if not self.settings.use_public_websocket:                    
                        #get bid las ask using api for max_auto_trades rows
                        m = min(self.signaldf.shape[0], int(self.max_auto_trades))
                        await asyncio.create_task(self.apply_last_data(','.join(self.signaldf['symbol'][:m].astype(str).tolist())))    
                        tasks = [
                            asyncio.create_task(self.apply_depth_data(row))
                            for _, row in self.signaldf[:m].iterrows()
                        ]
                        await asyncio.gather(*tasks)                
                else:
                    self.signaldf = pd.DataFrame()

        except Exception as e:
            logger.info(f"Function: BuySellList, {e}, {e.args}, {type(e).__name__}")
            logger.info(traceback.print_exc())
        if self.verbose_logging:
            logger.info(f"BuySellList: elapsed time {time.time()-start}")
        del inuse1, inuse2, inuseTickers
        gc.collect()

    async def AutoTradeProcess(self):
        if self.verbose_logging:
            logger.info(f"AutoTradeProcess started")
        start=time.time()
        period = self.option_moving_average
        try:
            if not self.autoTrade:
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

            if count < int(self.max_auto_trades):
                if not self.signaldf.empty:
                    #open position upto a max of max_auto_trades from the signal list
                    df=self.signaldf.copy(deep=False)
                    for index, row in df.iterrows():
                        side = "BUY" if row[f'{period}_barcolor'] == self.green else "SELL" if row[f'{period}_barcolor'] == self.red else ""

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
                                qty = str(max(balance * 0.01 / price * int(self.leverage),mtv))

                                datajs = await self.bitunixApi.PlaceOrder(row.symbol, qty, price, side)
                                if datajs["code"] == 0:
                                    self.notifications.add_notification(
                                        f'{colors.YELLOW} Auto open {side} submitted for {row.symbol} with {qty} qty @ {price}, ({datajs["code"]} {datajs["msg"]})'
                                    )
                                count=count+1
                        if count >= int(self.max_auto_trades):
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
                    datajs = await self.bitunixApi.CancelOrder(row.symbol, row.orderId)
                    if datajs["code"] == 0:
                        self.notifications.add_notification(
                            f'{colors.BLUE}Auto canceled order {row.orderId}, {row.symbol} {row.qty} created at {row.rtime} ({datajs["code"]} {datajs["msg"]})'
                        )
                await asyncio.sleep(0)

            if not self.positiondf.empty:
                df=self.positiondf.copy(deep=False)
                for index, row in df.iterrows():
                    unrealized_pnl = float(row.unrealizedPNL)
                    realized_pnl = float(row.realizedPNL)
                    total_pnl = unrealized_pnl + realized_pnl


                    requiredCols=[f'{period}_open', f'{period}_close', f'{period}_high', f'{period}_low', f'{period}_ema', f'{period}_macd', f'{period}_bbm', f'{period}_rsi', f'{period}_close_proximity', f'{period}_trend', f'{period}_cb', f'{period}_barcolor']    
                    required_cols = set(requiredCols)

                    # Close position that fall the below criteria
                    if not self.signaldf_full.columns.empty and self.signaldf_full['symbol'].isin([row.symbol]).any() and required_cols.issubset(set(self.signaldf_full.columns)):
                        
                        # Check orders
                        select = True
                        self.pendingOrders = await self.bitunixApi.GetPendingOrderData({'symbol': row.symbol})
                        if self.pendingOrders and len(self.pendingOrders['orderList']) == 1:
                            select = False
                            
                        if select and int(self.max_auto_trades)!=0:
                        
                            # candle reversed
                            if row.side == 'BUY' and self.signaldf_full.at[row.symbol, f'{period}_barcolor'] == self.red and self.signaldf_full.at[row.symbol, f'{period}_close_proximity'] == "xLOW":
                                last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                price = (ask if row['side'] == "BUY" else bid if row['side'] == "SELL" else last) if bid<=last<=ask else last

                                datajs = await self.bitunixApi.PlaceOrder(
                                    positionId=row.positionId,
                                    ticker=row.symbol,
                                    qty=row.qty,
                                    price=price,
                                    side=row.side,
                                    tradeSide="CLOSE"
                                )
                                if datajs["code"] == 0:
                                    self.notifications.add_notification(
                                        f'{colors.CYAN}Auto close submitted due to bearish candle reversal for {row.symbol} with {row.qty} qty @ {price}, {datajs["msg"]})'
                                    )
                                continue

                            if row.side == 'SELL' and self.signaldf_full.at[row.symbol, f'{period}_barcolor'] == self.green  and self.signaldf_full.at[row.symbol, f'{period}_close_proximity'] == "xHIGH":
                                last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                price = (ask if row['side'] == "BUY" else bid if row['side'] == "SELL" else last) if bid<=last<=ask else last

                                datajs = await self.bitunixApi.PlaceOrder(
                                    positionId=row.positionId,
                                    ticker=row.symbol,
                                    qty=row.qty,
                                    price=price,
                                    side=row.side,
                                    tradeSide="CLOSE"
                                )
                                if datajs["code"] == 0:
                                    self.notifications.add_notification(
                                        f'{colors.CYAN}Auto close submitted due to bullish candle reversal for {row.symbol} with {row.qty} qty @ {price}, {datajs["msg"]})'
                                    )
                                continue

                            # check take portit or accept loss
                            if float(self.loss_amount) > 0 and total_pnl < -float(self.loss_amount):
                                last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                price = (ask if row['side'] == "BUY" else bid if row['side'] == "SELL" else last) if bid<=last<=ask else last

                                datajs = await self.bitunixApi.PlaceOrder(
                                    positionId=row.positionId,
                                    ticker=row.symbol,
                                    qty=row.qty,
                                    price=price,
                                    side=row.side,
                                    tradeSide="CLOSE"
                                )
                                if datajs["code"] == 0:
                                    self.notifications.add_notification(
                                        f'{colors.CYAN}Auto close submitted due to stop loss for {row.symbol} with {row.qty} qty @ {price}, {datajs["msg"]})'
                                    )
                                continue

                            if float(self.profit_amount) > 0 and total_pnl > float(self.profit_amount):
                                last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                price = (ask if row['side'] == "BUY" else bid if row['side'] == "SELL" else last) if bid<=last<=ask else last

                                datajs = await self.bitunixApi.PlaceOrder(
                                    positionId=row.positionId,
                                    ticker=row.symbol,
                                    qty=row.qty,
                                    price=price,
                                    side=row.side,
                                    tradeSide="CLOSE"
                                )
                                if datajs["code"] == 0:
                                    self.notifications.add_notification(
                                        f'{colors.CYAN}Auto close submitted due to take profit for {row.symbol} with {row.qty} qty @ {price}, {datajs["msg"]})'
                                    )
                                continue

                            # Moving average comparison between fast and medium
                            if self.check_ema and row.side == 'BUY' and self.signaldf_full.at[row.symbol, f'{period}_ema'] == "SELL":
                                last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                price = (ask if row['side'] == "BUY" else bid if row['side'] == "SELL" else last) if bid<=last<=ask else last

                                datajs = await self.bitunixApi.PlaceOrder(
                                    positionId=row.positionId,
                                    ticker=row.symbol,
                                    qty=row.qty,
                                    price=price,
                                    side=row.side,
                                    tradeSide="CLOSE"
                                )
                                if datajs["code"] == 0:
                                    self.notifications.add_notification(
                                        f'{colors.CYAN}Auto close submitted due to MA {period} crossover for {row.symbol} with {row.qty} qty @ {price}, {datajs["msg"]})'
                                    )
                                continue

                            if self.check_ema and row.side == 'SELL' and self.signaldf_full.at[row.symbol, f'{period}_ema'] == "BUY":
                                last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                price = (ask if row['side'] == "BUY" else bid if row['side'] == "SELL" else last) if bid<=last<=ask else last
                                datajs = await self.bitunixApi.PlaceOrder(
                                    positionId=row.positionId,
                                    ticker=row.symbol,
                                    qty=row.qty,
                                    price=price,
                                    side=row.side,
                                    tradeSide="CLOSE"
                                )
                                if datajs["code"] == 0:
                                    self.notifications.add_notification(
                                        f'{colors.CYAN}Auto close submitted due to MA {period} crossover for {row.symbol} with {row.qty} qty @ {price}, {datajs["msg"]})'
                                    )
                                continue

                            # MACD comparison between MACD and Signal
                            if self.check_macd and row.side == 'BUY' and self.signaldf_full.at[row.symbol, f'{period}_macd'] == "SELL":
                                last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                price = (ask if row['side'] == "BUY" else bid if row['side'] == "SELL" else last) if bid<=last<=ask else last
                                datajs = await self.bitunixApi.PlaceOrder(
                                    positionId=row.positionId,
                                    ticker=row.symbol,
                                    qty=row.qty,
                                    price=price,
                                    side=row.side,
                                    tradeSide="CLOSE"
                                )
                                if datajs["code"] == 0:
                                    self.notifications.add_notification(
                                        f'{colors.CYAN}Auto close submitted due to MACD {period} crossover for {row.symbol} with {row.qty} qty @ {price}, {datajs["msg"]})'
                                    )
                                continue

                            if self.check_macd and row.side == 'SELL'  and self.signaldf_full.at[row.symbol, f'{period}_macd'] == "BUY":
                                last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                price = (ask if row['side'] == "BUY" else bid if row['side'] == "SELL" else last) if bid<=last<=ask else last
                                datajs = await self.bitunixApi.PlaceOrder(
                                    positionId=row.positionId,
                                    ticker=row.symbol,
                                    qty=row.qty,
                                    price=price,
                                    side=row.side,
                                    tradeSide="CLOSE"
                                )
                                if datajs["code"] == 0:
                                    self.notifications.add_notification(
                                        f'{colors.CYAN}Auto close submitted due to MACD {period} crossover for {row.symbol} with {row.qty} qty @ {price}, {datajs["msg"]})'
                                    )
                                continue

                            # Bollinger Band comparison between open and BBM
                            if self.check_bbm and row.side == 'BUY' and self.signaldf_full.at[row.symbol, f'{period}_bbm'] == "SELL":
                                last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                price = (ask if row['side'] == "BUY" else bid if row['side'] == "SELL" else last) if bid<=last<=ask else last
                                datajs = await self.bitunixApi.PlaceOrder(
                                    positionId=row.positionId,
                                    ticker=row.symbol,
                                    qty=row.qty,
                                    price=price,
                                    side=row.side,
                                    tradeSide="CLOSE"
                                )
                                if datajs["code"] == 0:
                                    self.notifications.add_notification(
                                        f'{colors.CYAN}Auto close submitted due to BBM {period} crossover for {row.symbol} with {row.qty} qty @ {price}, {datajs["msg"]})'
                                    )
                                continue

                            if self.check_bbm and row.side == 'SELL' and self.signaldf_full.at[row.symbol, f'{period}_bbm'] == "BUY":
                                last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                price = (ask if row['side'] == "BUY" else bid if row['side'] == "SELL" else last) if bid<=last<=ask else last
                                datajs = await self.bitunixApi.PlaceOrder(
                                    positionId=row.positionId,
                                    ticker=row.symbol,
                                    qty=row.qty,
                                    price=price,
                                    side=row.side,
                                    tradeSide="CLOSE"
                                )
                                if datajs["code"] == 0:
                                    self.notifications.add_notification(
                                        f'{colors.CYAN}Auto close submitted due to BBM {period} crossover for {row.symbol} with {row.qty} qty @ {price}, {datajs["msg"]})'
                                    )
                                continue
                            
                            # RSI comparison
                            if self.check_rsi and row.side == 'BUY' and self.signaldf_full.at[row.symbol, f'{period}_rsi'] == "SELL":
                                last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                price = (ask if row['side'] == "BUY" else bid if row['side'] == "SELL" else last) if bid<=last<=ask else last
                                datajs = await self.bitunixApi.PlaceOrder(
                                    positionId=row.positionId,
                                    ticker=row.symbol,
                                    qty=row.qty,
                                    price=price,
                                    side=row.side,
                                    tradeSide="CLOSE"
                                )
                                if datajs["code"] == 0:
                                    self.notifications.add_notification(
                                        f'{colors.CYAN}Auto close submitted due to RSI {period} crossover for {row.symbol} with {row.qty} qty @ {price}, {datajs["msg"]})'
                                    )
                                continue

                            if self.check_rsi and row.side == 'SELL' and self.signaldf_full.at[row.symbol, f'{period}_rsi'] == "BUY":
                                last, bid, ask, mtv = await self.GetTickerBidLastAsk(row.symbol)
                                price = (ask if row['side'] == "BUY" else bid if row['side'] == "SELL" else last) if bid<=last<=ask else last
                                datajs = await self.bitunixApi.PlaceOrder(
                                    positionId=row.positionId,
                                    ticker=row.symbol,
                                    qty=row.qty,
                                    price=price,
                                    side=row.side,
                                    tradeSide="CLOSE"
                                )
                                if datajs["code"] == 0:
                                    self.notifications.add_notification(
                                        f'{colors.CYAN}Auto close submitted due to RSI {period} crossover for {row.symbol} with {row.qty} qty @ {price}, {datajs["msg"]})'
                                    )
                                continue
                    await asyncio.sleep(0)
            
                self.lastAutoTradeTime = time.time()
        except Exception as e:
            stack = traceback.extract_stack()
            function_name = stack[-1].name
            logger.info(f"Function: {function_name}, {e}, {e.args}, {type(e).__name__}")
            logger.info(traceback.print_exc())
                
        if self.verbose_logging:
            logger.info(f"AutoTradeProcess: elapsed time {time.time()-start}")

        del df
        gc.collect()
            
            
    async def GetTickerBidLastAsk(self, symbol):
        tdata = await self.bitunixApi.GetTickerslastPrice(symbol)
        last=float(tdata[0]['lastPrice'])
        ddata = await self.bitunixApi.GetDepthData(symbol,"1")
        bid = float(ddata['bids'][0][0])
        ask = float(ddata['asks'][0][0])
        pdata = await self.bitunixApi.GetTickersPair(symbol)
        mtv=float(pdata[0]['minTradeVolume'])
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
                # self.notifications.add_notification(
                #     f'{orderStatus} {side} order for {symbol} with {qty} qty (event: {event})'
                # )

            elif channel == 'balance':
                
                self.available = data['available']
                self.margin = data['margin']
                # logger.info(feed)

            elif channel == 'position':
                
                ts = int(feed['ts'])
                symbol = data['symbol']
                qty = float(data['qty'])
                side = data['side']
                positionId = data['positionId']
                event = data['event']
                entryValue = float(data['entryValue'])
                price = entryValue / qty if entryValue != 0 and qty != 0 else 0

                if event == "OPEN":
                    self.notifications.add_notification(
                        f'{colors.PURPLE}{event} {side} position for {symbol} with {qty} qty @ {price}'
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
                            f'{colors.GREEN if profit>0 else colors.RED}{event} {side} position for {symbol} with {qty} qty @ {price} and {"profit" if profit>0 else "loss"} of {profit}'
                        )
                    del datajs
                    gc.collect()
                self.tickerObjects.get(symbol).trades.append({'ctime': ts, 'symbol': symbol, 'qty': qty, 'side': side, 'price': price})
            del feed
            gc.collect()
        except Exception as e:
            logger.info(f"Function: ProcessPrivateData, {e}, {e.args}, {type(e).__name__}")
            
    def color_cells(val, color):
        return f'background-color: {color}' if val else ''

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
 
    
