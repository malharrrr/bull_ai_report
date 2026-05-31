import json
import yfinance as yf
from google.genai import types
from extractor import _get_client, FINANCIAL_SCHEMA

def fetch_market_data(ticker: str, company_name: str) -> dict:
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
    """Synthesize extracted data with analyst insights and market data."""
    client = _get_client()
    
    ticker = extracted_data.get("nse_code") or extracted_data.get("bse_code")
    company_name = extracted_data.get("company_name", "")
    
    if not ticker and company_name:
        ticker = company_name.split()[0].upper()
        
    market_data = fetch_market_data(ticker, company_name)
    
    if market_data.get('cmp') and not extracted_data.get('cmp'):
        extracted_data['cmp'] = market_data['cmp']
    if market_data.get('stock_type') and not extracted_data.get('stock_type'):
        extracted_data['stock_type'] = market_data['stock_type']
    
    prompt = f"""
    You are a Lead Equity Research Analyst at a major brokerage firm like Geojit.
    
    I have extracted financial data from a corporate earnings document. Your task is to:
    
    1. VALIDATE RATINGS: If no rating is present, calculate one based on valuation:
       - BUY: upside > 15%
       - ACCUMULATE: upside 10-15%
       - HOLD: upside 0-10%
       - REDUCE: downside 0-10%
       - SELL: downside > 10%
    
    2. TARGET PRICE CALCULATION: If missing, calculate using:
       - Forward P/E multiple (use historical average or peer comparison)
       - OR EV/EBITDA multiple
       - OR P/B multiple
       Apply 12-month forward estimate
    
    3. FILL MISSING FORWARD ESTIMATES: If FY26E, FY27E missing:
       - Calculate based on historical CAGR
       - Conservative assumptions for mature companies
       - Growth assumptions for high-growth sectors
    
    4. OUTLOOK PARAGRAPH: Generate a 3-4 sentence professional outlook that:
       - Addresses the company's competitive position
       - Discusses growth drivers or headwinds
       - Justifies the valuation and rating
    
    Extracted Data:
    {json.dumps(extracted_data, indent=2)}
    
    Output MUST be valid JSON matching this schema with all required fields populated:
    - rating (BUY/HOLD/SELL/ACCUMULATE/REDUCE)
    - target_price (calculated if missing)
    - return_pct (upside/downside %)
    - outlook_valuation (professional paragraph)
    - annual_estimates (complete with projections if needed)
    
    Be analytical but conservative. Do not over-estimate growth.
    """
    
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=FINANCIAL_SCHEMA,
            temperature=0.3,
        )
    )
    
    synthesized = json.loads(response.text.strip())
    result = {**extracted_data, **synthesized}
    
    if not result.get('rating'):
        result['rating'] = 'HOLD'
    if not result.get('outlook_valuation'):
        result['outlook_valuation'] = 'Company shows stable operational performance with growing market presence.'
    
    return result