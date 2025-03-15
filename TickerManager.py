import pandas as pd
pd.set_option('future.no_silent_downcasting', True)
import numpy as np
import asyncio
import pandas_ta as ta
import traceback
from config import Settings
from logger import Logger
logger = Logger(__name__).get_logger()
import gc

class Interval:
    def __init__(self, symbol, intervalId, delta, data, settings : Settings):
        self.symbol = symbol
        self.intervalId = intervalId
        self.delta = delta
        self.settings=settings
        self._data = data
        
        self.current_signal="HOLD"
        self.ema_signal="HOLD"
        self.macd_signal="HOLD"
        self.bbm_signal="HOLD"
        self.rsi_signal="HOLD"
        self.close_proximity="HOLD"
        
        self.signal_strength=0

    def get_data(self):
        return self._data

    def set_data(self, new_value):
        self._data = new_value
        self.calculate_study()
            
    def calculate_study(self):
        df = pd.DataFrame(self._data)
        if not df.empty and df.shape[0] >= self.settings.bars:
            try:
                df['slope']=0.0
                df['angle']=0.0
                
                #consecutive same color candle 
                df['Group'] = (df['barcolor'] != df['barcolor'].shift()).cumsum()
                df['Consecutive'] = df.groupby('Group').cumcount() + 1
                
                # Get the last color and its consecutive count
                self.signal_strength = df['Consecutive'].iloc[-1]

                # Calculate the close proximity                
                df['range'] = df['high'] - df['low']
                df['close_proximity'] = ((df['close'] - df['low'])/df['range'])*100
                if df['close_proximity'].iloc[-1] > 70:
                    self.close_proximity = 'HIGH'
                elif df['close_proximity'].iloc[-1] < 30:
                    self.close_proximity = 'LOW'
                else:
                    self.close_proximity = 'HOLD'      
                df.fillna({'close_proximity':0}, inplace=True)
                df.fillna({'range':0}, inplace=True)

                # Calculate the RSI
                df['rsi_fast'] = ta.rsi(df['close'],length=self.settings.rsi_fast)
                df.fillna({'rsi_fast':0}, inplace=True)
                
                df['rsi_slow'] = ta.rsi(df['close'],length=self.settings.rsi_slow)
                df.fillna({'rsi_slow':0}, inplace=True)
                
                # Calculate the Moving Averages
                df['ma_fast'] = df['close'].ewm(span=self.settings.ma_fast, adjust=False).mean()
                df['ma_fast'] = df['ma_fast'].bfill()
                df.fillna({'ma_fast':0}, inplace=True)

                df['ma_slow'] = df['close'].ewm(span=self.settings.ma_slow, adjust=False).mean()
                df['ma_slow'] = df['ma_slow'].bfill()
                df.fillna({'ma_slow':0}, inplace=True)
                
                df['ma_medium'] = df['close'].ewm(span=self.settings.ma_medium, adjust=False).mean()
                df['ma_medium'] = df['ma_medium'].bfill()
                df.fillna({'ma_medium':0}, inplace=True)

                # Calculate Bollinger Bands  
                df['BBL'] = 0.0
                df['BBM'] = 0.0
                df['BBU'] = 0.0
                df['BBB'] = 0.0
                df['BBP'] = 0.0
                bbands = ta.bbands(df['close'], length=self.settings.bbm_period, std=self.settings.bbm_std)
                if bbands is not None:
                    bbands.rename(columns={f'BBL_{self.settings.bbm_period}_{self.settings.bbm_std}': 'BBL'}, inplace=True)
                    bbands.fillna({'BBL':0}, inplace=True)
                    bbands.rename(columns={f'BBM_{self.settings.bbm_period}_{self.settings.bbm_std}': 'BBM'}, inplace=True)
                    bbands.fillna({'BBM':0}, inplace=True)
                    bbands.rename(columns={f'BBU_{self.settings.bbm_period}_{self.settings.bbm_std}': 'BBU'}, inplace=True)
                    bbands.fillna({'BBU':0}, inplace=True)
                    bbands.rename(columns={f'BBB_{self.settings.bbm_period}_{self.settings.bbm_std}': 'BBB'}, inplace=True)
                    bbands.fillna({'BBB':0}, inplace=True)
                    bbands.rename(columns={f'BBP_{self.settings.bbm_period}_{self.settings.bbm_std}': 'BBP'}, inplace=True)
                    bbands.fillna({'BBP':0}, inplace=True)
                    # Add Bollinger Bands to the DataFrame
                    df['BBL'] = bbands['BBL']
                    df['BBM'] = bbands['BBM']
                    df['BBU'] = bbands['BBU']
                    df['BBB'] = bbands['BBB']
                    df['BBP'] = bbands['BBP']
                    df.fillna({'BBL':0}, inplace=True)
                    df.fillna({'BBM':0}, inplace=True)
                    df.fillna({'BBU':0}, inplace=True)
                    df.fillna({'BBB':0}, inplace=True)
                    df.fillna({'BBP':0}, inplace=True)

                # Calculate the MACD Line
                df['MACD_Line'] = 0.0
                df['MACD_Signal'] = 0.0
                df['MACD_Histogram'] = 0.0
                macd = ta.macd(df['close'], fast=self.settings.macd_short, slow=self.settings.macd_long, signal=self.settings.macd_period)
                if macd is not None:
                    macd.rename(columns={f'MACD_{self.settings.macd_short}_{self.settings.macd_long}_{self.settings.macd_period}': 'MACD_Line'}, inplace=True)
                    macd.rename(columns={f'MACDs_{self.settings.macd_short}_{self.settings.macd_long}_{self.settings.macd_period}': 'MACD_Signal'}, inplace=True)
                    macd.rename(columns={f'MACDh_{self.settings.macd_short}_{self.settings.macd_long}_{self.settings.macd_period}': 'MACD_Histogram'}, inplace=True)
                    df['MACD_Line'] = macd['MACD_Line']
                    df['MACD_Signal'] = macd['MACD_Signal']
                    df['MACD_Histogram'] = macd['MACD_Histogram']
                    df.fillna({'MACD_Line':0}, inplace=True)
                    df.fillna({'MACD_Signal':0}, inplace=True)
                    df.fillna({'MACD_Histogram':0}, inplace=True)
                                
                # Determine the signal based on the cross over
                if self.settings.check_ema:
                    df['slope'] = df['ma_medium'].diff()
                    df['angle'] = np.degrees(np.arctan(df['slope']))    
                    df.fillna({'slope':0}, inplace=True)
                    df.fillna({'angle':0}, inplace=True)                                    
                    if df['close'].iloc[-1] > df['ma_fast'].iloc[-1] and df['ma_fast'].iloc[-1] > df['ma_medium'].iloc[-1]:
                        self.ema_signal = "BUY"
                    elif df['close'].iloc[-1] < df['ma_fast'].iloc[-1] and df['ma_fast'].iloc[-1] < df['ma_medium'].iloc[-1]:
                        self.ema_signal = "SELL"
                    else:
                        self.ema_signal = "HOLD"
                    
                if self.settings.check_macd:
                    df['slope'] = df['MACD_Signal'].diff()
                    df['angle'] = np.degrees(np.arctan(df['slope']))                                        
                    df.fillna({'slope':0}, inplace=True)
                    df.fillna({'angle':0}, inplace=True)                                    
                    if df['MACD_Line'].iloc[-1] > df['MACD_Signal'].iloc[-1]: 
                        self.macd_signal = "BUY"
                    elif df['MACD_Line'].iloc[-1] < df['MACD_Signal'].iloc[-1]:
                        self.macd_signal = "SELL"
                    else:
                        self.macd_signal = "HOLD"

                if self.settings.check_bbm:
                    df['slope'] = df['BBM'].diff()
                    df['angle'] = np.degrees(np.arctan(df['slope']))                                        
                    df.fillna({'slope':0}, inplace=True)
                    df.fillna({'angle':0}, inplace=True)                                    
                    if df['close'].iloc[-1] > df['BBM'].iloc[-1] and df['close'].iloc[-2] > df['BBM'].iloc[-2] and df['slope'].iloc[-1]>0:
                        self.bbm_signal = "BUY"
                    elif df['close'].iloc[-1] < df['BBM'].iloc[-1] and df['close'].iloc[-2] < df['BBM'].iloc[-2] and df['slope'].iloc[-1]<0:
                        self.bbm_signal = "SELL"
                    else:
                        self.bbm_signal = "HOLD"
                
                if self.settings.check_rsi:
                    df['slope'] = df['ma_fast'].diff()
                    df['angle'] = np.degrees(np.arctan(df['slope']))                                        
                    df.fillna({'slope':0}, inplace=True)
                    df.fillna({'angle':0}, inplace=True)                                    
                    if df['rsi_fast'].iloc[-1] > df['rsi_slow'].iloc[-1]:
                        self.rsi_signal = "BUY"
                    elif df['rsi_fast'].iloc[-1] < df['rsi_slow'].iloc[-1]:
                        self.rsi_signal = "SELL"
                    else:
                        self.rsi_signal = "HOLD"

                if self.ema_signal=="BUY" and self.macd_signal=="BUY" and self.bbm_signal=="BUY" and self.rsi_signal=="BUY" and self.close_proximity=="HIGH":
                    self.current_signal="BUY"
                elif self.ema_signal=="SELL" and self.macd_signal=="SELL" and self.bbm_signal=="SELL" and self.rsi_signal=="SELL" and self.rsi_signal=="SELL" and self.close_proximity=="LOW":
                    self.current_signal="SELL"
                else:
                    self.current_signal="HOLD"
                    
                #replace infinity   
                df.replace([np.inf, -np.inf], 0, inplace=True)
                    
                self._data = df.to_dict('records')
                del df, bbands 
                gc.collect()            
            except Exception as e:
                logger.info(f"Function: calculate_macd, {e}, {e.args}, {type(e).__name__}")
                logger.info(traceback.logger.info_exc())
    
