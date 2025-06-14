# Bitunix Futures Auto Trading Platform

A real-time cryptocurrency trading platform built with FastAPI and WebSocket technology using Bitunix API and websockets for Futures. The platform provides automated trading capabilities, real-time market data visualization, and portfolio management features.

Supports running the app in multiple instances (bots) with each instance having its own configuration file and env file containing the API keys and other parameters. 

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
    - clicking on the ticker symbol will open the current selected period chart in modal window
    - notification are written to log file and can be displayed by clicking the message bar
    - Config button allows to edit the confix.txt file directly from the app
    - Candlestick charts for all timeframes (1m, 5m, 15m, 1h, 1d) on a single page avaible when you click the charts button
- Technical analysis including:
  - Moving Averages
  - MACD
  - Bollinger Bands
  - RSI
  - Support and Resistance levels
  - Brearish or bullish candle based on the close near high or low of the current candle
  - strength based on consecutive colored candles count
  - ADX
  - control study using the environment variables
- Secure authentication system
- Configurable trading parameters
- Real-time notifications
- Logging system with colored output
- Update environment variables without restarting the application


## Configuration
.env file
- `API_KEY`: Bitunix API key
- `SECRET_KEY`: Bitunix secret key
- `SECRET`: JWT secret for authentication, some string like "7c4c22ef6ad145f922c72f5a18047b6bf6eff983381c975c"
- `PASSWORD`: Password for the web interface
- `HOST`: Host IP address (e.g., 0.0.0.0 for server, 127.0.0.1 for local)

