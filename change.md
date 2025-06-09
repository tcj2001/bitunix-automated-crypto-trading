# Change Log
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