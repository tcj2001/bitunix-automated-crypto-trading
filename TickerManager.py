import pandas as pd
#pd.set_option('future.no_silent_downcasting', True)
import numpy as np
import asyncio
import talib
import traceback
from logger import Logger
logger = Logger(__name__).get_logger()
import gc
from concurrent.futures import ProcessPoolExecutor

class Interval:
    def __init__(self, symbol, intervalId, delta, data, settings):
        self.symbol = symbol
        self.intervalId = intervalId
        self.delta = delta
        self.settings=settings
        self._data = data
        
        #these signals are used to list stocks in the signals sections on the main page
        self.current_signal="HOLD"
        self.ema_signal="HOLD"
        self.macd_signal="HOLD"
        self.bbm_signal="HOLD"
        self.rsi_signal="HOLD"
        self.candle_trend="HOLD"
        self.adx_signal="WEAK"
        
        self.signal_strength=0
        
    def update_settings(self, settings):
        self.settings=settings

    def get_data(self):
        return self._data

    def set_data(self, new_value):
        self._data =  self.calculate_study(new_value)
            
    def calculate_study(self, new_value):
        df = pd.DataFrame(new_value)
        if not df.empty and df.shape[0] >= int(self.settings.BARS):
                        
            try:
                #consecutive same color candle 
                df['Group'] = (df['barcolor'] != df['barcolor'].shift()).cumsum()
                df['Consecutive'] = df.groupby('Group').cumcount() + 1
                
                # Get the last color and its consecutive count
                self.signal_strength = df['Consecutive'].iloc[-1]

                # Calculate the Moving Averages
                if self.settings.EMA_STUDY:
                    df['ma_fast'] = talib.EMA(df['close'], timeperiod=self.settings.MA_FAST)
                    df['ma_fast'] = df['ma_fast'].bfill()
                    df.fillna({'ma_fast':0}, inplace=True)

                    df['ma_slow'] = talib.EMA(df['close'], timeperiod=self.settings.MA_SLOW)
                    df['ma_slow'] = df['ma_slow'].bfill()
                    df.fillna({'ma_slow':0}, inplace=True)
                
                    df['ma_medium'] = talib.EMA(df['close'], timeperiod=self.settings.MA_MEDIUM)
                    df['ma_medium'] = df['ma_medium'].bfill()
                    df.fillna({'ma_medium':0}, inplace=True)

                    df['ma_slope'] = df['ma_medium'].diff()
                    df['ma_angle'] = np.degrees(np.arctan(df['ma_slope']))    
                    df.fillna({'ma_slope':0}, inplace=True)
                    df.fillna({'ma_angle':0}, inplace=True)  
                                                      
                    if self.settings.EMA_CROSSING:
                        if df['ma_fast'].iloc[-2] <= df['ma_medium'].iloc[-2] and df['ma_fast'].iloc[-1] > df['ma_medium'].iloc[-1]:
                            self.ema_signal = "BUY"
                        elif df['ma_fast'].iloc[-2] >= df['ma_medium'].iloc[-2] and df['ma_fast'].iloc[-1] <= df['ma_medium'].iloc[-1]:
                            self.ema_signal = "SELL"
                        else:
                            self.ema_signal = "HOLD"
                    else:
                        if df['close'].iloc[-1] > df['ma_fast'].iloc[-1] and df['ma_fast'].iloc[-1] > df['ma_medium'].iloc[-1]:
                            self.ema_signal = "BUY"
                        elif df['close'].iloc[-1] < df['ma_fast'].iloc[-1] and df['ma_fast'].iloc[-1] < df['ma_medium'].iloc[-1]:
                            self.ema_signal = "SELL"
                        else:
                            self.ema_signal = "HOLD"
                else:
                    # Drop EMA columns if not used
                    df.drop(['ma_fast', 'ma_medium', 'ma_slow', 'ma_slope', 'ma_angle'], axis=1, inplace=True, errors='ignore')

                # Calculate the MACD Line
                if self.settings.MACD_STUDY:
                    df['MACD_Line'] = 0.0
                    df['MACD_Signal'] = 0.0
                    df['MACD_Histogram'] = 0.0
                    df['MACD_Line'], df['MACD_Signal'], df['MACD_Histogram'] = talib.MACD(df['close'], fastperiod=self.settings.MACD_SHORT, slowperiod=self.settings.MACD_LONG, signalperiod=self.settings.MACD_PERIOD)
                    df.fillna({'MACD_Line':0}, inplace=True)
                    df.fillna({'MACD_Signal':0}, inplace=True)
                    df.fillna({'MACD_Histogram':0}, inplace=True)
                            
                    df['MACD_slope'] = df['MACD_Signal'].diff()
                    df['MACD_angle'] = np.degrees(np.arctan(df['MACD_slope']))                                        
                    df.fillna({'MACD_slope':0}, inplace=True)
                    df.fillna({'MACD_angle':0}, inplace=True)                                    
                        
                    if self.settings.MACD_CROSSING:
                        if df['MACD_Line'].iloc[-2] <= df['MACD_Signal'].iloc[-2] and df['MACD_Line'].iloc[-1] > df['MACD_Signal'].iloc[-1]: 
                            self.macd_signal = "BUY"
                        elif df['MACD_Line'].iloc[-2] >= df['MACD_Signal'].iloc[-2] and df['MACD_Line'].iloc[-1] < df['MACD_Signal'].iloc[-1]: 
                            self.macd_signal = "SELL"
                        else:
                            self.macd_signal = "HOLD"
                    else:
                        if df['MACD_Line'].iloc[-1] > df['MACD_Signal'].iloc[-1]: 
                            self.macd_signal = "BUY"
                        elif df['MACD_Line'].iloc[-1] < df['MACD_Signal'].iloc[-1]:
                            self.macd_signal = "SELL"
                        else:
                            self.macd_signal = "HOLD"
                else:
                    # Drop MACD columns if not used
                    df.drop(['MACD_Line', 'MACD_Signal', 'MACD_Histogram', 'MACD_slope', 'MACD_angle'], axis=1, inplace=True, errors='ignore')

                # Calculate Bollinger Bands  
                if self.settings.BBM_STUDY:
                    df['BBL'] = 0.0
                    df['BBM'] = 0.0
                    df['BBU'] = 0.0
                    df['BBU'], df['BBM'], df['BBL'] = talib.BBANDS(df['close'], timeperiod=self.settings.BBM_PERIOD, nbdevup=self.settings.BBM_STD, nbdevdn=self.settings.BBM_STD, )
                    df.fillna({'BBL':0}, inplace=True)
                    df.fillna({'BBM':0}, inplace=True)
                    df.fillna({'BBU':0}, inplace=True)

                    df['BBM_slope'] = df['BBM'].diff()
                    df['BBM_angle'] = np.degrees(np.arctan(df['BBM_slope']))                                        
                    df.fillna({'BBM_slope':0}, inplace=True)
                    df.fillna({'BBM_angle':0}, inplace=True)                                    

                    if self.settings.BBM_CROSSING:
                        if df['close'].iloc[-2] <= df['BBM'].iloc[-2] and df['close'].iloc[-1] > df['BBM'].iloc[-1]:
                            self.bbm_signal = "BUY"
                        elif df['close'].iloc[-2] >= df['BBM'].iloc[-2] and df['close'].iloc[-1] < df['BBM'].iloc[-1]:
                            self.bbm_signal = "SELL"
                        else:
                            self.bbm_signal = "HOLD"
                    else:
                        if df['close'].iloc[-1] > df['BBM'].iloc[-1] and df['close'].iloc[-2] > df['BBM'].iloc[-2]:
                            self.bbm_signal = "BUY"
                        elif df['close'].iloc[-1] < df['BBM'].iloc[-1] and df['close'].iloc[-2] < df['BBM'].iloc[-2]:
                            self.bbm_signal = "SELL"
                        else:
                            self.bbm_signal = "HOLD"
                else:
                    # Drop BBM columns if not used
                    df.drop(['BBL', 'BBM', 'BBU', 'BBM_slope', 'BBM_angle'], axis=1, inplace=True, errors='ignore') 

                # Calculate the RSI
                if self.settings.RSI_STUDY:
                    df['rsi_fast'] = talib.RSI(df['close'],timeperiod=self.settings.RSI_FAST)
                    df.fillna({'rsi_fast':0}, inplace=True)
                    
                    df['rsi_slow'] = talib.RSI(df['close'],timeperiod=self.settings.RSI_SLOW)
                    df.fillna({'rsi_slow':0}, inplace=True)
                
                    df['rsi_slope'] = df['rsi_fast'].diff()
                    df['rsi_angle'] = np.degrees(np.arctan(df['rsi_slope']))                                        
                    df.fillna({'rsi_slope':0}, inplace=True)
                    df.fillna({'rsi_angle':0}, inplace=True)                                    

                    if self.settings.RSI_CROSSING:
                        if df['rsi_fast'].iloc[-2] <= df['rsi_slow'].iloc[-2] and df['rsi_fast'].iloc[-1] > df['rsi_slow'].iloc[-1]:
                            self.rsi_signal = "BUY"
                        elif df['rsi_fast'].iloc[-2] >= df['rsi_slow'].iloc[-2] and df['rsi_fast'].iloc[-1] < df['rsi_slow'].iloc[-1]:
                            self.rsi_signal = "SELL"
                        else:
                            self.rsi_signal = "HOLD"
                    else:
                        if df['rsi_fast'].iloc[-1] > df['rsi_slow'].iloc[-1]:
                            self.rsi_signal = "BUY"
                        elif df['rsi_fast'].iloc[-1] < df['rsi_slow'].iloc[-1]:
                            self.rsi_signal = "SELL"
                        else:
                            self.rsi_signal = "HOLD"
                else:
                    # Drop RSI columns if not used
                    df.drop(['rsi_fast', 'rsi_slow', 'rsi_slope', 'rsi_angle'], axis=1, inplace=True, errors='ignore')  

                # Calculate the ADX
                if self.settings.ADX_STUDY:
                    df['ADX'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=self.settings.ADX_PERIOD)
                    df.fillna({'ADX':0}, inplace=True)
                    if df['ADX'].iloc[-1] > 25:
                        self.adx_signal = "STRONG"
                    else:
                        self.adx_signal = "WEAK"  
                else:
                    # Drop ADX columns if not used
                    df.drop(['ADX'], axis=1, inplace=True, errors='ignore')
                        
                # Calculate the close proximity
                if self.settings.CANDLE_TREND_STUDY:                
                    df['range'] = df['high'] - df['low']
                    df['candle_trend'] = ((df['close'] - df['low'])/df['range'])*100
                    df.fillna({'candle_trend':0}, inplace=True)
                    df.fillna({'range':0}, inplace=True)

                    #open and close criteria
                    if df['candle_trend'].iloc[-1] > 70:
                        self.candle_trend = 'BULLISH'
                    elif df['candle_trend'].iloc[-1] < 30:
                        self.candle_trend = 'BEARISH'
                    else:
                        self.candle_trend = 'HOLD'      
                else:
                    # Drop candle trend columns if not used
                    df.drop(['candle_trend', 'range'], axis=1, inplace=True, errors='ignore')

                    
                #replace infinity   
                df.replace([np.inf, -np.inf], 0, inplace=True)
                
                if self.settings.OPEN_ON_ANY_SIGNAL:
                    # If EMA is enabled and crossing or MACD is enabled and crossing or BBM is enabled and crossing or RSI is enbabled and crossing
                    # and 
                    # ADX is enabled and strong and candle trend is enabled and bullish
                    # then BUY or SELL

                    # Check for BUY signal
                    buy_conditions = (
                        (not self.settings.EMA_STUDY or not self.settings.EMA_CHECK_ON_OPEN or self.ema_signal == "BUY") or
                        (not self.settings.MACD_STUDY or not self.settings.MACD_CHECK_ON_OPEN or self.macd_signal == "BUY") or
                        (not self.settings.BBM_STUDY or not self.settings.BBM_CHECK_ON_OPEN or self.bbm_signal == "BUY") or
                        (not self.settings.RSI_STUDY or not self.settings.RSI_CHECK_ON_OPEN or self.rsi_signal == "BUY")
                    )
                    additional_buy_conditions = (
                        (not self.settings.ADX_STUDY or not self.settings.ADX_CHECK_ON_OPEN or self.adx_signal == "STRONG") and
                        (not self.settings.CANDLE_TREND_STUDY or not self.settings.CANDLE_TREND_CHECK_ON_OPEN or self.candle_trend == "BULLISH")
                    )

                    # Check for SELL signal
                    sell_conditions = (
                        (not self.settings.EMA_STUDY or not self.settings.EMA_CHECK_ON_OPEN or self.ema_signal == "SELL") or
                        (not self.settings.MACD_STUDY or not self.settings.MACD_CHECK_ON_OPEN or self.macd_signal == "SELL") or
                        (not self.settings.BBM_STUDY or not self.settings.BBM_CHECK_ON_OPEN or self.bbm_signal == "SELL") or
                        (not self.settings.RSI_STUDY or not self.settings.RSI_CHECK_ON_OPEN or self.rsi_signal == "SELL")
                    )
                    additional_sell_conditions = (
                        (not self.settings.ADX_STUDY or not self.settings.ADX_CHECK_ON_OPEN or self.adx_signal == "STRONG") and
                        (not self.settings.CANDLE_TREND_STUDY or not self.settings.CANDLE_TREND_CHECK_ON_OPEN or self.candle_trend == "BEARISH")
                    )

                    # Determine current signal
                    if buy_conditions and additional_buy_conditions:
                        self.current_signal = "BUY"
                    elif sell_conditions and additional_sell_conditions:
                        self.current_signal = "SELL"
                    else:
                        self.current_signal = "HOLD"
                else:
                    # If EMA is enabled and crossing and MACD is enabled and crossing and BBM is enabled and crossing and RSI is enbabled and crossing
                    # and 
                    # ADX is enabled and strong and candle trend is enabled and bullish
                    # then BUY or SELL
                    buy_conditions = (
                        (not self.settings.EMA_STUDY or not self.settings.EMA_CHECK_ON_OPEN or self.ema_signal == "BUY") and
                        (not self.settings.MACD_STUDY or not self.settings.MACD_CHECK_ON_OPEN or self.macd_signal == "BUY") and
                        (not self.settings.BBM_STUDY or not self.settings.BBM_CHECK_ON_OPEN or self.bbm_signal == "BUY") and
                        (not self.settings.RSI_STUDY or not self.settings.RSI_CHECK_ON_OPEN or self.rsi_signal == "BUY")
                    )
                    additional_buy_conditions = (
                        (not self.settings.ADX_STUDY or not self.settings.ADX_CHECK_ON_OPEN or self.adx_signal == "STRONG") and
                        (not self.settings.CANDLE_TREND_STUDY or not self.settings.CANDLE_TREND_CHECK_ON_OPEN or self.candle_trend == "BULLISH")
                    )

                    # Check for SELL signal
                    sell_conditions = (
                        (not self.settings.EMA_STUDY or not self.settings.EMA_CHECK_ON_OPEN or self.ema_signal == "SELL") and
                        (not self.settings.MACD_STUDY or not self.settings.MACD_CHECK_ON_OPEN or self.macd_signal == "SELL") and
                        (not self.settings.BBM_STUDY or not self.settings.BBM_CHECK_ON_OPEN or self.bbm_signal == "SELL") and
                        (not self.settings.RSI_STUDY or not self.settings.RSI_CHECK_ON_OPEN or self.rsi_signal == "SELL")
                    )
                    additional_sell_conditions = (
                        (not self.settings.ADX_STUDY or not self.settings.ADX_CHECK_ON_OPEN or self.adx_signal == "STRONG") and
                        (not self.settings.CANDLE_TREND_STUDY or not self.settings.CANDLE_TREND_CHECK_ON_OPEN or self.candle_trend == "BEARISH")
                    )

                    # Determine current signal
                    if buy_conditions and additional_buy_conditions:
                        self.current_signal = "BUY"
                    elif sell_conditions and additional_sell_conditions:
                        self.current_signal = "SELL"
                    else:
                        self.current_signal = "HOLD"
                    
                   
            except Exception as e:
                logger.info(f"Function: calculate_study, {e}, {e.args}, {type(e).__name__}")
                logger.info(traceback.logger.info_exc())
            retval =  df.to_dict('records')
            del df
            gc.collect()            
            return retval
    
