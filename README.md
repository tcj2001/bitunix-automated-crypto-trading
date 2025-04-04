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
    - clicking on the ticker symbol will open the current selected period chart in modal window
    - notification are written to log file and can be displayed by clicking the message bar
    - Config button allows to edit the confix.txt file directly from the app
    - Candlestick charts for all timeframes (1m, 5m, 15m, 1h, 1d) on a single page avaible when you click the charts button
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
  - `LEVERAGE`: Trading leverage (1-100)
  - `THRESHOLD`: Ticker selection based close near high or low of the day
  - `MIN_VOLUME`: Ticker selection based on Minimum trading volume
  - `ORDER_AMOUNT_PERCENTAGE`: Order size as percentage of portfolio
  - `MAX_AUTO_TRADES`: Maximum number of automated trades
  - `PROFIT_AMOUNT`: Target profit amount
  - `LOSS_AMOUNT`: Maximum loss amount
  - `OPTION_MOVING_AVERAGE`: Moving average period (1h, 1d, 15m, 5m, 1m)
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
    
  - `Study Parameters`:
    - `EMA_STUDY`: Enable EMA study
    - `EMA_CROSSING`: Check EMA crossing or crossed, COMPARING FAST AND MEDIUM MOVING AVERAGE 
    - `EMA_CHECK_ON_OPEN`: Check EMA on open
    - `EMA_CHECK_ON_CLOSE`: Check EMA on close

    - `MACD_STUDY`: Enable MACD study
    - `MACD_CROSSING`: Check MACD crossing or crossed, comparing MACD line and signal line
    - `MACD_CHECK_ON_OPEN`: Check MACD on open
    - `MACD_CHECK_ON_CLOSE`: Check MACD on close

    - `BBM_STUDY`: Enable Bollinger Band study
    - `BBM_CROSSING`: Check Bollinger Band crossing or crossed, comparing close and middle line
    - `BBM_CHECK_ON_OPEN`: Check Bollinger Band on open
    - `BBM_CHECK_ON_CLOSE`: Check Bollinger Band on close

    - `RSI_STUDY`: Enable RSI study
    - `RSI_CROSSING`: Check RSI crossing or crossed, comparing fast and slow RSI
    - `RSI_CHECK_ON_OPEN`: Check RSI on open
    - `RSI_CHECK_ON_CLOSE`: Check RSI on close

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
    - `PUBLIC_WEBSOCKET_RESTART_INTERVAL`: Public WebSocket restart interval
    
  - Currently not using public websocket for depth and ticker data as the data is lagging or missing sometime
    - `USE_PUBLIC_WEBSOCKET`: True or False

- Logging Parameters:
  -   `VERBOSE_LOGGING`: True or False

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

- Linux install (ubuntu 22.04)
  - sudo su -
  - # required for TA-Lib
  - wget https://github.com/ta-lib/ta-lib/releases/download/v0.6.4/ta-lib_0.6.4_amd64.deb
  - sudo dpkg -i ta-lib_0.6.4_amd64.deb
  - # change the tags/2.0 to the latest version in the script below and run it
  - bash -c "\
    apt-get install -y python3-pip wget unzip dos2unix && \
    python3 -m pip install --upgrade pip && \
    mkdir bitunix && cd bitunix && \
    wget https://github.com/tcj2001/bitunix-automated-crypto-trading/archive/refs/tags/2.0.tar.gz -O bitunix.tar.gz && \
    mkdir code && \
    tar --strip-components=1 -xvzf bitunix.tar.gz -C code && \
    cd code && \
    pip3 install -r requirements.txt && \
    cp sampleenv.txt .env"
  - The package will be installed in the bitunix/code directory
  - cd bitunix/code
  - python3 bitunix.py 

- Windows
  - mkdir c:\bitunix
  - cd c:\bitunix
  - python -m venv env
  - .\env\Scripts\activate
  - # check python version should be 3.13 or above
  - python3 --version
  - python -m pip install --upgrade pip
  - pip install https://github.com/cgohlke/talib-build/releases/download/v0.6.3/ta_lib-0.6.3-cp313-cp313-win_amd64.whl
  - # change the tags/2.0 to the latest version in the script below and run it
  - wget https://github.com/tcj2001/bitunix-automated-crypto-trading/archive/refs/tags/2.0.zip
  - unzip zip file and copy the content inside C:\bitunix\Ver1.0.zip\bitunix-automated-crypto-trading-Ver1.0 to c:\bitunix
  - pip install -r requirements.txt 
  - # Make sure ta-lib is installed
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