class Ticker:
    
    def __init__(self, symbol, settings : Settings):
        self.symbol=symbol
        self.settings=settings
        
        self.settings.bars=self.settings.bars
        
        self._bid = 0.0
        self.bidcolor = ""
        self._last = 0.0
        self.lastcolor = ""
        self._ask = 0.0
        self.askcolor = ""
        self._mtv=0.0
        self.intervals=['1m','5m','15m','1h','1d']
        self._ticks = {
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
        self.ts = ts
        loop = asyncio.get_event_loop()     
        for intervalId in self.intervals:
            loop.run_in_executor(None, self.create_bar_with_last_and_ts, intervalId)        

    def set_bidlastask(self, bid, last, ask):
        self.bidcolor = self.green if bid >= self._bid else self.red
        self._bid = bid
        self.lastcolor = self.green if last >= self._last else self.red
        self._last = last
        self.askcolor = self.green if ask >= self._ask else self.red
        self._ask = ask
        
    def get_ticks(self):
        return self._ticks

    def get_interval_ticks(self, intervalId):
        return self._ticks[intervalId]

    def set_interval_ticks(self, intervalId, new_value):
        self._ticks[intervalId] = new_value

    def create_bar_with_last_and_ts(self, intervalId):
        try:
            current_bar={}
            new_item = {
                'open': self._last,
                'high': self._last,
                'low': self._last,
                'close': self._last,
                'quoteVol': 0.0,
                'baseVol': 0.0,
                'time': self.ts,
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
            ticks_interval=intervalObj.get_data()
            if len(ticks_interval)==0 or self.ts - ticks_interval[-1]['time'] >= intervalObj.delta:
                ticks_interval.append(new_item)
                current_bar = ticks_interval[0]
                if len(ticks_interval) > self.settings.bars:
                    ticks_interval.pop(0)
            else:
                current_bar = ticks_interval[-1]
                current_bar['high'] = max(current_bar['high'], self._last)
                current_bar['low'] = min(current_bar['low'], self._last)
                current_bar['close'] = self._last
                current_bar['barcolor'] = self.red if current_bar['close'] <= current_bar['open'] else self.green

            intervalObj.set_data(ticks_interval)

        except Exception as e:
            logger.info(f"Function: create_bar_with_last_and_ts, {e}, {e.args}, {type(e).__name__}")
            logger.info(traceback.logger.info_exc())

              
class Tickers:
    def __init__(self, settings : Settings):
        self.settings=settings
        
        self.settings.bars = settings.bars
        
        self._tickerObjects=[]
        
        self.green="#A5DFDF" #light green
        self.red="#FFB1C1" #light red
        
        self.signaldf_full = pd.DataFrame()
        self.signaldf_filtered = pd.DataFrame()
        
        self.bidlastask = {}
        
    def add(self, symbol):
        ticker = Ticker(symbol, self.settings)
        self._tickerObjects.append({symbol:ticker})

    def get(self, symbol):
        ret = [d[symbol] for d in self._tickerObjects if symbol in d]
        return ret[0] if ret else None
    
    def get_interval(self, symbol, intervalId):
        ret = [d[symbol] for d in self._tickerObjects if symbol in d]
        tickerObj = ret[0] if ret else None
        if tickerObj:
            return tickerObj.get_interval_ticks(intervalId)
        else:
            return None

    def setTrades(self, symbol, trades):
        ret = [d[symbol] for d in self._tickerObjects if symbol in d]
        if ret:
            ret[0].trades = trades

    def symbols(self):
        symbols = [list(d.keys())[0] for d in self._tickerObjects]
        return symbols
    
    def getCurrentData(self, period):
        current_data = []
        df=pd.DataFrame()
        try:
            for ticker_dict in self._tickerObjects:
                for symbol, tickerObj in ticker_dict.items():
                    bid = tickerObj.get_bid()
                    last = tickerObj.get_last()
                    ask = tickerObj.get_ask()
                    lastcolor = tickerObj.lastcolor
                    bidcolor = tickerObj.bidcolor
                    askcolor = tickerObj.askcolor

                    for intervalId in tickerObj.intervals:
                        if intervalId != period:
                            continue    
                        intervalObj = tickerObj.get_interval_ticks(intervalId)
                        ticks = intervalObj.get_data()
                        if len(ticks)>=self.settings.bars:
                            lastcandle = intervalObj.get_data()[-1]
                            if len(lastcandle) >= 20:
                                new_row = {
                                    'symbol' : symbol,
                                    f"{intervalId}_trend": intervalObj.current_signal,
                                    f"{intervalId}_cb": intervalObj.signal_strength,
                                    f"{intervalId}_barcolor": lastcandle['barcolor'],
                                    f"{intervalId}_ema": intervalObj.ema_signal,
                                    f"{intervalId}_macd":intervalObj.macd_signal,
                                    f"{intervalId}_bbm":intervalObj.bbm_signal,
                                    f"{intervalId}_rsi":intervalObj.rsi_signal,
                                    f"{intervalId}_close_proximity":intervalObj.close_proximity,                                        
                                    'bid' : bid,
                                    'bidcolor' : bidcolor,
                                    'last' : last,
                                    'lastcolor' : lastcolor,
                                    'ask' : ask,
                                    'askcolor' : askcolor,
                                    f"{intervalId}_open": lastcandle['open'],
                                    f"{intervalId}_close": lastcandle['close'],
                                    f"{intervalId}_high": lastcandle['high'],
                                    f"{intervalId}_low": lastcandle['low'],
                                }
                                current_data.append(new_row)
                        
            df = pd.DataFrame(current_data)
            if not df.empty:
                fill_values = {
                    'lastcolor': "", 'bidcolor': "", 'askcolor': "", 'bid': 0.0, 'ask': 0.0, 'last': 0.0,
                    f"{intervalId}_cb":0, f"{intervalId}_barcolor": "", f"{intervalId}_trend": "",
                    f"{intervalId}_open": 0.0, f"{intervalId}_close": 0.0, f"{intervalId}_high": 0.0, f"{intervalId}_low": 0.0,
                    f"{intervalId}_ema": "", f"{intervalId}_macd": "", f"{intervalId}_bbm": "", f"{intervalId}_rsi": "", f"{intervalId}_close_proximity": ""
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