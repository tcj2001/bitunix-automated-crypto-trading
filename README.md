# Bitunix Futures Auto Trading Platform

A real-time cryptocurrency trading platform built with FastAPI and WebSocket technology using Bitunix API and websockets for Futures. The platform provides automated trading capabilities, real-time market data visualization, and portfolio management features.

## Current Issue
sometimes Web page takes a long time to load, need to investigate the issue

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
  - Candlestick charts for all timeframes (1m, 5m, 15m, 1h, 1d) on a single page with all indicators
    - Chart is activated when you click on the ticker symbol
- Technical analysis including:
  - Moving Averages
  - MACD
  - Bollinger Bands
  - RSI
  - Brearish or bullish candle based on the close near high or low of the current candle
  - strength based on consecutive colored candles count
- Secure authentication system
- Configurable trading parameters
- Real-time notifications
- Logging system with colored output

## Prerequisites

- Python 3.8+
- pip package manager
- Git

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd bitunix
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory with your configuration:
```env
API_KEY=your_api_key
SECRET_KEY=your_secret_key
SECRET=your_jwt_secret
PASSWORD=your_password
HOST=127.0.0.1
```

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

## Usage

1. Start the server:
```bash
python bitunix.py
```

2. Access the web interface:
   - Open your browser and navigate to `http://localhost:8000`
   - Log in with your credentials (currenly user and password is memory based)

3. Monitor your positions and trades:
   - Real-time portfolio value
   - Open positions
   - Active orders
   - Trading signals

## Project Structure

```
bitunix/
├── bitunix.py              # Main application file
├── BitunixSignal.py        # Trading signals and strategy implementation
├── BitunixApi.py           # API client implementation
├── BitunixWebSocket.py     # Websocketclient implementation
├── TickerManager.py        # Tickers, Ticker, Interval management
├── NotificationManager.py  # Notification management               
├── AsyncThreadRunner.py    # Async thread runner
├── ThreadManager.py        # Thread management
├── config.py               # Configuration management
├── logger.py               # Logging configuration
├── requirements.txt        # Project dependencies
├── templates/              # HTML templates
│   ├── main.html           # Main dashboard template
│   ├── login.html          # Login page template
│   └── charts.html         # Charts page template
└── .env                    # Environment variables
```

## Logging

The platform includes a logging system with colored output for trade type
- CYAN: Closing trades
- GREEN: Closed trades with profit
- RED: Closed traded with loss 
- YELLOW: Opening trades
- PURPLE: Opened trades
- BLUE: Auto canceled trades

Logs are also stored in `app.log` with automatic rotation when size limits are reached.

## WebSocket Endpoints

- `/wsmain`: Main WebSocket connection for real-time updates
- `/ws`: Chart data WebSocket connection

## Security

- JWT-based authentication
- Secure password hashing
- Environment variable configuration
- API key management

## Development

For development and debugging:
- VS Code launch configuration is provided in `.vscode/launch.json`
- Debug configuration is set up for Python debugging
- Use the integrated terminal for running the application

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

https://opensource.org/licenses/MIT

## Support

thomsonmathews@hotmail.com

If you like this project buy me a lunch or coffee
- 35ocu1V25Zw9tgXyrcWudUqpj8rHbT2CdE  (bitcoin)
- DEXXvZbTbxeaYCh3EMf7MsdptbAU2kujDc  (dogecoin)
