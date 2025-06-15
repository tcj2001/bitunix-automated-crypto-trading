# Change Log
## version 3.4.0 ##
Fixed SL moved to breakeven when ROI > SL_BREAKEVEN_PERCENTAGE of PROFIT_PERCENTAGE and LOSS_PERCENTAGE < PROFIT_PERCENTAGE

## version 3.3.9 ##
Added new parms
SL_BREAKEVEN_PERCENTAGE
    Percentage of profit to move the stop loss to breakeven, default is 50%
ALL_TICKERS  
    Will be tickers that are not in LONG_TICKERS and SHORT_TICKERS, this willtrade all other tickers that are not in LONG_TICKERS and SHORT_TICKERS
LONG_TICKERS 
    Will always trade long, even if the signal is SELL
SHORT_TICKERS 
    Will always trade short, even if the signal is BUY
IGNORE_TICKERS 
    will not trade these tickers

If you want to trade all tickers except the ones in IGNORE_TICKERS, then set ALL_TICKERS, LONG_TICKERS and SHORT_TICKERS to ""

Fixed a bug in moving SL to breakeven
updated logic to move the SL to close to breakeven if ROI > SL_BREAKEVEN_PERCENTAGE of PROFIT_PERCENTAGE and LOSS_PERCENTAGE < PROFIT_PERCENTAGE , this way initially you can set a larger SL percentage initially so you are not stopped out early, and once ROI > SL_BREAKEVEN_PERCENTAGE of PROFIT_PERCENTAGE, SL will use PROFIT_PERCENTAGE to Trail    


## version 3.3.8 ##
Fixed a bug in moving SL to breakeven
updated logic to move the SL to close to breakeven if ROI > 75% of PROFIT_PERCENTAGE and LOSS_PERCENTAGE < PROFIT_PERCENTAGE , this way initially you can set a larger SL percentage initially so you are not stopped out early, and once ROI > 75% of PROFIT_PERCENTAGE, SL will use PROFIT_PERCENTAGE to Trail    


## version 3.3.7 ##
Added
MINIMUM_CONSECUTIVE_CANDLES (default = 2)
    Minimum number of consecutive candles to consider for a signal.

Added a logic to move the SL to breakeven if ROI > PROFIT_PERCENTAGE and LOSS_PERCENTAGE < PROFIT_PERCENTAGE , this way initially you can set a larger SL so you are not stopped out early, and once ROI > PROFIT_PERCENTAGE, SL will use PROFIT_PERCENTAGE to Trail    

## version 3.3.6 ##
Removed
BOT_TRAIL_TP_SL

Added
BOT_TRAIL_TP
    if set to True then bot will trail the TP in the direction of profit    
BOT_TRAIL_SL
    if set to True then bot will trail the SL in the direction of profit

## version 3.3.5 ##
Renamed config
BOT_TAKE_PROFIT_STOP_LOSS to BOT_CONTROLS_TP_SL
BOT_TRAIL_STOP_LOSS to BOT_TRAIL_TP_SL

## version 3.3.4 ##
BOT_TRAIL_STOP_LOSS 
if set to True then bot will trail the TP and SL in the direction of profit

## version 3.3.3 ##
added new config
BOT_TRAIL_STOP_LOSS 
if set to True then bot will move the stop loss to breakeven when the trade is reaches 50% of the target profit and then move the stop loss to the 50% of the target profit when the trade reaches 90% of the target profit.

## version 3.3.2 ##
removed config
PROFIT_LOSS_PRICE_TYPE
PROFIT_LOSS_ORDER_TYPE

and new added config
BOT_TAKE_PROFIT_STOP_LOSS=False
    if false take_prodit and stop loss will be placed when the trade is opened, 
    if true then take profit and stop loss will be placed by the bot when take profit or stop loss is reached. 
TAKE_PROFIT_PRICE_TYPE -> this can be "MARK_PRICE" or "LAST_PRICE"
TAKE_PROFIT_ORDER_TYPE=LIMIT -> this can be "MARKET" or "LIMIT" 
STOP_LOSS_PRICE_TYPE=MARK_PRICE -> this can be "MARK_PRICE" or "LAST_PRICE"
STOP_LOSS_ORDER_TYPE=MARKET -> this can be "MARKET" or "LIMIT" 

## version 3.3.1 ##
bug fix

## version 3.3.0 ##
Fix for takeprofit and stoploss calculation

## version 3.2.9 ##
fixed a bug

## version 3.2.8 ##
fixed a bug

## version 3.2.7 ##
if PROFIT_PERCANTAGE, PROFIT_AMOUNT is > 0 then The trade is opened with take profit trade immediately instead of bot placing it after profit is reached.
if LOSS_PERCANTAGE, LOSS_AMOUNT is > 0 then The trade is opened with stop loss trade immediately instead of bot placing it after loss is reached.
_PERCANTAGE has greater priority over _AMOUNT. 

Added 2 new config
PROFIT_LOSS_PRICE_TYPE -> this can be "MARK_PRICE" or "LAST_PRICE"
PROFIT_LOSS_ORDER_TYPE -> this can be "MARKET" or "LIMIT" 


## version 3.2.6 ##
Default config:
Will open a trade ema_crossing or bbm_crosing or macd_crossing or rsi_crossing or bos_breakout or trendline_breakout happens and adx is strong and candle_trend is bullish.
Will close a trade profit percentage is 10% or loss percentage is 10%

Reversed the log entries to show the latest changes at the top.

Fix a bug in Selected Signal, not get cleared

Added a new config DELAY_IN_MINUTES_FOR_SAME_TICKER_TRADES, this will prohibit bot from trading the same ticker within the specified delay period. 

## verson 3.2.5 ##
Fixed Total Profit display

Added display of portfolio value in the web page

## version 3.2.4 ##
Added ma_spread to identify bullish or bearish trend, it is now used in EMA signals