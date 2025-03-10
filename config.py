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
    min_volume: int = Field(default=10000000, ge=0, alias="minVolume")
    order_amount_percentage: float = Field(default=0.01, ge=0.0, le=1.0, alias="orderAmountPercentage")
    max_auto_trades: int = Field(default=0, ge=0, alias="maxAutoTrades")
    profit_amount: float = Field(default=0.5, ge=0.0, alias="profitAmount")
    loss_amount: float = Field(default=1.0, ge=0.0, alias="lossAmount")
    option_moving_average: str = Field(default="1h", alias="optionMovingAverage")
    bars: int = Field(default=100, ge=1)

    # Technical Indicators
    ma_fast: int = Field(default=12, ge=1)
    ma_medium: int = Field(default=26, ge=1)
    ma_slow: int = Field(default=50, ge=1)
    check_ema: bool = Field(default=True)
    check_macd: bool = Field(default=True)
    check_bbm: bool = Field(default=True)
    check_rsi: bool = Field(default=True)

    # Intervals
    screen_refresh_interval: int = Field(default=3, ge=1)
    signal_interval: int = Field(default=3, ge=1)
    api_interval: int = Field(default=3, ge=1)
    public_websocket_restart_interval: int = Field(default=10800, ge=60)    # restart to avoid lagging issue

    # use websocket or use api
    use_public_websocket: bool = Field(default=False)  #if there is lagging issue then use api

    # logger
    verbose_logging: bool = Field(default=False)

    # Validation for secrets
    @validator('api_key', 'secret_key', 'SECRET', 'password')
    def validate_secrets(cls, v):
        if isinstance(v, str):
            if v.startswith('your_') or v == 'default':
                raise ValueError('Please set proper values for secrets')
            if len(v) < 16:  # Minimum length requirement
                raise ValueError('Secret too short - minimum 16 characters')
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = True

