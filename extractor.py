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
        "sector": types.Schema(type=types.Type.STRING, description="Industry sector (e.g., Power, Utilities, IT)."),
        "report_date": types.Schema(type=types.Type.STRING, description="Date the research report or earnings presentation was published."),
        "rating": types.Schema(type=types.Type.STRING, description="Investment recommendation. Must map to exactly one: BUY, HOLD, SELL, ACCUMULATE, REDUCE, or null."),
        "target_price": types.Schema(type=types.Type.NUMBER, description="The analyst's target price. Leave null if absent."),
        "cmp": types.Schema(type=types.Type.NUMBER, description="Current Market Price. Leave null if absent."),
        "return_pct": types.Schema(type=types.Type.NUMBER, description="Expected upside or return percentage number."),
        "stock_type": types.Schema(type=types.Type.STRING, description="Market cap classification (Large Cap, Mid Cap, Small Cap)."),
        "bloomberg_code": types.Schema(type=types.Type.STRING),
        "nse_code": types.Schema(type=types.Type.STRING),
        "bse_code": types.Schema(type=types.Type.STRING),
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
            }
        ),
        
        "quarterly_financials": types.Schema(
            type=types.Type.OBJECT,
            properties={
                "current_quarter": types.Schema(type=types.Type.STRING, description="Label of current quarter (e.g., Q2FY26)."),
                "prior_year_quarter": types.Schema(type=types.Type.STRING, description="Label of corresponding quarter last year (e.g., Q2FY25)."),
                "prior_quarter": types.Schema(type=types.Type.STRING, description="Label of consecutive prior quarter (e.g., Q1FY26). Leave null if not present."),
                "sales_current": types.Schema(type=types.Type.NUMBER, description="Current quarter Revenue / Turnover / Net Sales value in Rs. Cr."),
                "sales_prior_year": types.Schema(type=types.Type.NUMBER, description="Year-ago quarter Revenue / Net Sales value in Rs. Cr."),
                "sales_yoy_growth": types.Schema(type=types.Type.NUMBER, description="YoY Revenue growth percentage number."),
                "sales_prior_quarter": types.Schema(type=types.Type.NUMBER, description="Consecutive prior quarter Sales value. Leave null if missing."),
                "sales_qoq_growth": types.Schema(type=types.Type.NUMBER, description="QoQ revenue growth percentage. Leave null if missing."),
                "ebitda_current": types.Schema(type=types.Type.NUMBER, description="Current quarter EBITDA / Operating Profit in Rs. Cr."),
                "ebitda_prior_year": types.Schema(type=types.Type.NUMBER, description="Year-ago quarter EBITDA in Rs. Cr."),
                "ebitda_yoy_growth": types.Schema(type=types.Type.NUMBER, description="YoY EBITDA growth rate percentage number."),
                "ebitda_margin_current": types.Schema(type=types.Type.NUMBER, description="Current quarter EBITDA margin percentage number."),
                "ebitda_margin_prior_year": types.Schema(type=types.Type.NUMBER, description="Year-ago quarter EBITDA margin percentage number."),
                "pat_current": types.Schema(type=types.Type.NUMBER, description="Current quarter Net Profit / Profit After Tax (PAT) in Rs. Cr."),
                "pat_prior_year": types.Schema(type=types.Type.NUMBER, description="Year-ago quarter Profit After Tax (PAT) in Rs. Cr."),
                "pat_yoy_growth": types.Schema(type=types.Type.NUMBER, description="YoY PAT growth percentage number."),
                "eps_current": types.Schema(type=types.Type.NUMBER, description="Current quarter Earnings Per Share (EPS) value."),
                "eps_prior_year": types.Schema(type=types.Type.NUMBER, description="Year-ago quarter Earnings Per Share (EPS) value."),
            }
        ),
        
        "annual_estimates": types.Schema(
            type=types.Type.ARRAY,
            description="Historical and estimated annual performance table sequence.",
            items=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "year": types.Schema(type=types.Type.STRING, description="Year identifier (e.g., FY24, FY25, FY26E, FY27E)."),
                    "sales": types.Schema(type=types.Type.NUMBER, description="Annual Revenue / Net Sales in Rs. Cr."),
                    "sales_growth_pct": types.Schema(type=types.Type.NUMBER),
                    "ebitda": types.Schema(type=types.Type.NUMBER, description="Annual EBITDA / Operating Profit in Rs. Cr."),
                    "ebitda_margin_pct": types.Schema(type=types.Type.NUMBER),
                    "pat": types.Schema(type=types.Type.NUMBER, description="Annual Profit After Tax / Net Profit in Rs. Cr."),
                    "pat_growth_pct": types.Schema(type=types.Type.NUMBER),
                    "eps": types.Schema(type=types.Type.NUMBER),
                    "pe": types.Schema(type=types.Type.NUMBER),
                    "ev_ebitda": types.Schema(type=types.Type.NUMBER),
                    "roe_pct": types.Schema(type=types.Type.NUMBER),
                }
            )
        ),
        "key_highlights": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING), description="List of primary operational highlights."),
        "outlook_valuation": types.Schema(type=types.Type.STRING, description="Summary discussion detailing business outlook and target rationale."),
        "revenue_trend": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.OBJECT, properties={"period": types.Schema(type=types.Type.STRING), "value": types.Schema(type=types.Type.NUMBER)})),
        "ebitda_trend": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.OBJECT, properties={"period": types.Schema(type=types.Type.STRING), "value": types.Schema(type=types.Type.NUMBER), "margin_pct": types.Schema(type=types.Type.NUMBER)})),
        "pat_trend": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.OBJECT, properties={"period": types.Schema(type=types.Type.STRING), "value": types.Schema(type=types.Type.NUMBER)}))
    }
)

EXTRACTION_PROMPT = """
You are acting as an expert equity research data pipeline. Extract exact financial metrics from the attached document.

CRITICAL INSTRUCTION ALGORITHMS:
1. SYNONYM TABLE ROW RESOLUTION:
   - "Sales" can appear labeled as "Revenue", "Revenue from Operations", or "Net Sales".
   - "PAT" can appear labeled as "Profit After Tax", "Net Profit", or "Reported PAT".
   - Map these variations intelligently into their corresponding schema targets.
2. TREND SEQUENCES DATA MATRICES:
   - Look at the columns for Annual Estimates (e.g., FY24, FY25, FY26E). Generate one entry block for every year present.
Extract cleanly and factually. Do not invent missing data points.
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