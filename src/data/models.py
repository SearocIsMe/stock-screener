"""
Database models for the stock screener application
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Index
from sqlalchemy.orm import relationship
import enum
from .database import Base

class Exchange(enum.Enum):
    """Stock exchange enumeration"""
    SP500 = "SP500"
    NASDAQ = "NASDAQ"
    NYSE = "NYSE"
    ACN = "ACN"

class TimeFrame(enum.Enum):
    """Time frame enumeration"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class Stock(Base):
    """Stock model"""
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    exchange = Column(String, nullable=True)
    sector = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    market_cap = Column(Float, nullable=True)
    pe_ratio = Column(Float, nullable=True)
    gross_margin = Column(Float, nullable=True)  # 毛利率 (Gross Profit Margin)
    roe = Column(Float, nullable=True)  # 净资产收益率 (Return on Equity)
    rd_ratio = Column(Float, nullable=True)  # 研发比率 (R&D Ratio)
    pb_ratio = Column(Float, nullable=True)
    dividend_yield = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    prices = relationship("StockPrice", back_populates="stock", cascade="all, delete-orphan")
    filtered_results = relationship("FilteredStock", back_populates="stock", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Stock(symbol='{self.symbol}', name='{self.name}')>"

class StockPrice(Base):
    """Stock price model"""
    __tablename__ = "stock_prices"

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    adjusted_close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    time_frame = Column(String, nullable=False)  # daily, weekly, monthly
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    stock = relationship("Stock", back_populates="prices")

    # Indexes
    __table_args__ = (
        Index("idx_stock_date_timeframe", "stock_id", "date", "time_frame", unique=True),
    )

    def __repr__(self):
        return f"<StockPrice(stock_id={self.stock_id}, date='{self.date}', close={self.close})>"

class FilteredStock(Base):
    """Filtered stock model"""
    __tablename__ = "filtered_stocks"

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    filter_date = Column(DateTime, nullable=False)
    time_frame = Column(String, nullable=False)  # daily, weekly, monthly
    bias_value = Column(Float, nullable=True)
    rsi_value = Column(Float, nullable=True)
    macd_value = Column(Float, nullable=True)
    macd_signal = Column(Float, nullable=True)
    macd_histogram = Column(Float, nullable=True)
    gross_margin = Column(Float, nullable=True)  # 毛利率 (Gross Profit Margin)
    roe = Column(Float, nullable=True)  # 净资产收益率 (Return on Equity)
    rd_ratio = Column(Float, nullable=True)  # 研发比率 (R&D Ratio)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    stock = relationship("Stock", back_populates="filtered_results")

    # Indexes
    __table_args__ = (
        Index("idx_filter_date_timeframe", "filter_date", "time_frame"),
        Index("idx_stock_filter_date", "stock_id", "filter_date"),
    )

    def __repr__(self):
        return f"<FilteredStock(stock_id={self.stock_id}, filter_date='{self.filter_date}', time_frame='{self.time_frame}')>"