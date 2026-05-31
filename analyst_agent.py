import json
import yfinance as yf
from google.genai import types
from extractor import _get_client, FINANCIAL_SCHEMA

def fetch_market_data(ticker: str) -> dict:
    """Fetches market data from Yahoo Finance."""
    if not ticker: 
        return {}
        
    try:
        if not ticker.endswith('.NS') and not ticker.endswith('.BO'):
            ticker += '.NS'
            
        info = yf.Ticker(ticker).info
        
        market_cap = info.get('marketCap', 0) / 10000000 if info.get('marketCap') else None
        shares = info.get('sharesOutstanding', 0) / 10000000 if info.get('sharesOutstanding') else None
        
        return {
            "cmp": info.get('currentPrice', info.get('regularMarketPrice')),
            "week_52_high": info.get('fiftyTwoWeekHigh'),
            "week_52_low": info.get('fiftyTwoWeekLow'),
            "market_cap": market_cap,
            "outstanding_shares": shares,
            "beta": info.get('beta'),
            "stock_type": "Large Cap" if (market_cap and market_cap > 20000) else ("Mid Cap" if (market_cap and market_cap > 5000) else "Small Cap")
        }
    except Exception as e:
        print(f"[!] yfinance warning: Could not fetch data for {ticker} - {e}")
        return {}

def synthesize_report(extracted_data: dict) -> dict:
    """Passes raw extraction + market data to Gemini to finalize the report."""
    client = _get_client()
    
    ticker = extracted_data.get("nse_code")
    if not ticker and extracted_data.get("company_name"):
        ticker = extracted_data["company_name"].split()[0].upper()
        
    market_data = fetch_market_data(ticker)
    
    prompt = f"""
    You are the Lead Equity Research Analyst at a major brokerage. 
    I have provided the raw historical facts extracted from a corporate earnings document, along with market metrics.
    
    Raw Corporate Data: {json.dumps(extracted_data)}
    Live Market Data: {json.dumps(market_data)}
    
    YOUR TASK:
    1. Merge the Live Market Data into the final output.
    2. Act as the Analyst: If 'annual_estimates' lacks forward years (e.g., FY26E), generate reasonable projections based on historical trajectory.
    3. Formulate a professional 'outlook_valuation' paragraph explaining your thesis.
    4. Calculate a 'target_price' using standard multiple models (e.g., P/E or EV/EBITDA on your forward estimates).
    5. Assign a 'rating' (BUY/HOLD/SELL/ACCUMULATE/REDUCE) derived strictly from the upside percentage between 'cmp' and 'target_price'.
    6. Calculate the 'return_pct'.
    
    Output strict JSON matching the schema. You must populate the rating, target_price, and missing forward estimates.
    """
    
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=FINANCIAL_SCHEMA,
            temperature=0.2, 
        )
    )
    
    return json.loads(response.text.strip())