class Ticker:
    
    def __init__(self, symbol, intervalIds, settings):
        self.symbol=symbol
        self.settings=settings
        
        self._ts=0
        self._bid = 0.0
        self.bidcolor = ""
        self._last = 0.0
        self.lastcolor = ""
        self._ask = 0.0
        self.askcolor = ""
        self._mtv=0.0
        self.intervalIds=intervalIds
        self._intervals = {
            '1m' : Interval(self.symbol, '1m', 60000,    [], self.settings),
            '5m' : Interval(self.symbol, '5m', 300000,   [], self.settings),
            '15m': Interval(self.symbol, '15m', 900000,  [], self.settings),
            '1h' : Interval(self.symbol, '1h', 3600000,  [], self.settings),
            '1d' : Interval(self.symbol, '1d', 86400000, [], self.settings),
        }
        self.current_data={}
        self.trades = []

        self.green="#A5DFDF"
        self.red="#FFB1C1"
        
    def update_settings(self, settings):
        self.settings=settings
        for intervalId in self.intervalIds:
            self._intervals[intervalId].update_settings(settings)

    def get_bid(self):
        return self._bid

    def set_bid(self, value):
        self.bidcolor = self.green if value >= self._bid else self.red
        self._bid = value
        
    def get_ask(self):
        return self._ask

    def set_ask(self, value):
        self.askcolor = self.green if value >= self._ask else self.red
        self._ask = value
               
    def get_last(self):
        return self._last

    def set_last(self, last):
        self.lastcolor = self.green if last >= self._last else self.red
        self._last = last

    def set_mtv(self, value):
        self._mtv = value
        
    def set_24hrData(self, highest,lowest,volume,volumeInCurrency):
        self.highest = highest
        self.lowest = lowest
        self.volume = volume
        self.volumeInCurrency = volumeInCurrency         
               
    def form_candle(self, last, ts):
        self.lastcolor = self.green if last >= self._last else self.red
        self._last = last
        self._ts = ts
        for intervalId in self.intervalIds:
            self.create_bar_with_last_and_ts( intervalId)
        return (self._last, self.lastcolor, self._ts, self.get_intervals())

    async def set_bidlastask(self, bid, last, ask):
        self.bidcolor = self.green if bid >= self._bid else self.red
        self._bid = bid
        self.lastcolor = self.green if last >= self._last else self.red
        self._last = last
        self.askcolor = self.green if ask >= self._ask else self.red
        self._ask = ask
        
    def get_intervals(self):
        return self._intervals

    def set_intervals(self, intervals):
        self._intervals = intervals

    def get_interval_ticks(self, intervalId):
        return self._intervals.get(intervalId, None)

    def set_interval_ticks(self, intervalId, new_value):
        self._intervals[intervalId] = new_value

    def create_bar_with_last_and_ts(self, intervalId):
        if self._last==0:
            return
        try:
            current_bar={}
            new_item = {
                'open': self._last,
                'high': self._last,
                'low': self._last,
                'close': self._last,
                'quoteVol': 0.0,
                'baseVol': 0.0,
                'time': self._ts,
                'barcolor': "",
                'last':0.0,
                'ma_fast':0.0,
                'ma_slow':0.0,
                'ma_medium':0.0,
                'rsi_fast':0.0,
                'rsi_slow':0.0,
                'MACD_Line':0.0,
                'MACD_Signal':0.0,
                'MACD_Histogram':0.0,
                'BBU':0.0,
                'BBM':0.0,
                'BBL':0.0
            }
            
            intervalObj = self.get_interval_ticks(intervalId)
            if intervalObj is None:
                return
            ticks_interval=intervalObj.get_data()
            if ticks_interval is None:
                return
            if len(ticks_interval)==0 or self._ts - ticks_interval[-1]['time'] >= intervalObj.delta:
                ticks_interval.append(new_item)
                current_bar = ticks_interval[-1]
                if len(ticks_interval) > int(self.settings.BARS):
                    ticks_interval.pop(0)
                #print(f'{self.symbol} {self._last}, {self._ts} {intervalId} {ticks_interval[-1]['time']} n' )
            else:
                current_bar = ticks_interval[-1]
                current_bar['high'] = max(current_bar['high'], self._last)
                current_bar['low'] = min(current_bar['low'], self._last)
                current_bar['close'] = self._last
                current_bar['barcolor'] = self.red if current_bar['close'] <= current_bar['open'] else self.green
                #print(f'{self.symbol} {self._last}, {self._ts} {intervalId} {ticks_interval[-1]['time']} c' )

            intervalObj.set_data(ticks_interval)

        except Exception as e:
            logger.info(f"Function: create_bar_with_last_and_ts, {e}, {e.args}, {type(e).__name__}")
            logger.info(traceback.logger.info_exc())

              
