# Stock Screener

A comprehensive stock screening application that filters stocks based on technical indicators.

## Features

- Fetch stock data from Yahoo Finance API
- Calculate technical indicators (BIAS, RSI, MACD) 
- Filter stocks based on technical indicators and financial metrics
- Calculate portfolio performance metrics and return on investment
- Financial metrics filtering (毛利率/Gross Profit Margin, 净资产收益率/Return on Equity, 研发比率/R&D Ratio)
- Store filtered results in PostgreSQL and Redis
- RESTful API for accessing filtered stocks

## Technical Stack

- **Backend**: Python
- **Database**: PostgreSQL, Redis
- **Data Source**: Yahoo Finance (via yfinance)
- **API Framework**: FastAPI

## Getting Started

### Prerequisites

- Python 3.8 or higher
- PostgreSQL 12 or higher
- Redis 6.0 or higher

### Installation and Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/stock-screener.git
   cd stock-screener
   ```

2. Set up PostgreSQL and Redis (see [Database Setup](README_DB_SETUP.md) for detailed instructions):
   ```bash
   # For WSL users
   sudo apt update
   sudo apt install postgresql postgresql-contrib redis-server
   sudo service postgresql start
   sudo service redis-server start
   ```

3. Run the database setup script:
   ```bash
   ./setup_db.sh
   ```

4. Start the application:
   ```bash
   python run.py
   ```

5. Access the API at http://localhost:8000

For detailed setup instructions, especially for WSL users, see [Database Setup](README_DB_SETUP.md).

## Configuration

The application configuration is stored in `config/config.yaml`. You can modify this file to adjust:

- Database connection parameters
- API settings
- Data fetching parameters
- Technical indicator parameters
- Financial metrics thresholds:
  - `gross_margin_threshold`: Minimum acceptable 毛利率/gross profit margin (default: 0.3 or 30%)
  - `roe_threshold`: Minimum acceptable 净资产收益率/return on equity (default: 0.15 or 15%)
  - `rd_ratio_threshold`: Minimum acceptable 研发比率/R&D to revenue ratio (default: 0.1 or 10%)
  - `enable_financial_filtering`: Enable/disable financial metrics filtering

## Usage

### API Endpoints
All endpoints are prefixed with `/api` and return a standardized response format:

```json
{
  "success": true,
  "message": "Success message",
  "data": {
    // Response data
  }
}
```

- `POST /api/trigger_fetch_filtering`: Trigger fetching and filtering of stocks
  - Fetches stock data if not already in Redis
  - Calculates indicators for each stock
  - Filters stocks based on indicators and financial metrics
  - Stores filtered results in Redis
  - Request body:
    ```json
    {
      "symbols": ["AAPL", "MSFT"] or ["all"],
      "timeFrame": ["daily", "weekly", "monthly"],
      "financialFilters": {
        "gross_margin_threshold": 0.3,
        "roe_threshold": 0.15,
        "rd_ratio_threshold": 0.1
      }
    }
    ```

- `POST /api/retrieve_filtered_stocks`: Retrieve filtered stocks from Redis
  - Scans Redis for filtered stocks
  - Filters by time frame
  - Returns filtered stocks
  - Request body:
    ```json
    {
      "timeFrame": ["daily", "weekly", "monthly"],
      "recentDay": 1
    }
    ```
  - Response body (with "daily", "weekly" must to meet):
    <details>
    <summary>Collapse for the filtered stocks </summary>
    ```json
      {
      "success": true,
      "message": "Successfully retrieved 88 filtered stocks",
      "data": {
         "filtered_stocks": {
            "PUBM": {
            "metaData": {
               "stock": "PUBM",
               "filterTime": "2025-03-12T14:32:49.035766"
            },
            "daily": {
               "BIAS": {
                  "bias": -15.794040576424631
               },
               "RSI": {
                  "value": 18.564055122174523,
                  "period": 14
               },
               "MACD": {
                  "value": -1.5234014344971847,
                  "signal": -1.090363937702842,
                  "histogram": -0.43303749679434267,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               },
               "FinancialMetrics": {
                  "gross_margin": 0.45,
                  "roe": 0.22,
                  "rd_ratio": 0.15,
                  "thresholds": {
                    "gross_margin": 0.3,
                    "roe": 0.15,
                    "rd_ratio": 0.1
                  }
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -27.599479497090577
               },
               "RSI": {
                  "value": 28.62853198352002,
                  "period": 14
               },
               "MACD": {
                  "value": -1.3868694305196243,
                  "signal": -0.8667288557902623,
                  "histogram": -0.520140574729362,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               },
               "FinancialMetrics": {
                  "gross_margin": 0.45,
                  "roe": 0.22,
                  "rd_ratio": 0.15,
                  "thresholds": {
                    "gross_margin": 0.3,
                    "roe": 0.15,
                    "rd_ratio": 0.1
                  }
               }
            }
            }
         }
      }
      }
    ```
    </details>

- `POST /api/fetch_stock_history`: Fetch stock history for specified symbols
  - Fetches stock history for specified symbols
  - Stores in database
  - Request body:
    ```json
    {
      "symbols": ["AAPL", "MSFT"] or ["all"],
      "timeRange": {
        "start": "2023-01-01",
        "end": "2023-12-31"
      }
    }
    ```

- `POST /api/performance_retreat`: Calculate performance metrics for a portfolio of stocks
  - Calculates the performance of each stock in the portfolio from start_date to end_date
  - Calculates the total portfolio performance
  - Returns detailed performance metrics
  - Request body:(take some stocks that met the 3 BIAS strategy, 5 stocks among the 21 stock screened on 13-03-2025)
    ```json
        {
          "stocks": [
            {
              "symbol": "ACHC",
              "percentage": 20
            },
            {
              "symbol": "COO",
              "percentage": 20
            },
            {
              "symbol": "ELTK",
              "percentage": 20
            },
            {
              "symbol": "IMXI",
              "percentage": 20
            },
            {
              "symbol": "SGC",
              "percentage": 20
            }
          ],
          "total_money": 10000,
          "start_date": "2025-03-13",
          "end_date": "2025-03-19"
        }
    ```
  - Response body:
    ```json
        {
          "success": true,
          "message": "Successfully calculated portfolio performance",
          "data": {
            "start_date": "2025-03-13",
            "end_date": "2025-03-19",
            "initial_total_value": 10000,
            "final_total_value": 10124.697070683062,
            "total_gain_loss": 124.69707068306161,
            "total_gain_loss_percentage": 1.2469707068306162,
            "stock_performances": [
              {
                "symbol": "ACHC",
                "shares": 69.90562591167397,
                "initial_price": 28.610000610351562,
                "final_price": 29.25,
                "initial_value": 2000.0000000000002,
                "final_value": 2044.7395579164636,
                "gain_loss": 44.739557916463355,
                "gain_loss_percentage": 2.2369778958231676,
                "contribution_percentage": 35.87859576122393
              },
              {
                "symbol": "COO",
                "shares": 25.645957355221515,
                "initial_price": 77.98500061035156,
                "final_price": 79.81999969482422,
                "initial_value": 2000,
                "final_value": 2047.0603082672562,
                "gain_loss": 47.06030826725623,
                "gain_loss_percentage": 2.3530154133628116,
                "contribution_percentage": 37.73970632146432
              },
              {
                "symbol": "ELTK",
                "shares": 241.4001251460152,
                "initial_price": 8.28499984741211,
                "final_price": 8.619999885559082,
                "initial_value": 2000,
                "final_value": 2080.869051132599,
                "gain_loss": 80.869051132599,
                "gain_loss_percentage": 4.0434525566299495,
                "contribution_percentage": 64.85240646762358
              },
              {
                "symbol": "IMXI",
                "shares": 153.0807494252315,
                "initial_price": 13.065000057220459,
                "final_price": 13.069999694824219,
                "initial_value": 2000.0000000000002,
                "final_value": 2000.7653482712383,
                "gain_loss": 0.7653482712380537,
                "gain_loss_percentage": 0.03826741356190268,
                "contribution_percentage": 0.6137660388056059
              },
              {
                "symbol": "SGC",
                "shares": 177.22640913093522,
                "initial_price": 11.28499984741211,
                "final_price": 11.010000228881836,
                "initial_value": 2000,
                "final_value": 1951.2628050955027,
                "gain_loss": -48.7371949044973,
                "gain_loss_percentage": -2.436859745224865,
                "contribution_percentage": -39.08447458911926
              }
            ],
            "detailed_performances": [
              {
                "symbol": "ACHC",
                "shares": 69.90562591167397,
                "initial_price": 28.610000610351562,
                "final_price": 29.25,
                "initial_value": 2000.0000000000002,
                "final_value": 2044.7395579164636,
                "gain_loss": 44.739557916463355,
                "gain_loss_percentage": 2.2369778958231676,
                "contribution_percentage": 35.87859576122393,
                "daily_performance": [
                  {
                    "date": "2025-03-13",
                    "price": 28.8700008392334,
                    "value": 2018.1754787371633,
                    "gain_loss": 18.175478737163075,
                    "gain_loss_percentage": 0.9087739368581536
                  },
                  {
                    "date": "2025-03-14",
                    "price": 28.329999923706055,
                    "value": 1980.4263767443474,
                    "gain_loss": -19.57362325565282,
                    "gain_loss_percentage": -0.9786811627826408
                  },
                  {
                    "date": "2025-03-17",
                    "price": 28.549999237060547,
                    "value": 1995.8055664445317,
                    "gain_loss": -4.1944335554685495,
                    "gain_loss_percentage": -0.20972167777342743
                  },
                  {
                    "date": "2025-03-18",
                    "price": 29.25,
                    "value": 2044.7395579164636,
                    "gain_loss": 44.739557916463355,
                    "gain_loss_percentage": 2.2369778958231676
                  }
                ]
              },
              {
                "symbol": "COO",
                "shares": 25.645957355221515,
                "initial_price": 77.98500061035156,
                "final_price": 79.81999969482422,
                "initial_value": 2000,
                "final_value": 2047.0603082672562,
                "gain_loss": 47.06030826725623,
                "gain_loss_percentage": 2.3530154133628116,
                "contribution_percentage": 37.73970632146432,
                "daily_performance": [
                  {
                    "date": "2025-03-13",
                    "price": 78.91999816894531,
                    "value": 2023.9789075149315,
                    "gain_loss": 23.978907514931507,
                    "gain_loss_percentage": 1.1989453757465753
                  },
                  {
                    "date": "2025-03-14",
                    "price": 78.08000183105469,
                    "value": 2002.4363972548463,
                    "gain_loss": 2.43639725484627,
                    "gain_loss_percentage": 0.12181986274231349
                  },
                  {
                    "date": "2025-03-17",
                    "price": 81.26000213623047,
                    "value": 2083.990549470976,
                    "gain_loss": 83.99054947097602,
                    "gain_loss_percentage": 4.199527473548801
                  },
                  {
                    "date": "2025-03-18",
                    "price": 79.81999969482422,
                    "value": 2047.0603082672562,
                    "gain_loss": 47.06030826725623,
                    "gain_loss_percentage": 2.3530154133628116
                  }
                ]
              },
              {
                "symbol": "ELTK",
                "shares": 241.4001251460152,
                "initial_price": 8.28499984741211,
                "final_price": 8.619999885559082,
                "initial_value": 2000,
                "final_value": 2080.869051132599,
                "gain_loss": 80.869051132599,
                "gain_loss_percentage": 4.0434525566299495,
                "contribution_percentage": 64.85240646762358,
                "daily_performance": [
                  {
                    "date": "2025-03-13",
                    "price": 8.390000343322754,
                    "value": 2025.3471328532232,
                    "gain_loss": 25.34713285322323,
                    "gain_loss_percentage": 1.2673566426611615
                  },
                  {
                    "date": "2025-03-14",
                    "price": 8.520000457763672,
                    "value": 2056.729176748257,
                    "gain_loss": 56.72917674825703,
                    "gain_loss_percentage": 2.8364588374128514
                  },
                  {
                    "date": "2025-03-17",
                    "price": 8.380000114440918,
                    "value": 2022.9330763496594,
                    "gain_loss": 22.93307634965936,
                    "gain_loss_percentage": 1.1466538174829681
                  },
                  {
                    "date": "2025-03-18",
                    "price": 8.619999885559082,
                    "value": 2080.869051132599,
                    "gain_loss": 80.869051132599,
                    "gain_loss_percentage": 4.0434525566299495
                  }
                ]
              },
              {
                "symbol": "IMXI",
                "shares": 153.0807494252315,
                "initial_price": 13.065000057220459,
                "final_price": 13.069999694824219,
                "initial_value": 2000.0000000000002,
                "final_value": 2000.7653482712383,
                "gain_loss": 0.7653482712380537,
                "gain_loss_percentage": 0.03826741356190268,
                "contribution_percentage": 0.6137660388056059,
                "daily_performance": [
                  {
                    "date": "2025-03-13",
                    "price": 13,
                    "value": 1990.0497425280093,
                    "gain_loss": -9.95025747199088,
                    "gain_loss_percentage": -0.49751287359954394
                  },
                  {
                    "date": "2025-03-14",
                    "price": 12.970000267028809,
                    "value": 1985.4573609222225,
                    "gain_loss": -14.542639077777721,
                    "gain_loss_percentage": -0.727131953888886
                  },
                  {
                    "date": "2025-03-17",
                    "price": 13.220000267028809,
                    "value": 2023.7275482785303,
                    "gain_loss": 23.727548278530094,
                    "gain_loss_percentage": 1.1863774139265046
                  },
                  {
                    "date": "2025-03-18",
                    "price": 13.069999694824219,
                    "value": 2000.7653482712383,
                    "gain_loss": 0.7653482712380537,
                    "gain_loss_percentage": 0.03826741356190268
                  }
                ]
              },
              {
                "symbol": "SGC",
                "shares": 177.22640913093522,
                "initial_price": 11.28499984741211,
                "final_price": 11.010000228881836,
                "initial_value": 2000,
                "final_value": 1951.2628050955027,
                "gain_loss": -48.7371949044973,
                "gain_loss_percentage": -2.436859745224865,
                "contribution_percentage": -39.08447458911926,
                "daily_performance": [
                  {
                    "date": "2025-03-13",
                    "price": 11.430000305175781,
                    "value": 2025.6979104517975,
                    "gain_loss": 25.697910451797497,
                    "gain_loss_percentage": 1.2848955225898748
                  },
                  {
                    "date": "2025-03-14",
                    "price": 11.210000038146973,
                    "value": 1986.708053118435,
                    "gain_loss": -13.291946881565082,
                    "gain_loss_percentage": -0.6645973440782541
                  },
                  {
                    "date": "2025-03-17",
                    "price": 11.640000343322754,
                    "value": 2062.915463129945,
                    "gain_loss": 62.91546312994478,
                    "gain_loss_percentage": 3.1457731564972393
                  },
                  {
                    "date": "2025-03-18",
                    "price": 11.010000228881836,
                    "value": 1951.2628050955027,
                    "gain_loss": -48.7371949044973,
                    "gain_loss_percentage": -2.436859745224865
                  }
                ]
              }
            ]
          }
        }
    ```

### Example API Request

```bash
curl -X POST "http://localhost:8000/api/trigger_fetch_filtering" \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["all"], "timeFrame": ["daily", "weekly", "monthly"], "financialFilters": {"gross_margin_threshold": 0.3, "roe_threshold": 0.15, "rd_ratio_threshold": 0.1}}'

# Calculate portfolio performance
curl -X POST "http://localhost:8000/api/performance_retreat" \
  -H "Content-Type: application/json" \
  -d '{"stocks": [{"symbol": "AAPL", "percentage": 40}, {"symbol": "MSFT", "percentage": 30}, {"symbol": "GOOGL", "percentage": 30}], 
       "total_money": 10000, "start_date": "2024-01-01", "end_date": "2024-03-01"}'
```

## Project Structure

```
stock-screener/
├── config/
│   └── config.yaml         # Configuration file
├── src/
│   ├── api/                # API endpoints
│   ├── data/               # Data acquisition and storage
│   ├── filters/            # Stock filtering logic
│   ├── indicators/         # Technical indicators
│   └── utils/              # Utility functions
├── init_db.sql             # SQL initialization script
├── setup_db.sh             # Database setup script
├── run.py                  # Application entry point
└── README.md               # This file
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.