# Bitunix Futures Auto Trading Platform

A real-time cryptocurrency trading platform built with FastAPI and WebSocket technology using Bitunix API and websockets for Futures. The platform provides automated trading capabilities, real-time market data visualization, and portfolio management features.

## Features
- Real-time private account/new postion/new order data streaming via WebSocket
- Real-time public depth/kline for bid, ask and last streaming via WebSocket or thru api calls, configurable in the config file
- Automated trading strategies based on technical indicators
- Portfolio management and position tracking
- User interface is not a requirement for automated trading, all parmaeters can be configured in the config file 
  - login page
  - main page:
    - Interactive web interface with real-time updates, allows manual trading
    - Real-time portfolio value
    - Open positions, with signals and strength
    - Active orders
    - selected signals with strength
    - all signals with strength
    - position history
    - clicking on the ticker symbol will open the chart page
    - maintians a list of notification which can be access by clicking on the notification
  - Candlestick charts for all timeframes (1m, 5m, 15m, 1h, 1d) on a single page with all indicators
    - Chart is activated when you click on the ticker symbol
- Technical analysis including:
  - Moving Averages
  - MACD
  - Bollinger Bands
  - RSI
  - Brearish or bullish candle based on the close near high or low of the current candle
  - strength based on consecutive colored candles count
  - ADX
  - control study using the environment variables
- Secure authentication system
- Configurable trading parameters
- Real-time notifications
- Logging system with colored output


## Configuration

The platform can be configured through the `config.py` file or environment variables. Key configuration parameters include:

- API Keys
  - `api_key`: Bitunix API key
  - `secret_key`: Bitunix secret key
  - `SECRET`: JWT secret for authentication, some string like "7c4c22ef6ad145f922c72f5a18047b6bf6eff983381c975c"
  - `password`: Password for the web interface

- Trading Parameters:
  - `leverage`: Trading leverage (1-100)
  - `threshold`: Ticker selection based close near high or low of the day
  - `min_volume`: Ticker selection based on Minimum trading volume
  - `order_amount_percentage`: Order size as percentage of portfolio
  - `max_auto_trades`: Maximum number of automated trades
  - `profit_amount`: Target profit amount
  - `loss_amount`: Maximum loss amount
  - `option_moving_average`: Moving average period (1h, 1d, 15m, 5m, 1m)
  - `AutoTrade checkbox`: set the trading parameters and initate the auto trade process
  - `bars`: Number of bars to use for study and charting

- `Technical Indicators Parameters`:
    - `ma_fast`: Fast moving average period
    - `ma_medium`: Medium moving average period
    - `ma_slow`: Slow moving average period
    - `rsi_fast`: Fast RSI period
    - `rsi_slow`: Slow RSI period
    - `bbm_period`: Bollinger Band middle period
    - `bbm_std`: Bollinger Band standard deviation
    - `macd_period`: MACD period
    - `macd_short`: MACD short period
    - `macd_long`: MACD long period
    - `adx_period`: ADX period
  
  - `Study Parameters`:
    - `ema_study`: Enable EMA study
    - `macd_study`: Enable MACD study
    - `bbm_study`: Enable Bollinger Band study
    - `rsi_study`: Enable RSI study
    - `candle_trend_study`: Enable candle trend study
    - `adx_study`: Enable ADX study
  
  - `Check on Opening a Position`:
    - `ema_check_on_open`: Check EMA on open
    - `macd_check_on_open`: Check MACD on open
    - `bbm_check_on_open`: Check Bollinger Band on open
    - `rsi_check_on_open`: Check RSI on open
    - `candle_trend_check_on_open`: Check candle trend on open
    - `adx_check_on_open`: Check ADX on open
  
  - `Check on Close a Position`:
    - `ema_check_on_close`: Check EMA on close
    - `macd_check_on_close`: Check MACD on close
    - `bbm_check_on_close`: Check Bollinger Band on close
    - `rsi_check_on_close`: Check RSI on close
    - `candle_trend_check_on_close`: Check candle trend on close
    - `adx_check_on_close`: Check ADX on close
  
  - `intervals`:
    - `screen_refresh_interval`: Screen refresh interval
    - `signal_check_interval`: Signal check interval
    - `portfolio_api_interval`: Portfolio API interval
    - `pending_positions_api_interval`: Pending positions API interval
    - `pending_orders_api_interval`: Pending orders API interval
    - `trade_history_api_interval`: Trade history API interval
    - `position_history_api_interval`: Position history API interval
    - `ticker_data_api_interval`: Ticker data API interval
    - `public_websocket_restart_interval`: Public WebSocket restart interval

  - Currently not using public websocket for depth and ticker data as the data is lagging or missing sometime
    - `use_public_websocket`=False

- Logging Parameters:
  -   `verbose_logging`=False

## User Interface

- Access the web interface:
   - Open your browser and navigate to `http://localhost:8000` or `http://your_server_ip:8000`
   - Log in with your credentials (currenly user is admin and password is your_password in env file)