class Tickers:
    def __init__(self, settings):
        self.settings=settings
        
        self._tickerObjects={}
        
        self.green="#A5DFDF" #light green
        self.red="#FFB1C1" #light red
        
        self.signaldf_full = pd.DataFrame()
        self.signaldf_filtered = pd.DataFrame()
        
        self.intervalIds=['1m','5m','15m','1h','1d']
        
    def update_settings(self, settings):
        self.settings=settings
        for symbol in self._tickerObjects:
            self._tickerObjects[symbol].update_settings(settings)        
        
    def add(self, symbol):
        ticker = Ticker(symbol, self.intervalIds, self.settings)
        self._tickerObjects[symbol]=ticker

    def get_tickerDict(self):
        return self._tickerObjects

    def get(self, symbol):
        return self._tickerObjects.get(symbol, None)
    
    def get_intervalIds(self):
        return self.intervalIds

    def get_interval(self, symbol, intervalId):
        tickerObj = self.get(symbol)
        if tickerObj:
            return tickerObj.get_interval_ticks(intervalId)
        else:
            return None

    def setTrades(self, symbol, trades):
        tickerObj = self.get(symbol)
        if tickerObj:
            tickerObj.trades = trades   

    def symbols(self):
        return list(self._tickerObjects.keys())
    
    def load_kline_history(self, symbol, intervalId, bars, data=None):
        tickerObj=self.get(symbol)
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
    
    def process_ticker_candle(self,args):
        ticker_obj, last, ts = args  # Unpack the tuple
        return ticker_obj.form_candle(last, ts)
    
    # this uses cpu to process all ticker study when new lastprice arrives, 
    # since the calulation is done at a different thread and uses a different memory space, 
    # the caluated value has to be reassigned to the original ticker class instance from the caluated ticker instance
    def form_candle(self, tuples_list):
        with ProcessPoolExecutor() as executor:
            results = executor.map(self.process_ticker_candle, tuples_list, chunksize=10)
            for args, result in zip(tuples_list, results):
                for intervalId, interval in result[3].items():
                    if not interval._data is None:
                        args[0].get_interval_ticks(intervalId)._data = interval._data
                        args[0].get_interval_ticks(intervalId).current_signal = interval.current_signal                        
                        args[0].get_interval_ticks(intervalId).ema_signal = interval.ema_signal
                        args[0].get_interval_ticks(intervalId).macd_signal = interval.macd_signal
                        args[0].get_interval_ticks(intervalId).bbm_signal = interval.bbm_signal                        
                        args[0].get_interval_ticks(intervalId).rsi_signal = interval.rsi_signal
                        args[0].get_interval_ticks(intervalId).candle_trend = interval.candle_trend
                        args[0].get_interval_ticks(intervalId).adx_signal = interval.adx_signal
                        args[0].get_interval_ticks(intervalId).signal_strength = interval.signal_strength 
                        args[0]._last = result[0]
                        args[0].lastcolor = result[1]
                        args[0]._ts = result[2]
                                    
    def getCurrentData(self, period):
        current_data = []
        df=pd.DataFrame()
        try:
            for symbol, tickerObj in self._tickerObjects.items():
                bid = tickerObj.get_bid()
                last = tickerObj.get_last()
                ask = tickerObj.get_ask()
                lastcolor = tickerObj.lastcolor
                bidcolor = tickerObj.bidcolor
                askcolor = tickerObj.askcolor

                if period in tickerObj.intervalIds:
                    intervalObj = tickerObj.get_interval_ticks(period)
                    ticks = intervalObj.get_data()
                    if not ticks:
                        continue
                    if len(ticks)>=int(self.settings.BARS):
                        lastcandle = intervalObj.get_data()[-1]
                        if len(lastcandle) >= 20:
                            new_row = {
                                'symbol' : symbol,
                                f"{period}_trend": intervalObj.current_signal,
                                f"{period}_cb": intervalObj.signal_strength,
                                f"{period}_barcolor": lastcandle['barcolor'],
                                f"{period}_ema": intervalObj.ema_signal,
                                f"{period}_macd":intervalObj.macd_signal,
                                f"{period}_bbm":intervalObj.bbm_signal,
                                f"{period}_rsi":intervalObj.rsi_signal,
                                f"{period}_adx":intervalObj.adx_signal,                                       
                                f"{period}_candle_trend":intervalObj.candle_trend, 
                                'bid' : bid,
                                'bidcolor' : bidcolor,
                                'last' : last,
                                'lastcolor' : lastcolor,
                                'ask' : ask,
                                'askcolor' : askcolor,
                                f"{period}_open": lastcandle['open'],
                                f"{period}_close": lastcandle['close'],
                                f"{period}_high": lastcandle['high'],
                                f"{period}_low": lastcandle['low'],
                            }
                            current_data.append(new_row)
                        
            df = pd.DataFrame(current_data)
            if not df.empty:
                fill_values = {
                    'lastcolor': "", 'bidcolor': "", 'askcolor': "", 'bid': 0.0, 'ask': 0.0, 'last': 0.0,
                    f"{period}_cb":0, f"{period}_barcolor": "", f"{period}_trend": "",
                    f"{period}_open": 0.0, f"{period}_close": 0.0, f"{period}_high": 0.0, f"{period}_low": 0.0,
                    f"{period}_ema": "", f"{period}_macd": "", f"{period}_bbm": "", f"{period}_rsi": "", f"{period}_candle_trend": "", f"{period}_adx": ""
                }
                df.fillna(fill_values, inplace=True)
                df.set_index("symbol", inplace=True, drop=False) 
                self.signaldf_full = df.copy().sort_values(by=[f'{period}_cb'], ascending=[False]) 
                #signaldf only contain symbol that has cosecutive colored bar > 1 for buy or sell
                trending_conditions = [
                    (
                        (df[f'{period}_trend']=='BUY') &
                        (df[f'{period}_cb']>1) &
                        (df[f'{period}_barcolor']==self.green) 
                    ),
                    (
                        (df[f'{period}_trend']=='SELL') &
                        (df[f'{period}_cb']>1) &
                        (df[f'{period}_barcolor']==self.red) 
                    )
                ]
                self.signaldf_filtered = df[np.any(trending_conditions, axis=0)].copy()
        except Exception as e:
            logger.info(f"Function: getCurrentData, {e}, {e.args}, {type(e).__name__}")
            logger.info(traceback.logger.info_exc())
        finally:
            del df, current_data
            gc.collect()       