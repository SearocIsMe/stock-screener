# Stock Screener

A comprehensive stock screening application that filters stocks based on technical indicators.

## Features

- Fetch stock data from Yahoo Finance API
- Calculate technical indicators (BIAS, RSI, MACD)
- Filter stocks based on predefined criteria
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
  - Filters stocks based on indicators
  - Stores filtered results in Redis
  - Request body:
    ```json
    {
      "symbols": ["AAPL", "MSFT"] or ["all"],
      "timeFrame": ["daily", "weekly", "monthly"]
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
               }
            }
            },
            "CLMT": {
            "metaData": {
               "stock": "CLMT",
               "filterTime": "2025-03-12T14:27:28.476956"
            },
            "daily": {
               "BIAS": {
                  "bias": -18.045337398006883
               },
               "RSI": {
                  "value": 20.81484737266744,
                  "period": 14
               },
               "MACD": {
                  "value": -1.5649008396512443,
                  "signal": -1.247115410423398,
                  "histogram": -0.31778542922784636,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -32.904228274201216
               },
               "RSI": {
                  "value": 29.89185256095529,
                  "period": 14
               },
               "MACD": {
                  "value": -1.5201946108636832,
                  "signal": -0.3626201603579946,
                  "histogram": -1.1575744505056886,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "FA": {
            "metaData": {
               "stock": "FA",
               "filterTime": "2025-03-12T14:28:32.055930"
            },
            "daily": {
               "BIAS": {
                  "bias": -13.253770140920619
               },
               "RSI": {
                  "value": 18.394915535645644,
                  "period": 14
               },
               "MACD": {
                  "value": -1.549930631065953,
                  "signal": -1.0664911263925558,
                  "histogram": -0.48343950467339725,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -22.926687206474863
               },
               "RSI": {
                  "value": 29.21257249290332,
                  "period": 14
               },
               "MACD": {
                  "value": -0.7704095638601665,
                  "signal": -0.07480563495483954,
                  "histogram": -0.695603928905327,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "RDNT": {
            "metaData": {
               "stock": "RDNT",
               "filterTime": "2025-03-12T14:33:00.748682"
            },
            "daily": {
               "BIAS": {
                  "bias": -8.344716293569636
               },
               "RSI": {
                  "value": 28.343319324638507,
                  "period": 14
               },
               "MACD": {
                  "value": -4.151374471926999,
                  "signal": -3.4026025225564096,
                  "histogram": -0.7487719493705898,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -18.880021929137875
               },
               "RSI": {
                  "value": 29.87460906756613,
                  "period": 14
               },
               "MACD": {
                  "value": -3.146060203315656,
                  "signal": -0.20364438137167773,
                  "histogram": -2.942415821943978,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "RPAY": {
            "metaData": {
               "stock": "RPAY",
               "filterTime": "2025-03-12T14:33:15.621275"
            },
            "daily": {
               "BIAS": {
                  "bias": -10.898834983692598
               },
               "RSI": {
                  "value": 19.311555001440627,
                  "period": 14
               },
               "MACD": {
                  "value": -0.43026827625539266,
                  "signal": -0.28070788143283093,
                  "histogram": -0.14956039482256173,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -18.973403693843686
               },
               "RSI": {
                  "value": 25.07703797979943,
                  "period": 14
               },
               "MACD": {
                  "value": -0.5334502110785477,
                  "signal": -0.38556955003710675,
                  "histogram": -0.14788066104144099,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "MRVI": {
            "metaData": {
               "stock": "MRVI",
               "filterTime": "2025-03-12T14:31:19.979224"
            },
            "daily": {
               "BIAS": {
                  "bias": -15.831326056185823
               },
               "RSI": {
                  "value": 28.001892759382734,
                  "period": 14
               },
               "MACD": {
                  "value": -0.5422439159396486,
                  "signal": -0.5125714720628249,
                  "histogram": -0.029672443876823662,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -38.58363783652913
               },
               "RSI": {
                  "value": 29.54150547810141,
                  "period": 14
               },
               "MACD": {
                  "value": -1.0754286779290307,
                  "signal": -0.8834515096454797,
                  "histogram": -0.19197716828355105,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "EDUC": {
            "metaData": {
               "stock": "EDUC",
               "filterTime": "2025-03-12T14:28:15.610515"
            },
            "daily": {
               "BIAS": {
                  "bias": -9.705119548966264
               },
               "RSI": {
                  "value": 21.94914995854214,
                  "period": 14
               },
               "MACD": {
                  "value": -0.08311049545297466,
                  "signal": -0.06555320607324433,
                  "histogram": -0.017557289379730334,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -19.435911323585977
               },
               "RSI": {
                  "value": 28.208000895631596,
                  "period": 14
               },
               "MACD": {
                  "value": -0.14750104586928092,
                  "signal": -0.10401820136265835,
                  "histogram": -0.04348284450662257,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "TRUE": {
            "metaData": {
               "stock": "TRUE",
               "filterTime": "2025-03-12T14:34:36.330319"
            },
            "daily": {
               "BIAS": {
                  "bias": -13.366621755453313
               },
               "RSI": {
                  "value": 25.25781868731576,
                  "period": 14
               },
               "MACD": {
                  "value": -0.36255253849967906,
                  "signal": -0.33303732167122635,
                  "histogram": -0.029515216828452706,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -32.382274109434285
               },
               "RSI": {
                  "value": 24.533922251315058,
                  "period": 14
               },
               "MACD": {
                  "value": -0.3067442364121704,
                  "signal": -0.09178978337738065,
                  "histogram": -0.21495445303478977,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "IMXI": {
            "metaData": {
               "stock": "IMXI",
               "filterTime": "2025-03-12T14:29:56.960330"
            },
            "daily": {
               "BIAS": {
                  "bias": -11.807297308794112
               },
               "RSI": {
                  "value": 19.225536095392425,
                  "period": 14
               },
               "MACD": {
                  "value": -1.4412222121824154,
                  "signal": -1.1794905657725776,
                  "histogram": -0.2617316464098378,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -23.325454635354532
               },
               "RSI": {
                  "value": 25.23156366942792,
                  "period": 14
               },
               "MACD": {
                  "value": -1.17538015489448,
                  "signal": -0.4449560510227989,
                  "histogram": -0.7304241038716811,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "FNKO": {
            "metaData": {
               "stock": "FNKO",
               "filterTime": "2025-03-12T14:28:48.708264"
            },
            "daily": {
               "BIAS": {
                  "bias": -29.994257784959643
               },
               "RSI": {
                  "value": 12.18906040635588,
                  "period": 14
               },
               "MACD": {
                  "value": -1.2736409698007325,
                  "signal": -0.6795986057984182,
                  "histogram": -0.5940423640023142,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -36.58022785536241
               },
               "RSI": {
                  "value": 29.57650517792493,
                  "period": 14
               },
               "MACD": {
                  "value": -0.0015225953618607235,
                  "signal": 0.6589659127813681,
                  "histogram": -0.6604885081432288,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "PLTK": {
            "metaData": {
               "stock": "PLTK",
               "filterTime": "2025-03-12T14:32:34.787043"
            },
            "daily": {
               "BIAS": {
                  "bias": -14.25828681078391
               },
               "RSI": {
                  "value": 18.893676615986628,
                  "period": 14
               },
               "MACD": {
                  "value": -0.6253381655653856,
                  "signal": -0.47174999061893774,
                  "histogram": -0.15358817494644783,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -26.034366223786247
               },
               "RSI": {
                  "value": 25.480522141201078,
                  "period": 14
               },
               "MACD": {
                  "value": -0.5499030084793661,
                  "signal": -0.28006113618478584,
                  "histogram": -0.2698418722945803,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "SPWH": {
            "metaData": {
               "stock": "SPWH",
               "filterTime": "2025-03-12T14:33:58.436770"
            },
            "daily": {
               "BIAS": {
                  "bias": -16.895380265544667
               },
               "RSI": {
                  "value": 25.008462087623606,
                  "period": 14
               },
               "MACD": {
                  "value": -0.20548664600154742,
                  "signal": -0.19097142121255845,
                  "histogram": -0.014515224788988978,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -35.726777569455706
               },
               "RSI": {
                  "value": 29.982407236428593,
                  "period": 14
               },
               "MACD": {
                  "value": -0.33705685673544883,
                  "signal": -0.2473816216775454,
                  "histogram": -0.08967523505790342,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "ECPG": {
            "metaData": {
               "stock": "ECPG",
               "filterTime": "2025-03-12T14:28:14.179519"
            },
            "daily": {
               "BIAS": {
                  "bias": -13.465682078387905
               },
               "RSI": {
                  "value": 20.10614105470175,
                  "period": 14
               },
               "MACD": {
                  "value": -4.120410319760396,
                  "signal": -2.9149219996327345,
                  "histogram": -1.2054883201276612,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -23.584431692361637
               },
               "RSI": {
                  "value": 25.789904689793786,
                  "period": 14
               },
               "MACD": {
                  "value": -2.0050785374520643,
                  "signal": -0.34140223717714757,
                  "histogram": -1.6636763002749166,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "IOVA": {
            "metaData": {
               "stock": "IOVA",
               "filterTime": "2025-03-12T14:30:03.438424"
            },
            "daily": {
               "BIAS": {
                  "bias": -10.571035225213201
               },
               "RSI": {
                  "value": 26.83743449690067,
                  "period": 14
               },
               "MACD": {
                  "value": -0.6172195585061093,
                  "signal": -0.5304265557775316,
                  "histogram": -0.0867930027285777,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -32.20914350362406
               },
               "RSI": {
                  "value": 29.86371377814721,
                  "period": 14
               },
               "MACD": {
                  "value": -1.3719291242110057,
                  "signal": -1.0523512888368411,
                  "histogram": -0.3195778353741645,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "KBSX": {
            "metaData": {
               "stock": "KBSX",
               "filterTime": "2025-03-12T14:30:18.309226"
            },
            "daily": {
               "BIAS": {
                  "bias": -31.228438939444757
               },
               "RSI": {
                  "value": 25.685406820649582,
                  "period": 14
               },
               "MACD": {
                  "value": -0.7735603362476375,
                  "signal": -0.5930830067518037,
                  "histogram": -0.18047732949583384,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -44.85095099417609
               },
               "RSI": {
                  "value": 12.534055661482588,
                  "period": 14
               },
               "MACD": {
                  "value": -1.588226523459399,
                  "signal": -1.1305653455035227,
                  "histogram": -0.45766117795587635,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "TTD": {
            "metaData": {
               "stock": "TTD",
               "filterTime": "2025-03-12T14:34:38.230500"
            },
            "daily": {
               "BIAS": {
                  "bias": -15.705576942816094
               },
               "RSI": {
                  "value": 15.868306780675054,
                  "period": 14
               },
               "MACD": {
                  "value": -12.721675400581574,
                  "signal": -12.48618831977674,
                  "histogram": -0.23548708080483394,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -36.264036035969475
               },
               "RSI": {
                  "value": 23.08671118638411,
                  "period": 14
               },
               "MACD": {
                  "value": -10.25458775775789,
                  "signal": -1.8691237886839662,
                  "histogram": -8.385463969073923,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "TLRY": {
            "metaData": {
               "stock": "TLRY",
               "filterTime": "2025-03-12T14:34:28.189454"
            },
            "daily": {
               "BIAS": {
                  "bias": -16.82302601201994
               },
               "RSI": {
                  "value": 24.55265024488648,
                  "period": 14
               },
               "MACD": {
                  "value": -0.11140749081975265,
                  "signal": -0.10486664055086,
                  "histogram": -0.006540850268892659,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -38.36808874042997
               },
               "RSI": {
                  "value": 21.828697577470344,
                  "period": 14
               },
               "MACD": {
                  "value": -0.24180479011154188,
                  "signal": -0.1919894457853553,
                  "histogram": -0.04981534432618659,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "VRRM": {
            "metaData": {
               "stock": "VRRM",
               "filterTime": "2025-03-12T14:35:02.568616"
            },
            "daily": {
               "BIAS": {
                  "bias": -11.989578232563103
               },
               "RSI": {
                  "value": 14.521116577316807,
                  "period": 14
               },
               "MACD": {
                  "value": -1.3867067987433437,
                  "signal": -0.7801284231536874,
                  "histogram": -0.6065783755896563,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -16.626246057981405
               },
               "RSI": {
                  "value": 28.539968904552545,
                  "period": 14
               },
               "MACD": {
                  "value": -0.8077732361528902,
                  "signal": -0.3666636857514343,
                  "histogram": -0.4411095504014559,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "ELTK": {
            "metaData": {
               "stock": "ELTK",
               "filterTime": "2025-03-12T14:28:18.696306"
            },
            "daily": {
               "BIAS": {
                  "bias": -22.859687074644228
               },
               "RSI": {
                  "value": 18.250100658368282,
                  "period": 14
               },
               "MACD": {
                  "value": -0.23434872363854886,
                  "signal": -0.017921887361928127,
                  "histogram": -0.21642683627662074,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -22.19058016247384
               },
               "RSI": {
                  "value": 28.21473949077539,
                  "period": 14
               },
               "MACD": {
                  "value": -0.12752657817345536,
                  "signal": 0.005604501019848544,
                  "histogram": -0.13313107919330391,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "PESI": {
            "metaData": {
               "stock": "PESI",
               "filterTime": "2025-03-12T14:32:27.658573"
            },
            "daily": {
               "BIAS": {
                  "bias": -9.392288280372458
               },
               "RSI": {
                  "value": 22.809259164023583,
                  "period": 14
               },
               "MACD": {
                  "value": -0.7130300886270797,
                  "signal": -0.680654025945319,
                  "histogram": -0.03237606268176074,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -24.971372535213664
               },
               "RSI": {
                  "value": 29.22792774629255,
                  "period": 14
               },
               "MACD": {
                  "value": -1.047258696585681,
                  "signal": -0.5160165038819967,
                  "histogram": -0.5312421927036842,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "AMBC": {
            "metaData": {
               "stock": "AMBC",
               "filterTime": "2025-03-12T14:35:50.240023"
            },
            "daily": {
               "BIAS": {
                  "bias": -14.82615601319657
               },
               "RSI": {
                  "value": 20.387135767901647,
                  "period": 14
               },
               "MACD": {
                  "value": -0.7837161947158098,
                  "signal": -0.5353685238871311,
                  "histogram": -0.2483476708286787,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -23.219305891651867
               },
               "RSI": {
                  "value": 27.906816489211963,
                  "period": 14
               },
               "MACD": {
                  "value": -0.7536150852538022,
                  "signal": -0.4643664839889533,
                  "histogram": -0.28924860126484886,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "FGBI": {
            "metaData": {
               "stock": "FGBI",
               "filterTime": "2025-03-12T14:28:41.090719"
            },
            "daily": {
               "BIAS": {
                  "bias": -13.910997198736242
               },
               "RSI": {
                  "value": 14.831610087575035,
                  "period": 14
               },
               "MACD": {
                  "value": -0.8426624916262035,
                  "signal": -0.7048829373395505,
                  "histogram": -0.137779554286653,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -27.476007459974234
               },
               "RSI": {
                  "value": 25.941035564065437,
                  "period": 14
               },
               "MACD": {
                  "value": -0.7762931181772625,
                  "signal": -0.24228038408428618,
                  "histogram": -0.5340127340929763,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "TWIN": {
            "metaData": {
               "stock": "TWIN",
               "filterTime": "2025-03-12T14:34:40.628693"
            },
            "daily": {
               "BIAS": {
                  "bias": -8.540032204407018
               },
               "RSI": {
                  "value": 20.699783299512333,
                  "period": 14
               },
               "MACD": {
                  "value": -0.7484826831541476,
                  "signal": -0.7068483906046364,
                  "histogram": -0.04163429254951112,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -21.299623533324144
               },
               "RSI": {
                  "value": 25.495343967854886,
                  "period": 14
               },
               "MACD": {
                  "value": -1.1042142413542706,
                  "signal": -0.7796766029670156,
                  "histogram": -0.324537638387255,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "AMRC": {
            "metaData": {
               "stock": "AMRC",
               "filterTime": "2025-03-12T14:35:51.576447"
            },
            "daily": {
               "BIAS": {
                  "bias": -19.97694622450616
               },
               "RSI": {
                  "value": 25.254352415444785,
                  "period": 14
               },
               "MACD": {
                  "value": -3.1279977359869022,
                  "signal": -2.6620453870042784,
                  "histogram": -0.46595234898262383,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -44.896300007332826
               },
               "RSI": {
                  "value": 25.715082376282673,
                  "period": 14
               },
               "MACD": {
                  "value": -4.268801606590632,
                  "signal": -2.7621821617008804,
                  "histogram": -1.5066194448897514,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "RCKT": {
            "metaData": {
               "stock": "RCKT",
               "filterTime": "2025-03-12T14:32:58.815493"
            },
            "daily": {
               "BIAS": {
                  "bias": -10.134049003400788
               },
               "RSI": {
                  "value": 29.943727783002206,
                  "period": 14
               },
               "MACD": {
                  "value": -0.6068461055059888,
                  "signal": -0.5113217543701304,
                  "histogram": -0.09552435113585844,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -23.333634771042306
               },
               "RSI": {
                  "value": 24.713126985303106,
                  "period": 14
               },
               "MACD": {
                  "value": -2.523768157858406,
                  "signal": -2.5004715714826213,
                  "histogram": -0.023296586375784578,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "AEO": {
            "metaData": {
               "stock": "AEO",
               "filterTime": "2025-03-12T14:35:40.239988"
            },
            "daily": {
               "BIAS": {
                  "bias": -9.939705611774563
               },
               "RSI": {
                  "value": 26.410030953946457,
                  "period": 14
               },
               "MACD": {
                  "value": -0.9777949668584149,
                  "signal": -0.8996985695033017,
                  "histogram": -0.0780963973551132,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -22.538347135185333
               },
               "RSI": {
                  "value": 26.4920120547486,
                  "period": 14
               },
               "MACD": {
                  "value": -1.832763026169097,
                  "signal": -1.4046869659386858,
                  "histogram": -0.4280760602304112,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "EU": {
            "metaData": {
               "stock": "EU",
               "filterTime": "2025-03-12T14:28:26.703536"
            },
            "daily": {
               "BIAS": {
                  "bias": -22.555794404265615
               },
               "RSI": {
                  "value": 26.856471860276432,
                  "period": 14
               },
               "MACD": {
                  "value": -0.4272146739006428,
                  "signal": -0.35109274841744387,
                  "histogram": -0.07612192548319896,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -44.620885828964084
               },
               "RSI": {
                  "value": 23.85275452278934,
                  "period": 14
               },
               "MACD": {
                  "value": -0.4730058206041665,
                  "signal": -0.2861731292589794,
                  "histogram": -0.1868326913451871,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "MNY": {
            "metaData": {
               "stock": "MNY",
               "filterTime": "2025-03-12T14:31:15.741172"
            },
            "daily": {
               "BIAS": {
                  "bias": -9.9475557523687
               },
               "RSI": {
                  "value": 27.697661267182912,
                  "period": 14
               },
               "MACD": {
                  "value": -0.06281588286017004,
                  "signal": -0.05516714560127877,
                  "histogram": -0.007648737258891265,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -20.722269742679106
               },
               "RSI": {
                  "value": 27.605631782191757,
                  "period": 14
               },
               "MACD": {
                  "value": -0.12489400031389564,
                  "signal": -0.11285209901786737,
                  "histogram": -0.012041901296028265,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "NAUT": {
            "metaData": {
               "stock": "NAUT",
               "filterTime": "2025-03-12T14:31:27.572411"
            },
            "daily": {
               "BIAS": {
                  "bias": -11.850965716566924
               },
               "RSI": {
                  "value": 28.970877708992465,
                  "period": 14
               },
               "MACD": {
                  "value": -0.16310396900932211,
                  "signal": -0.14360407316683568,
                  "histogram": -0.01949989584248643,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -30.076688969340715
               },
               "RSI": {
                  "value": 26.84647695059965,
                  "period": 14
               },
               "MACD": {
                  "value": -0.32731322359571724,
                  "signal": -0.26640969737253706,
                  "histogram": -0.06090352622318018,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "DFLI": {
            "metaData": {
               "stock": "DFLI",
               "filterTime": "2025-03-12T14:27:59.227592"
            },
            "daily": {
               "BIAS": {
                  "bias": -28.73001067514854
               },
               "RSI": {
                  "value": 19.569416727199414,
                  "period": 14
               },
               "MACD": {
                  "value": -0.36468860285584914,
                  "signal": -0.295722199695677,
                  "histogram": -0.06896640316017216,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -53.47226893967313
               },
               "RSI": {
                  "value": 20.852969950855286,
                  "period": 14
               },
               "MACD": {
                  "value": -0.9881084525926882,
                  "signal": -0.8826292886724748,
                  "histogram": -0.10547916392021339,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "ALKT": {
            "metaData": {
               "stock": "ALKT",
               "filterTime": "2025-03-12T14:26:00.166190"
            },
            "daily": {
               "BIAS": {
                  "bias": -15.743359269509297
               },
               "RSI": {
                  "value": 18.582789519542768,
                  "period": 14
               },
               "MACD": {
                  "value": -2.396247635748807,
                  "signal": -1.8445459276534668,
                  "histogram": -0.5517017080953404,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -25.859496147005643
               },
               "RSI": {
                  "value": 26.975539252259367,
                  "period": 14
               },
               "MACD": {
                  "value": -1.298052112390863,
                  "signal": 0.3482056067613953,
                  "histogram": -1.6462577191522583,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "FTHM": {
            "metaData": {
               "stock": "FTHM",
               "filterTime": "2025-03-12T14:28:55.815392"
            },
            "daily": {
               "BIAS": {
                  "bias": -12.889878340062857
               },
               "RSI": {
                  "value": 27.340454991596744,
                  "period": 14
               },
               "MACD": {
                  "value": -0.14350130857285914,
                  "signal": -0.1259697312667214,
                  "histogram": -0.017531577306137747,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -36.38980880069973
               },
               "RSI": {
                  "value": 24.800784175555812,
                  "period": 14
               },
               "MACD": {
                  "value": -0.3591259910447504,
                  "signal": -0.29086243293612224,
                  "histogram": -0.06826355810862816,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "SBC": {
            "metaData": {
               "stock": "SBC",
               "filterTime": "2025-03-12T14:33:25.940115"
            },
            "daily": {
               "BIAS": {
                  "bias": -19.151153788770507
               },
               "RSI": {
                  "value": 26.642796329348858,
                  "period": 14
               },
               "MACD": {
                  "value": -0.43601395492020867,
                  "signal": -0.27661909126404505,
                  "histogram": -0.15939486365616362,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -32.45786791701471
               },
               "RSI": {
                  "value": 29.17915410196555,
                  "period": 14
               },
               "MACD": {
                  "value": -1.4509318671068723,
                  "signal": -1.4386884556472457,
                  "histogram": -0.012243411459626596,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "BGFV": {
            "metaData": {
               "stock": "BGFV",
               "filterTime": "2025-03-12T14:26:41.355274"
            },
            "daily": {
               "BIAS": {
                  "bias": -13.781233244799646
               },
               "RSI": {
                  "value": 19.434233613432784,
                  "period": 14
               },
               "MACD": {
                  "value": -0.14703433049482828,
                  "signal": -0.12792479073545632,
                  "histogram": -0.019109539759371963,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -30.66741353390882
               },
               "RSI": {
                  "value": 23.708912535475676,
                  "period": 14
               },
               "MACD": {
                  "value": -0.3213619521944826,
                  "signal": -0.30363593086441054,
                  "histogram": -0.01772602133007206,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "SCNX": {
            "metaData": {
               "stock": "SCNX",
               "filterTime": "2025-03-12T14:33:28.739073"
            },
            "daily": {
               "BIAS": {
                  "bias": -41.895865600349936
               },
               "RSI": {
                  "value": 18.967093148332847,
                  "period": 14
               },
               "MACD": {
                  "value": -0.6394546796350125,
                  "signal": -0.5828334818912303,
                  "histogram": -0.05662119774378216,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -65.9109098642466
               },
               "RSI": {
                  "value": 25.664391536757602,
                  "period": 14
               },
               "MACD": {
                  "value": -1.486985401692511,
                  "signal": -1.0598782405571163,
                  "histogram": -0.4271071611353947,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "OPAL": {
            "metaData": {
               "stock": "OPAL",
               "filterTime": "2025-03-12T14:32:06.387396"
            },
            "daily": {
               "BIAS": {
                  "bias": -8.604854397494721
               },
               "RSI": {
                  "value": 17.422698998657435,
                  "period": 14
               },
               "MACD": {
                  "value": -0.21891332877538616,
                  "signal": -0.17941875721103107,
                  "histogram": -0.039494571564355097,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -21.114874822188984
               },
               "RSI": {
                  "value": 27.346497590250618,
                  "period": 14
               },
               "MACD": {
                  "value": -0.3735380166865139,
                  "signal": -0.30129329047216646,
                  "histogram": -0.07224472621434741,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "GERN": {
            "metaData": {
               "stock": "GERN",
               "filterTime": "2025-03-12T14:29:06.848728"
            },
            "daily": {
               "BIAS": {
                  "bias": -14.764989638462087
               },
               "RSI": {
                  "value": 22.084167201958117,
                  "period": 14
               },
               "MACD": {
                  "value": -0.3519242704228218,
                  "signal": -0.32839935987811475,
                  "histogram": -0.023524910544707067,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -38.88909589795204
               },
               "RSI": {
                  "value": 22.946815302186724,
                  "period": 14
               },
               "MACD": {
                  "value": -0.5554131673609279,
                  "signal": -0.3618635407585942,
                  "histogram": -0.1935496266023337,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "MRIN": {
            "metaData": {
               "stock": "MRIN",
               "filterTime": "2025-03-12T14:31:18.786355"
            },
            "daily": {
               "BIAS": {
                  "bias": -14.546247269540629
               },
               "RSI": {
                  "value": 24.31147591424625,
                  "period": 14
               },
               "MACD": {
                  "value": -0.15383062342297005,
                  "signal": -0.11750009182205771,
                  "histogram": -0.03633053160091233,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -25.166520563835114
               },
               "RSI": {
                  "value": 29.33410091205103,
                  "period": 14
               },
               "MACD": {
                  "value": -0.15651936510174513,
                  "signal": -0.09310433050308337,
                  "histogram": -0.06341503459866177,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "LOT": {
            "metaData": {
               "stock": "LOT",
               "filterTime": "2025-03-12T14:30:46.767249"
            },
            "daily": {
               "BIAS": {
                  "bias": -22.621046295905458
               },
               "RSI": {
                  "value": 23.14314769967979,
                  "period": 14
               },
               "MACD": {
                  "value": -0.3575318616431782,
                  "signal": -0.3023868205559441,
                  "histogram": -0.05514504108723406,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -44.97956551236999
               },
               "RSI": {
                  "value": 21.546485541367975,
                  "period": 14
               },
               "MACD": {
                  "value": -0.9813187294270285,
                  "signal": -0.8964645155323117,
                  "histogram": -0.08485421389471681,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "CHR": {
            "metaData": {
               "stock": "CHR",
               "filterTime": "2025-03-12T14:27:23.188251"
            },
            "daily": {
               "BIAS": {
                  "bias": -17.088080926254932
               },
               "RSI": {
                  "value": 22.97560605280278,
                  "period": 14
               },
               "MACD": {
                  "value": -0.23750718939400817,
                  "signal": -0.17455110267857676,
                  "histogram": -0.0629560867154314,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -29.775113914453
               },
               "RSI": {
                  "value": 29.98532534303519,
                  "period": 14
               },
               "MACD": {
                  "value": -0.18953933325932848,
                  "signal": -0.09269918786249581,
                  "histogram": -0.09684014539683267,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "CGC": {
            "metaData": {
               "stock": "CGC",
               "filterTime": "2025-03-12T14:27:20.162773"
            },
            "daily": {
               "BIAS": {
                  "bias": -17.322783632182517
               },
               "RSI": {
                  "value": 22.996722628451867,
                  "period": 14
               },
               "MACD": {
                  "value": -0.28076899661318855,
                  "signal": -0.26984614656897743,
                  "histogram": -0.010922850044211119,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -46.93155552003761
               },
               "RSI": {
                  "value": 24.712644889225434,
                  "period": 14
               },
               "MACD": {
                  "value": -1.0142982188292322,
                  "signal": -0.949528304517838,
                  "histogram": -0.06476991431139423,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "LESL": {
            "metaData": {
               "stock": "LESL",
               "filterTime": "2025-03-12T14:30:36.675443"
            },
            "daily": {
               "BIAS": {
                  "bias": -17.10836094946583
               },
               "RSI": {
                  "value": 24.741771862767585,
                  "period": 14
               },
               "MACD": {
                  "value": -0.2606328791711676,
                  "signal": -0.2594315995781523,
                  "histogram": -0.001201279593015303,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -44.71790666307919
               },
               "RSI": {
                  "value": 19.788663752033333,
                  "period": 14
               },
               "MACD": {
                  "value": -0.6056559021599681,
                  "signal": -0.5391240963770749,
                  "histogram": -0.0665318057828932,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "ARVN": {
            "metaData": {
               "stock": "ARVN",
               "filterTime": "2025-03-12T14:26:17.222659"
            },
            "daily": {
               "BIAS": {
                  "bias": -49.01139434425801
               },
               "RSI": {
                  "value": 21.428345351516857,
                  "period": 14
               },
               "MACD": {
                  "value": -0.9812621355902031,
                  "signal": -0.47705646195951235,
                  "histogram": -0.5042056736306908,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -53.217444457535265
               },
               "RSI": {
                  "value": 23.20597244637259,
                  "period": 14
               },
               "MACD": {
                  "value": -3.1460928880015224,
                  "signal": -2.6266571210008935,
                  "histogram": -0.5194357670006289,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "AMPY": {
            "metaData": {
               "stock": "AMPY",
               "filterTime": "2025-03-12T14:35:51.342192"
            },
            "daily": {
               "BIAS": {
                  "bias": -8.815259689666734
               },
               "RSI": {
                  "value": 26.431209731529904,
                  "period": 14
               },
               "MACD": {
                  "value": -0.40239824537913726,
                  "signal": -0.32060572557098627,
                  "histogram": -0.081792519808151,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -21.61947238114198
               },
               "RSI": {
                  "value": 29.077353666437492,
                  "period": 14
               },
               "MACD": {
                  "value": -0.5800501811031058,
                  "signal": -0.3754687260168858,
                  "histogram": -0.20458145508622,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "NAII": {
            "metaData": {
               "stock": "NAII",
               "filterTime": "2025-03-12T14:31:26.586371"
            },
            "daily": {
               "BIAS": {
                  "bias": -14.617424152899211
               },
               "RSI": {
                  "value": 24.269613376703198,
                  "period": 14
               },
               "MACD": {
                  "value": -0.150181336848779,
                  "signal": -0.09572269260726472,
                  "histogram": -0.05445864424151427,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -19.555737970488526
               },
               "RSI": {
                  "value": 26.58131960277918,
                  "period": 14
               },
               "MACD": {
                  "value": -0.4163981749344563,
                  "signal": -0.39263353008277596,
                  "histogram": -0.02376464485168034,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "FTRE": {
            "metaData": {
               "stock": "FTRE",
               "filterTime": "2025-03-12T14:28:56.128872"
            },
            "daily": {
               "BIAS": {
                  "bias": -16.23219116065244
               },
               "RSI": {
                  "value": 21.210283872295886,
                  "period": 14
               },
               "MACD": {
                  "value": -1.6826508809067384,
                  "signal": -1.3783983155495774,
                  "histogram": -0.30425256535716105,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -33.876249594771096
               },
               "RSI": {
                  "value": 25.001971275119512,
                  "period": 14
               },
               "MACD": {
                  "value": -2.884685035569012,
                  "signal": -2.309531838615622,
                  "histogram": -0.5751531969533898,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "BIAF": {
            "metaData": {
               "stock": "BIAF",
               "filterTime": "2025-03-12T14:26:43.093505"
            },
            "daily": {
               "BIAS": {
                  "bias": -25.39567687654803
               },
               "RSI": {
                  "value": 25.41724293756954,
                  "period": 14
               },
               "MACD": {
                  "value": -0.12162458908647295,
                  "signal": -0.09647637365767428,
                  "histogram": -0.025148215428798665,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -51.460356779281724
               },
               "RSI": {
                  "value": 27.919897350389046,
                  "period": 14
               },
               "MACD": {
                  "value": -0.30174718568544334,
                  "signal": -0.275387208623636,
                  "histogram": -0.026359977061807316,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "GPRO": {
            "metaData": {
               "stock": "GPRO",
               "filterTime": "2025-03-12T14:29:18.766534"
            },
            "daily": {
               "BIAS": {
                  "bias": -11.106649448642562
               },
               "RSI": {
                  "value": 28.466087558716964,
                  "period": 14
               },
               "MACD": {
                  "value": -0.07256257112771036,
                  "signal": -0.07172630687966955,
                  "histogram": -0.0008362642480408133,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -26.982627045136514
               },
               "RSI": {
                  "value": 22.662895617076803,
                  "period": 14
               },
               "MACD": {
                  "value": -0.20053620826300744,
                  "signal": -0.18069449061530093,
                  "histogram": -0.019841717647706508,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "YTRA": {
            "metaData": {
               "stock": "YTRA",
               "filterTime": "2025-03-12T14:35:28.583079"
            },
            "daily": {
               "BIAS": {
                  "bias": -14.93039276870332
               },
               "RSI": {
                  "value": 19.473831171593382,
                  "period": 14
               },
               "MACD": {
                  "value": -0.0723953112038781,
                  "signal": -0.059291340282991996,
                  "histogram": -0.013103970920886103,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -26.17684493296814
               },
               "RSI": {
                  "value": 24.660093736912092,
                  "period": 14
               },
               "MACD": {
                  "value": -0.14111742895009116,
                  "signal": -0.09753084144153094,
                  "histogram": -0.04358658750856022,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "FTDR": {
            "metaData": {
               "stock": "FTDR",
               "filterTime": "2025-03-12T14:28:55.345584"
            },
            "daily": {
               "BIAS": {
                  "bias": -15.564311210708432
               },
               "RSI": {
                  "value": 17.018060999476162,
                  "period": 14
               },
               "MACD": {
                  "value": -5.262164625488765,
                  "signal": -3.700676961173041,
                  "histogram": -1.5614876643157243,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -25.592956236806703
               },
               "RSI": {
                  "value": 29.13649494140266,
                  "period": 14
               },
               "MACD": {
                  "value": -0.3793374910469183,
                  "signal": 2.4301569111621264,
                  "histogram": -2.8094944022090447,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "SHOO": {
            "metaData": {
               "stock": "SHOO",
               "filterTime": "2025-03-12T14:33:38.109902"
            },
            "daily": {
               "BIAS": {
                  "bias": -14.454523207552636
               },
               "RSI": {
                  "value": 15.015392624630476,
                  "period": 14
               },
               "MACD": {
                  "value": -3.1672489212399952,
                  "signal": -2.436994540915278,
                  "histogram": -0.7302543803247175,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -26.7353795883487
               },
               "RSI": {
                  "value": 21.259426449578594,
                  "period": 14
               },
               "MACD": {
                  "value": -3.227660408414714,
                  "signal": -1.6074910576742614,
                  "histogram": -1.6201693507404524,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "NEHC": {
            "metaData": {
               "stock": "NEHC",
               "filterTime": "2025-03-12T14:31:31.289478"
            },
            "daily": {
               "BIAS": {
                  "bias": -29.022863211553428
               },
               "RSI": {
                  "value": 26.0542953419745,
                  "period": 14
               },
               "MACD": {
                  "value": -0.408741811324389,
                  "signal": -0.35879004557000366,
                  "histogram": -0.04995176575438537,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -57.92175338685311
               },
               "RSI": {
                  "value": 17.7278920563923,
                  "period": 14
               },
               "MACD": {
                  "value": -2.260483113595692,
                  "signal": -2.0762124528689947,
                  "histogram": -0.1842706607266975,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "BTOC": {
            "metaData": {
               "stock": "BTOC",
               "filterTime": "2025-03-12T14:26:59.215562"
            },
            "daily": {
               "BIAS": {
                  "bias": -27.116050240145757
               },
               "RSI": {
                  "value": 23.600644686217635,
                  "period": 14
               },
               "MACD": {
                  "value": -0.6156261207708973,
                  "signal": -0.557951266457383,
                  "histogram": -0.05767485431351427,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -54.7155635016473
               },
               "RSI": {
                  "value": 28.640049526157572,
                  "period": 14
               },
               "MACD": {
                  "value": -0.744090553938503,
                  "signal": -0.35754601430034627,
                  "histogram": -0.3865445396381567,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "ADV": {
            "metaData": {
               "stock": "ADV",
               "filterTime": "2025-03-12T14:25:47.496875"
            },
            "daily": {
               "BIAS": {
                  "bias": -28.1635531498868
               },
               "RSI": {
                  "value": 20.028956053768486,
                  "period": 14
               },
               "MACD": {
                  "value": -0.19849501511643375,
                  "signal": -0.11820086250957665,
                  "histogram": -0.0802941526068571,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -36.651714043100526
               },
               "RSI": {
                  "value": 26.84408672031475,
                  "period": 14
               },
               "MACD": {
                  "value": -0.3458239433055974,
                  "signal": -0.24786921919412191,
                  "histogram": -0.09795472411147549,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "ILAG": {
            "metaData": {
               "stock": "ILAG",
               "filterTime": "2025-03-12T14:29:53.218727"
            },
            "daily": {
               "BIAS": {
                  "bias": -20.77084651665856
               },
               "RSI": {
                  "value": 24.153990818543644,
                  "period": 14
               },
               "MACD": {
                  "value": -0.09616250558036787,
                  "signal": -0.077605990327436,
                  "histogram": -0.01855651525293188,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -38.12705529781997
               },
               "RSI": {
                  "value": 29.22446188702221,
                  "period": 14
               },
               "MACD": {
                  "value": -0.07903644385535225,
                  "signal": -0.021987414102288813,
                  "histogram": -0.05704902975306343,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "ACHC": {
            "metaData": {
               "stock": "ACHC",
               "filterTime": "2025-03-12T14:25:42.202574"
            },
            "daily": {
               "BIAS": {
                  "bias": -12.249877389091445
               },
               "RSI": {
                  "value": 25.186942782708275,
                  "period": 14
               },
               "MACD": {
                  "value": -3.555468083874459,
                  "signal": -2.717748923946413,
                  "histogram": -0.8377191599280458,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -24.129788115273676
               },
               "RSI": {
                  "value": 25.657551601978927,
                  "period": 14
               },
               "MACD": {
                  "value": -6.929812974646637,
                  "signal": -6.549336377814283,
                  "histogram": -0.380476596832354,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "UEIC": {
            "metaData": {
               "stock": "UEIC",
               "filterTime": "2025-03-12T14:34:43.131468"
            },
            "daily": {
               "BIAS": {
                  "bias": -10.464370661644283
               },
               "RSI": {
                  "value": 25.120195017826333,
                  "period": 14
               },
               "MACD": {
                  "value": -0.7796683229599406,
                  "signal": -0.689479558382429,
                  "histogram": -0.09018876457751157,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -23.152349654450312
               },
               "RSI": {
                  "value": 29.30498048539969,
                  "period": 14
               },
               "MACD": {
                  "value": -0.6038178197695707,
                  "signal": -0.18841916735258232,
                  "histogram": -0.41539865241698837,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "MODV": {
            "metaData": {
               "stock": "MODV",
               "filterTime": "2025-03-12T14:31:16.604195"
            },
            "daily": {
               "BIAS": {
                  "bias": -31.501155065546605
               },
               "RSI": {
                  "value": 27.20469554131738,
                  "period": 14
               },
               "MACD": {
                  "value": -1.0336994335264045,
                  "signal": -0.9640471981899805,
                  "histogram": -0.06965223533642395,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -63.00508412418618
               },
               "RSI": {
                  "value": 27.67353133983271,
                  "period": 14
               },
               "MACD": {
                  "value": -4.800242160774328,
                  "signal": -4.543484915268648,
                  "histogram": -0.25675724550568013,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "ACVA": {
            "metaData": {
               "stock": "ACVA",
               "filterTime": "2025-03-12T14:25:45.123092"
            },
            "daily": {
               "BIAS": {
                  "bias": -11.328939184964739
               },
               "RSI": {
                  "value": 23.072866860579026,
                  "period": 14
               },
               "MACD": {
                  "value": -1.8876270641641923,
                  "signal": -1.5532017417396278,
                  "histogram": -0.3344253224245646,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -24.85562462966046
               },
               "RSI": {
                  "value": 29.673101060332055,
                  "period": 14
               },
               "MACD": {
                  "value": -0.8058035842157132,
                  "signal": 0.17284265779966096,
                  "histogram": -0.9786462420153741,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "FWRD": {
            "metaData": {
               "stock": "FWRD",
               "filterTime": "2025-03-12T14:28:58.986187"
            },
            "daily": {
               "BIAS": {
                  "bias": -22.545613922536457
               },
               "RSI": {
                  "value": 13.03250902222414,
                  "period": 14
               },
               "MACD": {
                  "value": -3.4441367758145383,
                  "signal": -2.669154927099651,
                  "histogram": -0.7749818487148872,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -36.6326545273216
               },
               "RSI": {
                  "value": 26.705849789312374,
                  "period": 14
               },
               "MACD": {
                  "value": -2.7115116276611637,
                  "signal": -1.03316356349526,
                  "histogram": -1.6783480641659037,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "EKSO": {
            "metaData": {
               "stock": "EKSO",
               "filterTime": "2025-03-12T14:28:17.458925"
            },
            "daily": {
               "BIAS": {
                  "bias": -15.942721996475631
               },
               "RSI": {
                  "value": 29.37892777114328,
                  "period": 14
               },
               "MACD": {
                  "value": -0.05725047391758342,
                  "signal": -0.043017314993208315,
                  "histogram": -0.014233158924375107,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -33.04277419304869
               },
               "RSI": {
                  "value": 28.522279744557945,
                  "period": 14
               },
               "MACD": {
                  "value": -0.1597845377339262,
                  "signal": -0.15270442243643975,
                  "histogram": -0.00708011529748645,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "XPEL": {
            "metaData": {
               "stock": "XPEL",
               "filterTime": "2025-03-12T14:35:23.564237"
            },
            "daily": {
               "BIAS": {
                  "bias": -8.407883985304835
               },
               "RSI": {
                  "value": 27.460829383327784,
                  "period": 14
               },
               "MACD": {
                  "value": -3.1648174402068108,
                  "signal": -2.4931834696693533,
                  "histogram": -0.6716339705374574,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -20.02695645392627
               },
               "RSI": {
                  "value": 29.54055658676373,
                  "period": 14
               },
               "MACD": {
                  "value": -2.2020397833824035,
                  "signal": -0.9675043144011387,
                  "histogram": -1.2345354689812646,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "CREX": {
            "metaData": {
               "stock": "CREX",
               "filterTime": "2025-03-12T14:27:43.656205"
            },
            "daily": {
               "BIAS": {
                  "bias": -15.795263563236329
               },
               "RSI": {
                  "value": 27.896111717769607,
                  "period": 14
               },
               "MACD": {
                  "value": -0.21221013818999723,
                  "signal": -0.16103776239442022,
                  "histogram": -0.05117237579557701,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -31.032921344696714
               },
               "RSI": {
                  "value": 22.421444110736893,
                  "period": 14
               },
               "MACD": {
                  "value": -0.49409801829949007,
                  "signal": -0.40528824770495,
                  "histogram": -0.0888097705945401,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "DECK": {
            "metaData": {
               "stock": "DECK",
               "filterTime": "2025-03-12T14:24:14.781122"
            },
            "daily": {
               "BIAS": {
                  "bias": -11.069077621455714
               },
               "RSI": {
                  "value": 19.603890694804566,
                  "period": 14
               },
               "MACD": {
                  "value": -14.931129995611428,
                  "signal": -14.386943201494901,
                  "histogram": -0.544186794116527,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -25.19461100349899
               },
               "RSI": {
                  "value": 28.632440729000965,
                  "period": 14
               },
               "MACD": {
                  "value": -8.06342264671963,
                  "signal": 2.375033241369038,
                  "histogram": -10.438455888088669,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "IPWR": {
            "metaData": {
               "stock": "IPWR",
               "filterTime": "2025-03-12T14:30:04.682215"
            },
            "daily": {
               "BIAS": {
                  "bias": -12.2149263916461
               },
               "RSI": {
                  "value": 27.951464282278433,
                  "period": 14
               },
               "MACD": {
                  "value": -0.5280910148111522,
                  "signal": -0.459711827911613,
                  "histogram": -0.06837918689953915,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -24.676081441496258
               },
               "RSI": {
                  "value": 29.965575506633392,
                  "period": 14
               },
               "MACD": {
                  "value": -0.5470182918047515,
                  "signal": -0.32285336865498454,
                  "histogram": -0.22416492314976694,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "ASTL": {
            "metaData": {
               "stock": "ASTL",
               "filterTime": "2025-03-12T14:26:20.235751"
            },
            "daily": {
               "BIAS": {
                  "bias": -13.346203274853044
               },
               "RSI": {
                  "value": 28.570504541010365,
                  "period": 14
               },
               "MACD": {
                  "value": -0.6249481993730122,
                  "signal": -0.4981922906947702,
                  "histogram": -0.12675590867824194,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -26.34643305862069
               },
               "RSI": {
                  "value": 27.575569225580903,
                  "period": 14
               },
               "MACD": {
                  "value": -0.7267890992323593,
                  "signal": -0.32930258447398963,
                  "histogram": -0.3974865147583697,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "FRPT": {
            "metaData": {
               "stock": "FRPT",
               "filterTime": "2025-03-12T14:28:52.834425"
            },
            "daily": {
               "BIAS": {
                  "bias": -16.00665636080876
               },
               "RSI": {
                  "value": 21.991407801524954,
                  "period": 14
               },
               "MACD": {
                  "value": -14.340639013257388,
                  "signal": -12.923551605386841,
                  "histogram": -1.4170874078705467,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -32.100866962043916
               },
               "RSI": {
                  "value": 27.697874770714776,
                  "period": 14
               },
               "MACD": {
                  "value": -8.35869954078575,
                  "signal": -0.00878010155408071,
                  "histogram": -8.34991943923167,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "DCBO": {
            "metaData": {
               "stock": "DCBO",
               "filterTime": "2025-03-12T14:27:57.485391"
            },
            "daily": {
               "BIAS": {
                  "bias": -11.644135832523684
               },
               "RSI": {
                  "value": 23.080770831289023,
                  "period": 14
               },
               "MACD": {
                  "value": -3.269615201630785,
                  "signal": -2.5926316131248592,
                  "histogram": -0.6769835885059257,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -23.105169078760355
               },
               "RSI": {
                  "value": 25.98730158076297,
                  "period": 14
               },
               "MACD": {
                  "value": -2.9426260839352167,
                  "signal": -1.1093130357214043,
                  "histogram": -1.8333130482138125,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "AREB": {
            "metaData": {
               "stock": "AREB",
               "filterTime": "2025-03-12T14:26:14.396506"
            },
            "daily": {
               "BIAS": {
                  "bias": -44.76531636563683
               },
               "RSI": {
                  "value": 17.072126318271085,
                  "period": 14
               },
               "MACD": {
                  "value": -0.2822229119319666,
                  "signal": -0.270517784806185,
                  "histogram": -0.01170512712578159,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -74.63748167645487
               },
               "RSI": {
                  "value": 27.941742412623505,
                  "period": 14
               },
               "MACD": {
                  "value": -0.7181707839422942,
                  "signal": -0.6191484980268648,
                  "histogram": -0.09902228591542939,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "LVLU": {
            "metaData": {
               "stock": "LVLU",
               "filterTime": "2025-03-12T14:30:53.306996"
            },
            "daily": {
               "BIAS": {
                  "bias": -20.589752630848768
               },
               "RSI": {
                  "value": 13.23153646864258,
                  "period": 14
               },
               "MACD": {
                  "value": -0.09855013927158873,
                  "signal": -0.07831276657386113,
                  "histogram": -0.0202373726977276,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -39.769241768189985
               },
               "RSI": {
                  "value": 21.580921201424005,
                  "period": 14
               },
               "MACD": {
                  "value": -0.2315797043875244,
                  "signal": -0.19197272722735564,
                  "histogram": -0.039606977160168755,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "AGMH": {
            "metaData": {
               "stock": "AGMH",
               "filterTime": "2025-03-12T14:25:51.940894"
            },
            "daily": {
               "BIAS": {
                  "bias": -55.39130886277724
               },
               "RSI": {
                  "value": 22.043999130045908,
                  "period": 14
               },
               "MACD": {
                  "value": -0.23709971174306627,
                  "signal": -0.2212301171529345,
                  "histogram": -0.015869594590131764,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -82.74567461675467
               },
               "RSI": {
                  "value": 23.08586791721631,
                  "period": 14
               },
               "MACD": {
                  "value": -0.29320868025378843,
                  "signal": -0.14127716782396804,
                  "histogram": -0.1519315124298204,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "FLYW": {
            "metaData": {
               "stock": "FLYW",
               "filterTime": "2025-03-12T14:28:47.097849"
            },
            "daily": {
               "BIAS": {
                  "bias": -19.319636394098563
               },
               "RSI": {
                  "value": 19.32510520984335,
                  "period": 14
               },
               "MACD": {
                  "value": -2.6068644758356427,
                  "signal": -2.1523570922884034,
                  "histogram": -0.4545073835472393,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -38.928582038943645
               },
               "RSI": {
                  "value": 26.37276180288,
                  "period": 14
               },
               "MACD": {
                  "value": -1.6729065106710497,
                  "signal": -0.48941693715706286,
                  "histogram": -1.1834895735139868,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "PYXS": {
            "metaData": {
               "stock": "PYXS",
               "filterTime": "2025-03-12T14:32:50.827565"
            },
            "daily": {
               "BIAS": {
                  "bias": -10.732135810028472
               },
               "RSI": {
                  "value": 28.521036725356264,
                  "period": 14
               },
               "MACD": {
                  "value": -0.105762279798856,
                  "signal": -0.10523972437179571,
                  "histogram": -0.0005225554270602839,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -31.92501373443733
               },
               "RSI": {
                  "value": 29.447736067059537,
                  "period": 14
               },
               "MACD": {
                  "value": -0.5555918257986814,
                  "signal": -0.5259755785798543,
                  "histogram": -0.029616247218827052,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "ASBP": {
            "metaData": {
               "stock": "ASBP",
               "filterTime": "2025-03-12T14:26:17.506398"
            },
            "daily": {
               "BIAS": {
                  "bias": -66.26346448283115
               },
               "RSI": {
                  "value": 19.801971624329568,
                  "period": 14
               },
               "MACD": {
                  "value": -2.657933747971281,
                  "signal": -2.5538318575051373,
                  "histogram": -0.10410189046614349,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -88.55021583695579
               },
               "RSI": {
                  "value": 11.909361635544201,
                  "period": 14
               },
               "MACD": {
                  "value": -2.306703652252459,
                  "signal": -1.0011263408219575,
                  "histogram": -1.3055773114305014,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "SGRP": {
            "metaData": {
               "stock": "SGRP",
               "filterTime": "2025-03-12T14:33:36.008023"
            },
            "daily": {
               "BIAS": {
                  "bias": -11.66855811477946
               },
               "RSI": {
                  "value": 12.300410473310404,
                  "period": 14
               },
               "MACD": {
                  "value": -0.1438985604703047,
                  "signal": -0.11432622326612533,
                  "histogram": -0.029572337204179358,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -23.991634224447477
               },
               "RSI": {
                  "value": 28.722630213601835,
                  "period": 14
               },
               "MACD": {
                  "value": -0.13424512999104476,
                  "signal": -0.05314208958289332,
                  "histogram": -0.08110304040815144,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "DNUT": {
            "metaData": {
               "stock": "DNUT",
               "filterTime": "2025-03-12T14:28:04.731840"
            },
            "daily": {
               "BIAS": {
                  "bias": -17.023877111973583
               },
               "RSI": {
                  "value": 24.67704174150746,
                  "period": 14
               },
               "MACD": {
                  "value": -0.8742869511722793,
                  "signal": -0.7260501866813659,
                  "histogram": -0.1482367644909134,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -33.253309293438456
               },
               "RSI": {
                  "value": 23.02460309664902,
                  "period": 14
               },
               "MACD": {
                  "value": -1.1943832058219446,
                  "signal": -0.8256432608825924,
                  "histogram": -0.36873994493935214,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "ANF": {
            "metaData": {
               "stock": "ANF",
               "filterTime": "2025-03-12T14:35:52.539406"
            },
            "daily": {
               "BIAS": {
                  "bias": -14.382147764457878
               },
               "RSI": {
                  "value": 21.821333326205245,
                  "period": 14
               },
               "MACD": {
                  "value": -10.357212772190849,
                  "signal": -8.906029634502161,
                  "histogram": -1.4511831376886875,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -30.91676342201551
               },
               "RSI": {
                  "value": 27.058585732006993,
                  "period": 14
               },
               "MACD": {
                  "value": -14.196715767083603,
                  "signal": -7.290447189126495,
                  "histogram": -6.906268577957108,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "BMBL": {
            "metaData": {
               "stock": "BMBL",
               "filterTime": "2025-03-12T14:26:47.887077"
            },
            "daily": {
               "BIAS": {
                  "bias": -9.144499950725663
               },
               "RSI": {
                  "value": 29.090834584732246,
                  "period": 14
               },
               "MACD": {
                  "value": -0.7884700040060277,
                  "signal": -0.7570294148390916,
                  "histogram": -0.03144058916693615,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -27.453066201546278
               },
               "RSI": {
                  "value": 29.409381979284678,
                  "period": 14
               },
               "MACD": {
                  "value": -0.7601984313023271,
                  "signal": -0.48638674828708317,
                  "histogram": -0.27381168301524395,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "CCCC": {
            "metaData": {
               "stock": "CCCC",
               "filterTime": "2025-03-12T14:27:09.942689"
            },
            "daily": {
               "BIAS": {
                  "bias": -17.997031769075257
               },
               "RSI": {
                  "value": 20.420863586111178,
                  "period": 14
               },
               "MACD": {
                  "value": -0.34658950665672617,
                  "signal": -0.30579456350309436,
                  "histogram": -0.0407949431536318,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -37.456611838181814
               },
               "RSI": {
                  "value": 27.858309405858364,
                  "period": 14
               },
               "MACD": {
                  "value": -0.7622243938949333,
                  "signal": -0.608430611938882,
                  "histogram": -0.1537937819560513,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "LSH": {
            "metaData": {
               "stock": "LSH",
               "filterTime": "2025-03-12T14:30:51.425238"
            },
            "daily": {
               "BIAS": {
                  "bias": -25.25155357025547
               },
               "RSI": {
                  "value": 22.908100881595274,
                  "period": 14
               },
               "MACD": {
                  "value": -0.25625964841011784,
                  "signal": -0.19620034250211552,
                  "histogram": -0.06005930590800232,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -44.276129316614075
               },
               "RSI": {
                  "value": 28.141911034417536,
                  "period": 14
               },
               "MACD": {
                  "value": -0.41360217805402355,
                  "signal": -0.30564841267453435,
                  "histogram": -0.1079537653794892,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "XELB": {
            "metaData": {
               "stock": "XELB",
               "filterTime": "2025-03-12T14:35:21.185586"
            },
            "daily": {
               "BIAS": {
                  "bias": -11.03750271976412
               },
               "RSI": {
                  "value": 25.418115358195895,
                  "period": 14
               },
               "MACD": {
                  "value": -0.040926506473314694,
                  "signal": -0.038566526487498684,
                  "histogram": -0.0023599799858160103,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -33.785150309452234
               },
               "RSI": {
                  "value": 25.596264357501425,
                  "period": 14
               },
               "MACD": {
                  "value": -0.1131957001215077,
                  "signal": -0.09512230823002038,
                  "histogram": -0.018073391891487323,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "SRDX": {
            "metaData": {
               "stock": "SRDX",
               "filterTime": "2025-03-12T14:33:59.610292"
            },
            "daily": {
               "BIAS": {
                  "bias": -11.147742392867189
               },
               "RSI": {
                  "value": 19.44071967127681,
                  "period": 14
               },
               "MACD": {
                  "value": -1.8966865125094934,
                  "signal": -1.3482722497945532,
                  "histogram": -0.5484142627149402,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -19.30280953672795
               },
               "RSI": {
                  "value": 20.511355430001696,
                  "period": 14
               },
               "MACD": {
                  "value": -2.064667502894814,
                  "signal": -0.9535058780249308,
                  "histogram": -1.111161624869883,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "GRWG": {
            "metaData": {
               "stock": "GRWG",
               "filterTime": "2025-03-12T14:29:21.018260"
            },
            "daily": {
               "BIAS": {
                  "bias": -13.595248894411306
               },
               "RSI": {
                  "value": 25.496924827100667,
                  "period": 14
               },
               "MACD": {
                  "value": -0.10424710627699518,
                  "signal": -0.0938212255483502,
                  "histogram": -0.010425880728644976,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -27.56245730242825
               },
               "RSI": {
                  "value": 28.30341218520953,
                  "period": 14
               },
               "MACD": {
                  "value": -0.24387047731713785,
                  "signal": -0.20024051885852553,
                  "histogram": -0.04362995845861231,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "KTCC": {
            "metaData": {
               "stock": "KTCC",
               "filterTime": "2025-03-12T14:30:27.093100"
            },
            "daily": {
               "BIAS": {
                  "bias": -9.30552216217725
               },
               "RSI": {
                  "value": 28.415898638073724,
                  "period": 14
               },
               "MACD": {
                  "value": -0.2419379950474605,
                  "signal": -0.24106368770209585,
                  "histogram": -0.0008743073453646444,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -25.593593161495647
               },
               "RSI": {
                  "value": 22.376751760335782,
                  "period": 14
               },
               "MACD": {
                  "value": -0.5370304160838852,
                  "signal": -0.342370335648733,
                  "histogram": -0.19466008043515226,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "DMRC": {
            "metaData": {
               "stock": "DMRC",
               "filterTime": "2025-03-12T14:28:04.317589"
            },
            "daily": {
               "BIAS": {
                  "bias": -23.586457144442548
               },
               "RSI": {
                  "value": 19.56765304419342,
                  "period": 14
               },
               "MACD": {
                  "value": -5.760198560196553,
                  "signal": -5.147904011334915,
                  "histogram": -0.6122945488616383,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -47.88658008006566
               },
               "RSI": {
                  "value": 28.75423640232649,
                  "period": 14
               },
               "MACD": {
                  "value": -2.868671891720826,
                  "signal": 0.10782831867695253,
                  "histogram": -2.9765002103977785,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "UCTT": {
            "metaData": {
               "stock": "UCTT",
               "filterTime": "2025-03-12T14:34:42.894216"
            },
            "daily": {
               "BIAS": {
                  "bias": -13.677445544034986
               },
               "RSI": {
                  "value": 27.796396616950602,
                  "period": 14
               },
               "MACD": {
                  "value": -3.6585985732516306,
                  "signal": -3.033934818305947,
                  "histogram": -0.6246637549456837,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -29.11302150264178
               },
               "RSI": {
                  "value": 28.17716659439784,
                  "period": 14
               },
               "MACD": {
                  "value": -2.8718360704430523,
                  "signal": -1.4763730488749218,
                  "histogram": -1.3954630215681305,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "TNDM": {
            "metaData": {
               "stock": "TNDM",
               "filterTime": "2025-03-12T14:34:29.617073"
            },
            "daily": {
               "BIAS": {
                  "bias": -20.82395412770765
               },
               "RSI": {
                  "value": 18.556947783377737,
                  "period": 14
               },
               "MACD": {
                  "value": -4.537602862749907,
                  "signal": -3.5328736641272735,
                  "histogram": -1.0047291986226332,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -38.09901801511553
               },
               "RSI": {
                  "value": 25.508392556062475,
                  "period": 14
               },
               "MACD": {
                  "value": -3.605814456562026,
                  "signal": -1.808026714372058,
                  "histogram": -1.797787742189968,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            }
            },
            "COHU": {
            "metaData": {
               "stock": "COHU",
               "filterTime": "2025-03-12T14:27:38.287080"
            },
            "daily": {
               "BIAS": {
                  "bias": -10.184743243632207
               },
               "RSI": {
                  "value": 27.80174158853771,
                  "period": 14
               },
               "MACD": {
                  "value": -1.624649520821091,
                  "signal": -1.3879994435299485,
                  "histogram": -0.2366500772911424,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
               }
            },
            "weekly": {
               "BIAS": {
                  "bias": -23.364668581360366
               },
               "RSI": {
                  "value": 23.782969028864187,
                  "period": 14
               },
               "MACD": {
                  "value": -2.4687053079911436,
                  "signal": -1.7129547322004062,
                  "histogram": -0.7557505757907375,
                  "fast_period": 12,
                  "slow_period": 26,
                  "signal_period": 9
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

### Example API Request

```bash
curl -X POST "http://localhost:8000/api/trigger_fetch_filtering" \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["all"], "timeFrame": ["daily", "weekly", "monthly"]}'
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