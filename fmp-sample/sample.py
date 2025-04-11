import requests
import pandas as pd

api_key = "dfiMAaPz1npS81CJctAuUwaajtCzBRsw"

def get_fundamentals(api_key, ticker):
    """
    Returns: dict with pb, pe, roe, dy, gm (or None if unavailable)
    Ticker format: "AAPL" (US), "0700.HK" (Hong Kong)
    """
    results = {'pb': None, 'pe': None, 'roe': None, 'dy': None, 'gm': None}
    
    # Get P/B and P/E from Key Metrics endpoint
    metric_url = f"https://financialmodelingprep.com/api/v3/key-metrics/{ticker}?period=annual&apikey={api_key}"
    metric_data = requests.get(metric_url).json()
    if metric_data:
        results['pe'] = metric_data[0].get('peRatioTTM')

    results['pb'] = get_pb_ratio(api_key, ticker)

    print(f"Annual Metrics: {metric_data}")
          
    # Get ROE and Gross Margin from Ratios endpoint
    ratios_url = f"https://financialmodelingprep.com/api/v3/ratios-ttm/{ticker}?apikey={api_key}"
    ratios_data = requests.get(ratios_url).json()
    if ratios_data:
        results['roe'] = ratios_data[0].get('returnOnEquityTTM') * 100  # Convert to %
        results['gm'] = ratios_data[0].get('grossProfitMarginTTM') * 100
    
    # Get Dividend Yield from Profile endpoint
    profile_url = f"https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={api_key}"
    profile_data = requests.get(profile_url).json()
    if profile_data:
        results['dy'] = profile_data[0].get('lastDiv') / profile_data[0].get('price') * 100
    
    return {k: round(v, 2) if v else None for k,v in results.items()}

def get_pb_ratio(api_key, ticker):
    try:

        url = f"https://financialmodelingprep.com/api/v3/key-metrics/{ticker}?period=quarter&apikey={api_key}"
        data = requests.get(url).json()
        
        if data and len(data) > 0:
            # Prefer pbRatio (more frequently updated) over priceToBookRatio
            return data[0].get('pbRatio')
    except Exception as e:
        print(f"Exception is caught:{e}")

    return get_realtime_pb(api_key, ticker)

def get_realtime_pb(api_key, ticker):
    try:

        # Get latest book value per share
        metrics_url = f"https://financialmodelingprep.com/api/v3/key-metrics/{ticker}?limit=1&apikey={api_key}"
        bvps = requests.get(metrics_url).json()[0].get('bookValuePerShare')
        
        # Get real-time price
        price_url = f"https://financialmodelingprep.com/api/v3/quote-short/{ticker}?apikey={api_key}"
        price = requests.get(price_url).json()[0].get('price')
        
        return round(price / bvps, 2) if all([price, bvps]) else None
    except :
         print(f"Exception is caught in function get_realtime_pb")
    
    return None

# Example usage
print(get_fundamentals(api_key, "AAPL"))  # US Stock

