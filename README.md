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
  - control study using the environment variables
- Secure authentication system
- Configurable trading parameters
- Real-time notifications
- Logging system with colored output


## Configuration

The platform can be configured through the `config.py` file or environment variables. Key configuration parameters include:

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

- Automated Trading Algorithm is customizable:
  - It allow you to select the moving average period (1h, 1d, 15m, 5m, 1m)
  - It allow to select how many auto trades you want to open at a time
  - CalculateStudy Function inside TickerManager.py (Interval class)
    - You can setup current_signal (BUY,SELL,HOLD) and signal_strength (numeric value) based on your strategy
    - current_signal can be setup based on Moving Average, MACD, Bollinger Band, RSI or close proximity to high or low of the candle
    - signal_strength can be setup based on number of consecutive green or red candles or any other strategy
  - AutoTradeProcess function inside BitunixSignal.py, you can setup your opening and closing trading strategy
    - User interface will list the stocks in the signal window with BUY or SELL signal based on the descending value of signal_strength
    - you have the option to manually initiate a trade or let the auto trade process to initiate the trade on top row in the signal window
    - You can manually close the trade on the current positions window or let the auto trade process to close the trade based on following conditions:
      - If the current open position reversed direction, it will close the trade
      - If the trade is in profit and greater than the profit_amount , it will close the trade
      - If the trade is in profit and greater than the profit_amount , it will close the trade
      - If the trade is in loss and greater than the loss_amount , it will close the trade
      - If the orderis open for more than 1 minute, it will close the open orders
      - It will close long or short postions:
        - If the trade is long and the fast moving average is above the medium moving average, it will close the trade
        - If the trade is short and the fast moving average is below the medium moving average, it will close the trade
        - If the trade is long and the MACD_line < Signal_line, it will close the trade
        - If the trade is short and the MACD_line > Signal_line, it will close the trade
        - If the trade is long and the RSI > 90, it will close the trade
        - If the trade is short and the RSI < 10, it will close the trade
        - if the trade is long and current close is less bollinger band middle line , it will close the trade
        - if the trade is short and the current close is above bollinger band middle line , it will close the trade


## Instructions

1. Installation
  - This uses TA-LIb
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
    host=127.0.0.1

  - cd bitunix/code
  - python3 bitunix.py 

2. Access the web interface:
   - Open your browser and navigate to `http://localhost:8000`
   - Log in with your credentials (currenly user is admin and password is your_password in env file)

3. Monitor your positions and trades:
   - Real-time portfolio value
   - Open positions
   - Active orders
   - Trading signals
   - Position history

   To change any parameter in the screen you need to deactivate and activate AutoTrade checkbox

## License

https://opensource.org/licenses/MIT

## Support

thomsonmathews@hotmail.com

If you like this project buy me a lunch or coffee
- 35ocu1V25Zw9tgXyrcWudUqpj8rHbT2CdE  (bitcoin)
- DEXXvZbTbxeaYCh3EMf7MsdptbAU2kujDc  (dogecoin)