The platform can be configured through the `config.py` file or `config.txt`. Key configuration parameters include:
- Trading Parameters:
  - `AUTOTRADE` : True or False

  - `ALL_TICKERS`  will be tickers that are not in LONG_TICKERS and SHORT_TICKERS, this willtrade all other tickers that are not in LONG_TICKERS and SHORT_TICKERS
  - `LONG_TICKERS` will always trade long, even if the signal is SELL
  - `SHORT_TICKERS` will always trade short, even if the signal is BUY
  - `IGNORE_TICKERS` will not trade these tickers
    If you want to trade all tickers except the ones in IGNORE_TICKERS, then set ALL_TICKERS, LONG_TICKERS and SHORT_TICKERS to ""
  
  - `TICKERS`: supply a list of tickers seperated by comma to trade, e.g., "BTCUSDT,ETHUSDT" or "" to auto select based on MIN_VOLUME and THRESHOLD
  - `LEVERAGE`: Trading leverage (1-100)
  - `THRESHOLD`: Ticker selection based close near high or low of the day
  - `MIN_VOLUME`: Ticker selection based on Minimum trading volume
  - `ORDER_AMOUNT_PERCENTAGE`: Order size as percentage of portfolio
  - `MAX_AUTO_TRADES`: Maximum number of automated trades
  - `TP_AMOUNT`: Target profit amount
  - `SL_AMOUNT`: Maximum loss amount
  - `TP_PERCENTAGE`: Target profit ROI percentage

  - `TP_ROI_PERCENTAGE_1`: ROI percentage for the firts TP
  - `TP_ROI_PERCENTAGE_2`: ROI percentage for the second TP
  - `TP_ROI_PERCENTAGE_3`: ROI percentage for the third TP
  - `TP_QTY_PERCENTAGE_1`: Quantity percentage for the first TP
  - `TP_QTY_PERCENTAGE_2`: Quantity percentage for the second TP   
  - `TP_QTY_PERCENTAGE_3`: Quantity percentage for the third TP, if zero then the remaining quantity will be used for the last TP
     the above setting need TP_PERCENTAGE set to 0 and BOT_TRAIL_TP to False

  - `SL_PERCENTAGE`: Maximum loss ROI percentage
  - `SL_BREAKEVEN_PERCENTAGE`
      Percentage of profit to move the stop loss to breakeven, default is 75%
  - `BOT_TRAIL_TP`
      if set to True then bot will trail the TP in the direction of profit    
  - `BOT_TRAIL_SL`
      if set to True then bot will trail the SL in the direction of profit
  - `PROFIT_LOSS_PRICE_TYPE`: "MARK_PRICE" or "LAST_PRICE"
  - `PROFIT_LOSS_ORDER_TYPE`: "MARKET" or "LIMIT" 
  - `OPTION_MOVING_AVERAGE`: Moving average period (1h, 1d, 15m, 5m, 1m)
  - `DELAY_IN_MINUTES_FOR_SAME_TICKER_TRADES`: Delay in minutes to prohibit trading the same ticker again
  - `BARS`: Number of bars to use for study and charting
    
  - `Technical Indicators Parameters`:
    - `MA_FAST`: Fast moving average period
    - `MA_MEDIUM`: Medium moving average period
    - `MA_SLOW`: Slow moving average period
    - `RSI_FAST`: Fast RSI period
    - `RSI_SLOW`: Slow RSI period
    - `BBM_PERIOD`: Bollinger Band middle period
    - `BBM_STD`: Bollinger Band standard deviation
    - `MACD_PERIOD`: MACD period
    - `MACD_SHORT`: MACD short period
    - `MACD_LONG`: MACD long period
    - `ADX_PERIOD`: ADX period
    - `MINIMUM_CONSECUTIVE_CANDLES`: Minimum number of consecutive candles to consider for a signal.
    
  - `Study Parameters`:
    - `EMA_STUDY`: Enable EMA study
    - `EMA_CHART`: Display EMA chart
    - `EMA_STUDY`: Enable EMA study
    - `EMA_CROSSING`: Check EMA crossing or crossed, COMPARING MEDIUM AND SLOW MOVING AVERAGE 
    - `EMA_CHECK_ON_OPEN`: Check EMA on open
    - `EMA_CHECK_ON_CLOSE`: Check EMA on close
    - `EMA_CLOSE_ON_FAST_MEDIUM`: Check EMA close comparing fast and medium

    - `MACD_STUDY`: Enable MACD study
    - `MACD_CHART`: Display MACD chart
    - `MACD_CROSSING`: Check MACD crossing or crossed, comparing MACD line and signal line
    - `MACD_CHECK_ON_OPEN`: Check MACD on open
    - `MACD_CHECK_ON_CLOSE`: Check MACD on close

    - `BBM_STUDY`: Enable Bollinger Band study
    - `BBM_CHART`: Display Bollinger Band chart
    - `BBM_CROSSING`: Check Bollinger Band crossing or crossed, comparing close and middle line
    - `BBM_CHECK_ON_OPEN`: Check Bollinger Band on open
    - `BBM_CHECK_ON_CLOSE`: Check Bollinger Band on close

    - `RSI_STUDY`: Enable RSI study
    - `RSI_CHART`: Display RSI chart
    - `RSI_CROSSING`: Check RSI crossing or crossed, comparing fast and slow RSI
    - `RSI_CHECK_ON_OPEN`: Check RSI on open
    - `RSI_CHECK_ON_CLOSE`: Check RSI on close

    - `BOS_PERIOD`: Break of structure period, number of bars to look back to determine the previous high or low
    - `BOS_STUDY`: Enable Break Of Structure study
    - `BOS_CHART`: Display Break Of Structure chart
    - `BOS_CHECK_ON_OPEN`: Check bos support and resistance on open
    - `BOS_CHECK_ON_CLOSE`: Check bos support and resistance on close

    - `TRENDLINE_PEAK_DISTANCE` : distance between peaks or troughs
    - `TRENDLINE_STUDY`: Enable Trendline support and resistance study
    - `TRENDLINE_CHART`: Display Trendline chart
    - `TRENDLINE_LOOKBACK`: Lookback period for trendline study
    - `TRENDLINE_BREAKOUT`: Check if breakout from support or resistance line
    - `TRENDLINE_CHECK_ON_OPEN`: Check Trendline support and resistance on open
    - `TRENDLINE_CHECK_ON_CLOSE`: Check Trendline support and resistance on close

    - `ADX_STUDY`: Enable ADX study
    - `ADX_CHECK_ON_OPEN`: Check ADX on open
    - `ADX_CHECK_ON_CLOSE`: Check ADX on close
  
    - `CANDLE_TREND_STUDY`: Enable candle trend study
    - `CANDLE_TREND_CHECK_ON_OPEN`: Check candle trend on open
    - `CANDLE_TREND_CHECK_ON_CLOSE`: Check candle trend on close
    
  - `intervals`:
    - `SCREEN_REFRESH_INTERVAL`: Screen refresh interval
    - `SIGNAL_CHECK_INTERVAL`: Signal check interval
    - `PORTFOLIO_API_INTERVAL`: Portfolio API interval
    - `PENDING_POSITIONS_API_INTERVAL`: Pending positions API interval
    - `PENDING_ORDERS_API_INTERVAL`: Pending orders API interval
    - `TRADE_HISTORY_API_INTERVAL`: Trade history API interval
    - `POSITION_HISTORY_API_INTERVAL`: Position history API interval
    - `TICKER_DATA_API_INTERVAL`: Ticker data API interval
    - `BATCH_PROCESS_SIZE`=2500 # Number of tick or bid/ask to process in a batch
    
  - Currently not using public websocket for depth and ticker data as the data is lagging or missing sometime
    - `USE_PUBLIC_WEBSOCKET`: True or False

- Logging Parameters:
  -   `VERBOSE_LOGGING`: True or False

