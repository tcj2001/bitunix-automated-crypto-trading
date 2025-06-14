import secrets
import base64
import time
import json
import hashlib
import asyncio 
import re
import requests
from urllib.parse import urlencode
from typing import Dict, Any
import traceback
from logger import Logger
#import ccxt


class BitunixApi:
    
    def __init__(self, api_key, secret_key, settings, logger):
        self.api_key = api_key
        self.secret_key = secret_key
        self.logger = logger
        self.settings = settings
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'BitunixAPI/1.0'
        })
        
        self.pending_positions_URL="https://fapi.bitunix.com/api/v1/futures/position/get_pending_positions"
        self.account_Url="https://fapi.bitunix.com/api/v1/futures/account"
        self.ticker_Url='https://fapi.bitunix.com/api/v1/futures/market/tickers'
        self.ticker_pair_Url='https://fapi.bitunix.com/api/v1/futures/market/trading_pairs'
        self.kline_Url='https://fapi.bitunix.com/api/v1/futures/market/kline'
        self.depth_Url='https://fapi.bitunix.com/api/v1/futures/market/depth'
        self.placeOrder_Url="https://fapi.bitunix.com/api/v1/futures/trade/place_order"
        self.flashClose_Url="https://fapi.bitunix.com/api/v1/futures/trade/flash_close_position"
        self.get_order_url="https://fapi.bitunix.com/api/v1/futures/trade/get_order_detail"
        self.pending_order_url="https://fapi.bitunix.com/api/v1/futures/trade/get_pending_orders"
        self.cancelOrder_Url="https://fapi.bitunix.com/api/v1/futures/trade/cancel_orders"
        self.pending_tpsl_order_url="https://fapi.bitunix.com/api/v1/futures/tpsl/get_pending_orders"
        self.place_tpsl_order_url="https://fapi.bitunix.com/api/v1/futures/tpsl/place_order"
        self.modify_tpsl_order_url="https://fapi.bitunix.com/api/v1/futures/tpsl/modify_order"
        self.cancel_tpsl_Order_Url="https://fapi.bitunix.com/api/v1/futures/tpsl/cancel_order"
        self.Trade_history_Url="https://fapi.bitunix.com/api/v1/futures/trade/get_history_trades"
        self.position_history_Url="https://fapi.bitunix.com/api/v1/futures/position/get_history_positions"
 
    async def update_settings(self, settings):
        self.settings = settings
       
    async def is_near_high_of_day(self, current_value, high_of_day, threshold_percentage=5):
        # Calculate the difference as a percentage of the high of the day
        difference_percentage = ((high_of_day - current_value) / high_of_day) * 100
        # Check if the difference is within the threshold
        return difference_percentage <= threshold_percentage

    async def is_near_low_of_day(self, current_value, low_of_day, threshold_percentage=5):
        # Calculate the difference as a percentage of the low of the day
        difference_percentage = ((current_value - low_of_day) / low_of_day) * 100
        # Check if the difference is within the threshold
        return difference_percentage <= threshold_percentage

    #signature generation related methods
    async def _create_timestamp(self):
        return str(int(time.time()*1000))

    async def _generate_nonce(self) -> str:
        random_bytes = secrets.token_bytes(32)
        return base64.b64encode(random_bytes).decode('utf-8')

    async def _generate_sign_api(self, nonce, timestamp, api_key, secret_key, method, data):
        query_params = ""
        body = ""
        if data:
            if method.lower() == "get":
                data = {k: v for k, v in data.items() if v is not None}
                query_params = '&'.join([f"{k}={v}" for k, v in sorted(data.items())])
                query_params = re.sub(r'[^a-zA-Z0-9]', '', query_params)
            if method.lower() == "post":
                # body = str(data).replace(" ", "")
                body = str(data)

        digest_input = nonce + timestamp + api_key + query_params + body
        # print(f"digest_input={digest_input}")
        digest = hashlib.sha256((digest_input).encode()).hexdigest()
        # print(f"digest={digest}")
        sign_input = digest + secret_key
        # print(f"sign_input={sign_input}")
        sign = hashlib.sha256((sign_input).encode()).hexdigest()

        return sign        
    
    async def _get_authenticated(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        timestamp = await self._create_timestamp()
        nonce = await self._generate_nonce()
        
        signature = await self._generate_sign_api(nonce, timestamp, self.api_key, self.secret_key, "get", params)  
        
        headers = {
            "api-key": self.api_key,  
            "nonce": nonce,
            "timestamp": timestamp,   
            "sign": signature,  # Placeholder for signature   
            "language": "en-US",
            "Content-Type": "application/json"  
        }

        response = self.session.get(endpoint, params=params, headers=headers)
        response.raise_for_status()
        return response.json()

    async def _post_authenticated(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = await self._create_timestamp()
        nonce = await self._generate_nonce()
        
        body_string = json.dumps(data, separators=(',',':'))
        signature = await self._generate_sign_api(nonce, timestamp, self.api_key, self.secret_key, "post", body_string)

        headers = {
            "api-key": self.api_key,
            "timestamp": timestamp,
            "nonce": nonce,
            "sign": signature,
            "Content-Type": "application/json"
        }

        response = self.session.post(endpoint, data=body_string, headers=headers)
        self.logger.info(f"Response: {body_string} {response.json()}")
        response.raise_for_status()
        return response.json()

    async def _get(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
            response = self.session.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()    

    async def PlaceOrder(self, ticker, qty, price, side, positionId=0, tradeSide="OPEN",reduceOnly=False, tpPrice=0, tpOrderPrice=0, slPrice=0, slOrderPrice=0):
        datajs = None
        if tpPrice == 0 and slPrice == 0:
            data = {
                "side": side,
                "orderType":"LIMIT",
                "qty":  qty,
                "price": price,
                "symbol": ticker,
                "tradeSide":tradeSide,
                "reduceOnly":reduceOnly,
                "positionId":positionId
            }
            datajs = await self._post_authenticated(self.placeOrder_Url,data)
        elif tpPrice == 0:
            data = {
                "side": side,
                "orderType":"LIMIT",
                "qty":  qty,
                "price": price,
                "symbol": ticker,
                "tradeSide":tradeSide,
                "slPrice": slPrice,
                "slStopType": self.settings.SL_STOP_TYPE,
                "slOrderType": self.settings.SL_ORDER_TYPE,
                "slOrderPrice": slOrderPrice,
                "positionId":positionId
            }
            datajs = await self._post_authenticated(self.placeOrder_Url,data)
        elif slPrice == 0:
            data = {
                "side": side,
                "orderType":"LIMIT",
                "qty":  qty,
                "price": price,
                "symbol": ticker,
                "tradeSide":tradeSide,
                "tpPrice": tpPrice,
                "tpStopType": self.settings.TP_STOP_TYPE,
                "tpOrderType": self.settings.TP_ORDER_TYPE,
                "tpOrderPrice":tpOrderPrice,
                "positionId":positionId
            }
            datajs = await self._post_authenticated(self.placeOrder_Url,data)
        else:
            data = {
                "side": side,
                "orderType":"LIMIT",
                "qty":  qty,
                "price": price,
                "symbol": ticker,
                "tradeSide":tradeSide,
                "tpPrice": tpPrice,
                "tpStopType": self.settings.TP_STOP_TYPE,
                "tpOrderType": self.settings.TP_ORDER_TYPE,
                "tpOrderPrice":tpOrderPrice,
                "slPrice": slPrice,
                "slStopType": self.settings.SL_STOP_TYPE,
                "slOrderType": self.settings.SL_ORDER_TYPE,
                "slOrderPrice": slOrderPrice,
                "positionId":positionId
            }
            datajs = await self._post_authenticated(self.placeOrder_Url,data)
            
        return datajs

    async def FlashClose(self, positionId):
        data = {
            "positionId": positionId
        }
        datajs = await self._post_authenticated(self.flashClose_Url,data)
        return datajs

    async def CancelOrder(self, symbol, orderId):
        data = {
            "symbol": symbol,
            "orderList":[{"orderId": orderId}]
        }
        datajs = await self._post_authenticated(self.cancelOrder_Url,data)
        return datajs

    async def GetTradeHistoryData(self, dictparm={}):
        tradeHistory=await self._get_authenticated(self.Trade_history_Url, dictparm)
        if tradeHistory['code']==0:
            return tradeHistory['data']
        else:
            self.logger.info(tradeHistory['msg'])

    async def GetOrderData(self, dictparm={}):
        orders=await self._get_authenticated(self.get_order_url, dictparm)
        if orders['code']==0:
            return orders['data']
        else:
            self.logger.info(orders['msg'])

    async def GetPendingOrderData(self,dictparm={}):
        orders=await self._get_authenticated(self.pending_order_url, dictparm)
        if orders['code']==0:
            return orders['data']
        else:
            self.logger.info(orders['msg'])

    async def GetPendingTpSlOrderData(self,dictparm={}):
        orders=await self._get_authenticated(self.pending_tpsl_order_url, dictparm)
        if orders['code']==0:
            return orders['data']
        else:
            self.logger.info(orders['msg'])

    async def PlaceTpSlOrder(self,dictparm={}):
        orders=await self._post_authenticated(self.place_tpsl_order_url, dictparm)
        if orders['code']==0:
            return orders['data']
        else:
            self.logger.info(orders['msg'])

    async def ModifyTpSlOrder(self,dictparm={}):
        orders=await self._post_authenticated(self.modify_tpsl_order_url, dictparm)
        if orders['code']==0:
            return orders['data']
        else:
            self.logger.info(orders['msg'])

    async def CancelTpSlOrder(self, symbol, orderId):
        data = {
            "symbol": symbol,
            "orderId":orderId
        }
        datajs = await self._post_authenticated(self.cancel_tpsl_Order_Url,data)
        return datajs

    async def GetPendingPositionData(self, dictparm={}):
        positions=await self._get_authenticated(self.pending_positions_URL, dictparm)
        if positions['code']==0:
            return positions['data']
        else:
            self.logger.info(positions['msg'])

    async def GetPositionHistoryData(self, dictparm={}):
        tradeHistory=await self._get_authenticated(self.position_history_Url, dictparm)
        if tradeHistory['code']==0:
            return tradeHistory['data']
        else:
            self.logger.info(tradeHistory['msg'])

    
    async def GetportfolioData(self):
        portfolio=await self._get_authenticated(self.account_Url, params={"marginCoin":"USDT"})
        if portfolio['code']==0:
            return portfolio['data']
        else:
            self.logger.info(portfolio['msg'])
           

    async def GetTickerslastPrice(self, tickersStr):
        try:
            resp = self.session.get(self.ticker_Url+'?symbols='+tickersStr)
            datajs = resp.json()
            if datajs['code']==0:
                return datajs['data']
        except Exception as e:
            stack = traceback.extract_stack()
            function_name = stack[-2].name
            self.logger.error(f"Function: {function_name}, {e}, {e.args}, {type(e).__name__}")

    async def GetTickersPair(self, tickersStr):
        try:
            resp = self.session.get(self.ticker_pair_Url+'?symbols='+tickersStr)
            datajs = resp.json()
            if datajs['code']==0:
                return datajs['data']
        except Exception as e:
            stack = traceback.extract_stack()
            function_name = stack[-2].name
            self.logger.error(f"Function: {function_name}, {e}, {e.args}, {type(e).__name__}")

    async def GetTickerList(self, threshold, volume):
        symbols=[]
        try:
            resp = self.session.get(self.ticker_Url)
            datajs = resp.json()
            for item in datajs["data"]: 
                if await self.is_near_high_of_day(float(item['last']), float(item['high']) ,threshold) and float(item['baseVol']) > volume:
                        symbols.append(item['symbol'])
                if await self.is_near_low_of_day(float(item['last']), float(item['low']) ,threshold) and float(item['baseVol']) > volume:
                        symbols.append(item['symbol'])
                #if float(item['baseVol']) > volume:
                #    symbols.append(item['symbol'])
            return symbols
        except Exception as e:
            stack = traceback.extract_stack()
            function_name = stack[-2].name
            self.logger.info(f"Function: {function_name}, {e}, {e.args}, {type(e).__name__}")
            
    async def GetTickerData(self):
        try:
            url = f'{self.ticker_Url}'
            resp = self.session.get(url)
            datajs = resp.json()
            if datajs['code']==0:
                return datajs['data']
        except Exception as e:
            stack = traceback.extract_stack()
            function_name = stack[-2].name
            self.logger.info(f"Function: {function_name}, {e}, {e.args}, {type(e).__name__}")           

    async def GetDepthData(self,symbol,limit):
        try:
            url = f'{self.depth_Url}?symbol={symbol}&limit={limit}'
            resp = self.session.get(url)
            datajs = resp.json()
            if datajs['code']==0:
                return datajs['data']
        except Exception as e:
            stack = traceback.extract_stack()
            function_name = stack[-2].name
            self.logger.info(f"Function: {function_name}, {e}, {e.args}, {type(e).__name__}")           

    async def GetKlineHistory(self, ticker, interval, limit, starttime):
        data = []
        lm=limit
        st=starttime
        try:
            while True:
                url = f'{self.kline_Url}?symbol={ticker}&startTime={st}&interval={interval}&limit={lm}'
                resp = self.session.get(url)
                datajs = resp.json()
                if datajs['data'] == []:
                    break
                data.extend(datajs['data'])
                if len(datajs['data']) < lm:
                    st = int(datajs['data'][-1]['time']) + 1
                    lm=limit-len(data)
                else:
                    break
            return data
        except Exception as e:
            stack = traceback.extract_stack()
            function_name = stack[-2].name
            self.logger.info(f"Function: {function_name}, {e}, {e.args}, {type(e).__name__}") 

    def __del__(self):
            """Cleanup method to close the session"""
            if hasattr(self, 'session'):
                self.session.close()