- Monitor your positions and trades:
   - Real-time portfolio value
   - Open positions
   - Active orders
   - Trading signals
   - Position history
   - Manual trading using buy, sell, add, reduce buttons

- Autotrade using the AutoTrade checkbox
    - you can change
      - Moving Average period
      - Max auto trades
      - Take Profit amount
      - Accept Loss amount
    - You can control the study like Moving Average, MACD, Bollinger Band, RSI or close proximity to high or low of the candle using the env file
    - You can control the trading strategy using the CalculateStudy function in TickerManager.py and AutoTradeProcess function in BitunixSignal.py
    - Changes are activated by unchecking and checking the AutoTrade checkbox

## Auto Trading

- Automated Trading Algorithm is customizable:
  - It allow you to select the moving average period (1h, 1d, 15m, 5m, 1m)
  - It allow to select how many auto trades you want to open at a time
  - CalculateStudy Function inside TickerManager.py (Interval class)
    - You can setup current_signal (BUY,SELL,HOLD) and signal_strength (numeric value) based on your strategy
    - current_signal can be setup based on Moving Average, MACD, Bollinger Band, RSI or close proximity to high or low of the candle
    - signal_strength can be setup based on number of consecutive green or red candles or any other strategy
  - AutoTradeProcess function inside BitunixSignal.py, you can setup your opening and closing trading strategy
  - User interface will list the stocks in the signal window with BUY or SELL signal based on the descending value of signal_strength
  - All study can be controlled thru environment variables
  - Auto trade process open the trade based on following conditions:
    - If the current candle is bullish 
      and moving average is above the medium moving average
      and MACD_line > Signal_line
      and RSI is above the long RSI
      and current close is above bollinger band middle line
      and ADX is above 25 (STRONG)
      it will open long position
    - If the current candle is bearish
      and moving average is below the medium moving average
      and MACD_line < Signal_line
      and RSI is below the long RSI
      and current close is belowe bollinger band middle line
      and ADX is above 25 (STRONG)
      it will open short position
  - Auto trade process closes the trade based on following conditions:
    - If the current candle is bearish, it will close the trade
    - If the trade is in profit and greater than the profit_amount , it will close the trade
    - If the trade is in profit and greater than the profit_amount , it will close the trade
    - If the trade is in loss and greater than the loss_amount , it will close the trade
    - If the order is open for more than 1 minute, it will close the open orders
    - It will close long or short postions:
      - If the trade is long and the fast moving average is above the medium moving average, it will close the trade
      - If the trade is short and the fast moving average is below the medium moving average, it will close the trade
      - If the trade is long and the MACD_line < Signal_line, it will close the trade
      - If the trade is short and the MACD_line > Signal_line, it will close the trade
      - If the trade is long and the short RSI < long RSI, it will close the trade
      - If the trade is short and the short RSI > long RSI, it will close the trade
      - if the trade is long and current close is less bollinger band middle line , it will close the trade
      - if the trade is short and the current close is above bollinger band middle line , it will close the trade
      - if the trade is long or short and the ADX is below 25 (WEAK), it will close the trade


## Installation

- This uses TA-LIb
  - sudo apt-get update
  - sudo apt-get install build-essential libssl-dev libffi-dev python3.9-dev
  - For windows install using precompiled wheel using
    - pip install https://github.com/cgohlke/talib-build/releases/download/v0.6.3/ta_lib-0.6.3-cp313-cp313-win_amd64.whl
  - For linux download
    - wget https://github.com/ta-lib/ta-lib/releases/download/v0.6.4/ta-lib_0.6.4_amd64.deb
    - sudo dpkg -i ta-lib_0.6.4_amd64.deb
    
- Change the Ver1.0 to the latest version in the script
  - bash -c "\
    apt-get install -y python3.9 python3.9-distutils python3-pip wget unzip dos2unix && \
    ln -sf /usr/bin/python3.9 /usr/bin/python3 && \
    python3 -m pip install --upgrade pip && \
    mkdir bitunix && cd bitunix && \
    wget https://github.com/tcj2001/bitunix-automated-crypto-trading/archive/refs/tags/Ver1.0.tar.gz -O bitunix.tar.gz && \
    mkdir code && \
    tar --strip-components=1 -xvzf bitunix.tar.gz -C code && \
    cd code && \
    pip3 install -r requirements.txt && \
    cp sampleenv.txt .env"


- The package will be installed in the bitunix/code directory

- make sure to update the .env file with your keys
  api_key=your_api_key
  secret_key=your_secret_key
  SECRET=your_jwt_secret
  password=your_password
  host=0.0.0.0 (for server) or 127.0.0.1 (for local)

- cd bitunix/code
- python3 bitunix.py 

 
## License

https://opensource.org/licenses/MIT

## Support

thomsonmathews@hotmail.com

If you like this project buy me a lunch or coffee
- 35ocu1V25Zw9tgXyrcWudUqpj8rHbT2CdE  (bitcoin)
- DEXXvZbTbxeaYCh3EMf7MsdptbAU2kujDc  (dogecoin)