- CPU processing parameters:
  -   `CPU_PROCESSING`: True or False
  
## User Interface

- Access the web interface:
   - Open your browser and navigate to `http://localhost:8000` or `http://your_server_ip:8000`
   - Log in with your credentials (currenly user is admin and password is your_password in env file)
   - display charts for all timeframes (1m, 5m, 15m, 1h, 1d) on a single page with all indicators when you click charts button
   - edit the config file directly from the app
   - display the log messages in amodal window by clicking the message bar
     
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
    - BOS study is basically when the price breakout from the previous high or low
    - Trendline study is basically when the price breakout from the trendline support or resistance
    - You can control the study like Moving Average, MACD, Bollinger Band, RSI or close proximity to high or low of the candle using the env file
    - You can control the trading strategy using the CalculateStudy function in TickerManager.py and AutoTradeProcess function in BitunixSignal.py
    - Changes are activated by unchecking and checking the AutoTrade checkbox
    - BOT controled take profit and stop loss or take_profit and stop_loss create when order is created
    - Trailing TP and SL in the direction of profit, if BOT_TRAIL_TP_SL to True and BOT_TAKE_PROFIT_STOP_LOSS to False in the config file

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
  - Auto trade process for opening the trade and closing the trade is configurable using the config file


## Installation

- Linux install (ubuntu 22.04)
  - sudo su -
  - required for TA-Lib
    - wget https://github.com/ta-lib/ta-lib/releases/download/v0.6.4/ta-lib_0.6.4_amd64.deb
    - sudo dpkg -i ta-lib_0.6.4_amd64.deb
  - change the tags/3.1.8 to the latest version in the script below and run it
    - bash -c "\
      apt-get install -y python3-pip wget unzip dos2unix && \
      python3 -m pip install --upgrade pip && \
      mkdir bitunix && cd bitunix && \
      wget https://github.com/tcj2001/bitunix-automated-crypto-trading/archive/refs/tags/v3.1.8.tar.gz -O bitunix.tar.gz && \
      mkdir code && \
      tar --strip-components=1 -xvzf bitunix.tar.gz -C code && \
      cd code && \
      pip3 install -r requirements.txt && \
      cp sampleenv.txt .env"
    - The package will be installed in the bitunix/code directory
    - cd bitunix/code
    - python3 bitunix.py .env config.txt 8000 (This is the default even if you dont pass these)
    
  For multiple instance or bots
  - python3 bitunix.py .env1 bot1.txt 8001
  - python3 bitunix.py .env2 bot2.txt 8002
  

- Windows
  - mkdir c:\bitunix
  - cd c:\bitunix
  - python -m venv env
  - .\env\Scripts\activate
  - check python version should be 3.13 or above
    - python3 --version
    - python -m pip install --upgrade pip
    - ta-lib, install it from https://ta-lib.org/install/#executable-installer-recommended
  - change the tags/3.1.8 to the latest version in the script below and run it
    - wget https://github.com/tcj2001/bitunix-automated-crypto-trading/archive/refs/tags/3.1.8.zip
    - unzip zip file and copy the content inside C:\bitunix\Ver1.0.zip\bitunix-automated-crypto-trading-Ver1.0 to c:\bitunix
  - pip install -r requirements.txt 
  - Make sure ta-lib is installed
    - python -c "import talib; print(talib.get_functions());"
  - copy sampleenv.txt to .env and update the keys accordingly
  - python bitunix.py 

- make sure to update the .env file with your keys
  api_key=your_api_key
  secret_key=your_secret_key
  SECRET=your_jwt_secret
  password=your_password
  host=0.0.0.0 (for server) or 127.0.0.1 (for local)

- cd bitunix/code
- python3 bitunix.py 

- This app will exit if there is any error detected on a the periodic async threads. create a systemd service to run the app in the background and restart it if it exits. The app will 

  - sudo nano /etc/systemd/system/bitunix.service and enter these lines

    Description=Bitunix service
    After=network.target
    StartLimitIntervalSec=0
    [Service]
    User=root
    Restart=always
    RestartSec=15
    ExecStart=/usr/bin/python3 /home/tcj2001/bitunix/code/bitunix.py
    WorkingDirectory=/home/tcj2001/bitunix/code

    [Install]
    WantedBy=multi-user.target

- systemctl daemon-reload
- systemctl enable bitunix.service
- systemctl start bitunix.service or just reboot the server
 
## License

https://opensource.org/licenses/MIT

## Support

thomsonmathews@hotmail.com

If you like this project buy me a lunch or coffee
- 35ocu1V25Zw9tgXyrcWudUqpj8rHbT2CdE  (bitcoin)
- DEXXvZbTbxeaYCh3EMf7MsdptbAU2kujDc  (dogecoin)
