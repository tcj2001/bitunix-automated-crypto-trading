from pydantic import Field, SecretStr, validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
   
    # API Configuration
    api_key: SecretStr
    secret_key: SecretStr
    SECRET: SecretStr
    password: SecretStr  
    host: str = Field(default="127.0.0.1")

    #start autotrading on start
    autoTrade: bool = Field(default=False)

    # Trading Parameters
    leverage: int = Field(default=20, ge=1, le=100)
    threshold: float = Field(default=5.0, ge=0.0)
    min_volume: int = Field(default=10000000, ge=0)
    order_amount_percentage: float = Field(default=0.01, ge=0.0, le=1.0)
    max_auto_trades: int = Field(default=10, ge=0)
    profit_amount: float = Field(default=0.25, ge=0.0)
    loss_amount: float = Field(default=5.0, ge=0.0)
    option_moving_average: str = Field(default="1h")
    bars: int = Field(default=100, ge=1)

    # Technical Indicators Parameters    
    ma_fast: int = Field(default=12, ge=1)
    ma_medium: int = Field(default=26, ge=1) 
    ma_slow: int = Field(default=50, ge=1)
    rsi_fast: int = Field(default=6, ge=1)
    rsi_slow: int = Field(default=24, ge=1)
    bbm_period: int = Field(default=20, ge=1)
    bbm_std: int = Field(default=2, ge=1)
    macd_period: int = Field(default=9, ge=1)
    macd_short: int = Field(default=12, ge=1)
    macd_long: int = Field(default=26, ge=1)
    adx_period: int = Field(default=14, ge=1)

    # Technical Indicators
    ema_study: bool = Field(default=True)
    macd_study: bool = Field(default=True)
    bbm_study: bool = Field(default=True)
    rsi_study: bool = Field(default=True)
    candle_trend_study: bool = Field(default=True)
    adx_study: bool = Field(default=True)

    ema_check_on_open: bool = Field(default=True)
    ema_check_on_close: bool = Field(default=False)
    macd_check_on_open: bool = Field(default=True)
    macd_check_on_close: bool = Field(default=False)
    rsi_check_on_open: bool = Field(default=True)
    rsi_check_on_close: bool = Field(default=False)
    bbm_check_on_open: bool = Field(default=True)
    bbm_check_on_close: bool = Field(default=False)
    candle_trend_check_on_open: bool = Field(default=True)
    candle_trend_check_on_close: bool = Field(default=False)
    adx_check_on_open: bool = Field(default=True)
    adx_check_on_close: bool = Field(default=False)

    # Time Intervals
    screen_refresh_interval: int = Field(default=1, ge=1)
    signal_check_interval: int = Field(default=15, ge=1)
    portfolio_api_interval: int = Field(default=3, ge=1)
    pending_positions_api_interval: int = Field(default=3, ge=1)
    pending_orders_api_interval: int = Field(default=3, ge=1)
    trade_history_api_interval: int = Field(default=3, ge=1)
    position_history_api_interval: int = Field(default=3, ge=1)
    ticker_data_api_interval: int = Field(default=30, ge=1)
    public_websocket_restart_interval: int = Field(default=10800, ge=1)
        
    # use websocket or use api
    use_public_websocket: bool = Field(default=False)  #if there is lagging issue then use api
    # logger
    verbose_logging: bool = Field(default=False)
    #benchmark
    benchmark: bool = Field(default=False)

    # Validation for secrets
    @validator('api_key', 'secret_key', 'SECRET', 'password')
    def validate_secrets(cls, v):
        if isinstance(v, SecretStr):
            if v.get_secret_value().startswith('your_') or v == 'default':
                raise ValueError('Please set proper values for secrets')
            if len(v) < 16:  # Minimum length requirement
                raise ValueError('Secret too short - minimum 16 characters')
        return v

    def reload_env(self):
        """Reload the .env file and update the settings."""
        updated_instance = self.__class__()  # Create a new instance with updated values
        self.__dict__.update(updated_instance.__dict__)  # Update current instance with new values

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = True