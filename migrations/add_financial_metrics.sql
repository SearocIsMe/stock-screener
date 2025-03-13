-- Migration script to add financial metrics columns to the database

-- Add financial metrics columns to stocks table
ALTER TABLE stocks 
ADD COLUMN gross_margin FLOAT,
ADD COLUMN roe FLOAT,
ADD COLUMN rd_ratio FLOAT;

-- Add financial metrics columns to filtered_stocks table
ALTER TABLE filtered_stocks
ADD COLUMN gross_margin FLOAT,
ADD COLUMN roe FLOAT,
ADD COLUMN rd_ratio FLOAT;

-- Add indexes for financial metrics columns
CREATE INDEX idx_stocks_gross_margin ON stocks (gross_margin);
CREATE INDEX idx_stocks_roe ON stocks (roe);
CREATE INDEX idx_stocks_rd_ratio ON stocks (rd_ratio);

-- Add comment to explain the financial metrics
COMMENT ON COLUMN stocks.gross_margin IS '毛利率 (Gross Profit Margin)';
COMMENT ON COLUMN stocks.roe IS '净资产收益率 (Return on Equity)';
COMMENT ON COLUMN stocks.rd_ratio IS '研发比率 (R&D Ratio)';

COMMENT ON COLUMN filtered_stocks.gross_margin IS '毛利率 (Gross Profit Margin)';
COMMENT ON COLUMN filtered_stocks.roe IS '净资产收益率 (Return on Equity)';
COMMENT ON COLUMN filtered_stocks.rd_ratio IS '研发比率 (R&D Ratio)';