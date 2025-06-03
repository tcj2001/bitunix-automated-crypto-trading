from pydantic import Field, SecretStr, validator
from pydantic_settings import BaseSettings
import os
import sqlite3

class Settings(BaseSettings):
    # Start autotrading on start
    AUTOTRADE: bool = Field(default=False)
    
    #Ticker list
    TICKERS:str = Field(default="")
    THRESHOLD: float = Field(default=5.0, ge=0.0)
    MIN_VOLUME: int = Field(default=10_000_000, ge=0)

    # Trading Parameters
    LEVERAGE: int = Field(default=20, ge=1, le=100)
    ORDER_AMOUNT_PERCENTAGE: float = Field(default=0.01, ge=0.0, le=100)
    MAX_AUTO_TRADES: int = Field(default=10, ge=0)
    PROFIT_AMOUNT: float = Field(default=0.25, ge=0.0)
    LOSS_AMOUNT: float = Field(default=5.0, ge=0.0)
    OPTION_MOVING_AVERAGE: str = Field(default="1h")
    BARS: int = Field(default=100, ge=1)

    # Technical Indicators Parameters
    MA_FAST: int = Field(default=10, ge=1)
    MA_MEDIUM: int = Field(default=20, ge=1)
    MA_SLOW: int = Field(default=50, ge=1)
    RSI_FAST: int = Field(default=6, ge=1)
    RSI_SLOW: int = Field(default=24, ge=1)
    BBM_PERIOD: int = Field(default=20, ge=1)
    BBM_STD: int = Field(default=2, ge=1)
    MACD_PERIOD: int = Field(default=9, ge=1)
    MACD_SHORT: int = Field(default=12, ge=1)
    MACD_LONG: int = Field(default=26, ge=1)
    ADX_PERIOD: int = Field(default=14, ge=1)

    # Technical Indicators
    OPEN_ON_ANY_SIGNAL: bool = Field(default=True)

    BOS_STUDY: bool = Field(default=True)
    EMA_CHART: bool = Field(default=True)
    EMA_STUDY: bool = Field(default=True)
    EMA_CROSSING: bool = Field(default=False)
    EMA_CHECK_ON_OPEN: bool = Field(default=True)
    EMA_CHECK_ON_CLOSE: bool = Field(default=True)
    EMA_CLOSE_ON_FAST_MEDIUM: bool = Field(default=True)

    MACD_CHART: bool = Field(default=False)
    MACD_STUDY: bool = Field(default=True)
    MACD_CROSSING: bool = Field(default=False)
    MACD_CHECK_ON_OPEN: bool = Field(default=False)
    MACD_CHECK_ON_CLOSE: bool = Field(default=False)

    BBM_CHART: bool = Field(default=False)
    BBM_STUDY: bool = Field(default=True)
    BBM_CROSSING: bool = Field(default=False)
    BBM_CHECK_ON_OPEN: bool = Field(default=False)
    BBM_CHECK_ON_CLOSE: bool = Field(default=False)

    RSI_CHART: bool = Field(default=False)
    RSI_STUDY: bool = Field(default=True)
    RSI_CROSSING: bool = Field(default=False)
    RSI_CHECK_ON_OPEN: bool = Field(default=False)
    RSI_CHECK_ON_CLOSE: bool = Field(default=False)

    TRENDLINE_PEAK_DISTANCE: int = Field(default=1, ge=0, le=30)
    TRENDLINE_CHART: bool = Field(default=True)
    TRENDLINE_STUDY: bool = Field(default=True)
    TRENDLINE_BREAKOUT: bool = Field(default=False)
    TRENDLINE_CHECK_ON_OPEN: bool = Field(default=False)
    TRENDLINE_CHECK_ON_CLOSE: bool = Field(default=False)

    ADX_STUDY: bool = Field(default=True)
    ADX_CHECK_ON_OPEN: bool = Field(default=False)
    ADX_CHECK_ON_CLOSE: bool = Field(default=False)

    CANDLE_TREND_STUDY: bool = Field(default=True)
    CANDLE_TREND_CHECK_ON_OPEN: bool = Field(default=False)
    CANDLE_TREND_REVERSAL_CHECK_ON_CLOSE: bool = Field(default=False)

    # Time Intervals
    SCREEN_REFRESH_INTERVAL: int = Field(default=1, ge=1)
    SIGNAL_CHECK_INTERVAL: int = Field(default=15, ge=1)
    PORTFOLIO_API_INTERVAL: int = Field(default=3, ge=1)
    PENDING_POSITIONS_API_INTERVAL: int = Field(default=3, ge=1)
    PENDING_ORDERS_API_INTERVAL: int = Field(default=3, ge=1)
    TRADE_HISTORY_API_INTERVAL: int = Field(default=3, ge=1)
    POSITION_HISTORY_API_INTERVAL: int = Field(default=3, ge=1)
    TICKER_DATA_API_INTERVAL: int = Field(default=30, ge=1)
    BATCH_PROCESS_SIZE: int = Field(default=1000, ge=1)

    # Use websocket or API
    USE_PUBLIC_WEBSOCKET: bool = Field(default=False)  # If there is lagging issue then use API

    # Logger
    VERBOSE_LOGGING: bool = Field(default=False)

    #use CPU
    CPU_PROCCESING: bool = Field(default=True)

    # Benchmark
    BENCHMARK: bool = Field(default=False)

    class Config:
        # Specify the file name for loading environment variables
        env_file = os.path.dirname(os.path.abspath(__file__))+"/config.txt"

   
    @classmethod
    def load_from_db(cls, db_path: str, table_name: str = "settings"):
        # Connect to SQLite database
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()

        # Fetch all parameters and values from the database
        cursor.execute(f"SELECT param, value FROM {table_name}")
        rows = cursor.fetchall()
        connection.close()

        # Map fetched data to the class attributes dynamically
        settings_dict = {}
        for param, value in rows:
            # Convert string 'value' to proper type based on attribute type
            if hasattr(cls, param):
                attr_type = type(getattr(cls(), param))
                settings_dict[param] = attr_type(value) if attr_type != bool else value.lower() in ("true", "1")

        # Create the Settings instance with mapped data
        return cls(**settings_dict)

