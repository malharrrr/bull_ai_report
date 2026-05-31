import os
import json
from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import types

_client = None

def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key == "your_gemini_api_key_here":
            raise ValueError(
                "GEMINI_API_KEY is not set. "
                "Please edit .env and add your Gemini API key."
            )
        _client = genai.Client(api_key=api_key)
    return _client

FINANCIAL_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "company_name": types.Schema(type=types.Type.STRING, description="Official name of the company."),
        "sector": types.Schema(type=types.Type.STRING, description="Industry sector."),
        "report_date": types.Schema(type=types.Type.STRING, description="Date the research report was published."),
        "rating": types.Schema(type=types.Type.STRING, description="BUY, HOLD, SELL, ACCUMULATE, or REDUCE."),
        "target_price": types.Schema(type=types.Type.NUMBER, description="Target price in INR."),
        "cmp": types.Schema(type=types.Type.NUMBER, description="Current Market Price in INR."),
        "return_pct": types.Schema(type=types.Type.NUMBER, description="Expected return percentage."),
        "stock_type": types.Schema(type=types.Type.STRING, description="Large Cap, Mid Cap, or Small Cap."),
        "bloomberg_code": types.Schema(type=types.Type.STRING),
        "nse_code": types.Schema(type=types.Type.STRING),
        "bse_code": types.Schema(type=types.Type.STRING),
        "sensex": types.Schema(type=types.Type.STRING),
        "time_frame": types.Schema(type=types.Type.STRING),
        
        "company_data": types.Schema(
            type=types.Type.OBJECT,
            properties={
                "market_cap": types.Schema(type=types.Type.NUMBER),
                "week_52_high": types.Schema(type=types.Type.NUMBER),
                "week_52_low": types.Schema(type=types.Type.NUMBER),
                "enterprise_value": types.Schema(type=types.Type.NUMBER),
                "outstanding_shares": types.Schema(type=types.Type.NUMBER),
                "free_float_pct": types.Schema(type=types.Type.NUMBER),
                "face_value": types.Schema(type=types.Type.NUMBER),
                "beta": types.Schema(type=types.Type.NUMBER),
                "dividend_yield": types.Schema(type=types.Type.NUMBER),
            }
        ),
        
        "shareholding": types.Schema(
            type=types.Type.OBJECT,
            properties={
                "promoters_pct": types.Schema(type=types.Type.NUMBER),
                "fii_pct": types.Schema(type=types.Type.NUMBER),
                "mf_institutions_pct": types.Schema(type=types.Type.NUMBER),
                "public_pct": types.Schema(type=types.Type.NUMBER),
                "others_pct": types.Schema(type=types.Type.NUMBER),
            }
        ),
        
        "price_performance": types.Schema(
            type=types.Type.OBJECT,
            properties={
                "three_month_pct": types.Schema(type=types.Type.NUMBER),
                "six_month_pct": types.Schema(type=types.Type.NUMBER),
                "one_year_pct": types.Schema(type=types.Type.NUMBER),
            }
        ),
        
        "quarterly_financials": types.Schema(
            type=types.Type.OBJECT,
            properties={
                "current_quarter": types.Schema(type=types.Type.STRING),
                "prior_year_quarter": types.Schema(type=types.Type.STRING),
                "sales_current": types.Schema(type=types.Type.NUMBER),
                "sales_prior_year": types.Schema(type=types.Type.NUMBER),
                "sales_yoy_growth": types.Schema(type=types.Type.NUMBER),
                "ebitda_current": types.Schema(type=types.Type.NUMBER),
                "ebitda_prior_year": types.Schema(type=types.Type.NUMBER),
                "ebitda_yoy_growth": types.Schema(type=types.Type.NUMBER),
                "ebitda_margin_current": types.Schema(type=types.Type.NUMBER),
                "ebitda_margin_prior_year": types.Schema(type=types.Type.NUMBER),
                "pat_current": types.Schema(type=types.Type.NUMBER),
                "pat_prior_year": types.Schema(type=types.Type.NUMBER),
                "pat_yoy_growth": types.Schema(type=types.Type.NUMBER),
                "eps_current": types.Schema(type=types.Type.NUMBER),
                "eps_prior_year": types.Schema(type=types.Type.NUMBER),
            }
        ),
        
        "annual_estimates": types.Schema(
            type=types.Type.ARRAY,
            description="Historical and estimated annual performance.",
            items=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "year": types.Schema(type=types.Type.STRING),
                    "sales": types.Schema(type=types.Type.NUMBER),
                    "sales_growth_pct": types.Schema(type=types.Type.NUMBER),
                    "ebitda": types.Schema(type=types.Type.NUMBER),
                    "ebitda_margin_pct": types.Schema(type=types.Type.NUMBER),
                    "pat": types.Schema(type=types.Type.NUMBER),
                    "pat_growth_pct": types.Schema(type=types.Type.NUMBER),
                    "eps": types.Schema(type=types.Type.NUMBER),
                    "eps_growth_pct": types.Schema(type=types.Type.NUMBER),
                    "pe": types.Schema(type=types.Type.NUMBER),
                    "ev_ebitda": types.Schema(type=types.Type.NUMBER),
                    "pb": types.Schema(type=types.Type.NUMBER),
                    "roe_pct": types.Schema(type=types.Type.NUMBER),
                }
            )
        ),
        
        "key_highlights": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
        "outlook_valuation": types.Schema(type=types.Type.STRING, description="Business outlook and valuation thesis paragraph."),
    }
)

EXTRACTION_PROMPT = """
You are an expert equity research data pipeline. Extract financial metrics from the attached document matching the Geojit research report structure.

CRITICAL EXTRACTION RULES:
1. SYNONYM MAPPING:
   - "Sales", "Revenue", "Revenue from Operations", "Net Sales" all map to sales fields
   - "PAT", "Profit After Tax", "Net Profit" all map to pat fields
   - "EBITDA", "Operating Profit", "Operating Income" all map to ebitda fields

2. FINANCIAL TABLE EXTRACTION:
   - Look for quarterly performance tables: extract current quarter, prior year quarter, YoY growth rates
   - Look for annual estimates tables: extract all years (FY24A, FY25A, FY26E, FY27E, etc.)
   - For each year, extract: Sales, Growth%, EBITDA, Margin%, PAT, EPS, P/E, EV/EBITDA, P/B, ROE%

3. COMPANY DATA:
   - Market Cap, 52-Week High/Low, Enterprise Value, Outstanding Shares, Free Float%, Face Value, Beta

4. SHAREHOLDING PATTERN:
   - Promoters, FII, MF/Institutions, Public, Others percentages

5. PRICE PERFORMANCE:
   - 3-Month, 6-Month, 1-Year returns percentages

6. KEY INFORMATION:
   - Sector classification
   - Report date
   - NSE/BSE codes
   - Bloomberg code
   - Key operational highlights (bullet points)
   - Business outlook and valuation thesis paragraph

Do not invent data. If a field is not in the document, leave it null or empty.
"""

def extract_financials(filepath: str) -> dict:
    client = _get_client()
    uploaded_file = client.files.upload(file=filepath)
    
    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=[uploaded_file, EXTRACTION_PROMPT],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=FINANCIAL_SCHEMA,
                temperature=0.0,
            )
        )
        return json.loads(response.text.strip())
    finally:
        try:
            client.files.delete(name=uploaded_file.name)
        except Exception:
            pass