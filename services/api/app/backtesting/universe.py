from __future__ import annotations

NIFTY50_CURRENT = {
    "ADANIENT": "Adani Enterprises", "ADANIPORTS": "Adani Ports & SEZ", "APOLLOHOSP": "Apollo Hospitals",
    "ASIANPAINT": "Asian Paints", "AXISBANK": "Axis Bank", "BAJAJ-AUTO": "Bajaj Auto", "BAJFINANCE": "Bajaj Finance",
    "BAJAJFINSV": "Bajaj Finserv", "BEL": "Bharat Electronics", "BHARTIARTL": "Bharti Airtel", "CIPLA": "Cipla",
    "COALINDIA": "Coal India", "DRREDDY": "Dr. Reddy's Laboratories", "EICHERMOT": "Eicher Motors", "ETERNAL": "Eternal",
    "GRASIM": "Grasim Industries", "HCLTECH": "HCL Technologies", "HDFCBANK": "HDFC Bank", "HDFCLIFE": "HDFC Life",
    "HINDALCO": "Hindalco Industries", "HINDUNILVR": "Hindustan Unilever", "ICICIBANK": "ICICI Bank",
    "INDIGO": "InterGlobe Aviation", "INFY": "Infosys", "ITC": "ITC", "JIOFIN": "Jio Financial Services", "JSWSTEEL": "JSW Steel",
    "KOTAKBANK": "Kotak Mahindra Bank", "LT": "Larsen & Toubro", "M&M": "Mahindra & Mahindra", "MARUTI": "Maruti Suzuki",
    "MAXHEALTH": "Max Healthcare", "NESTLEIND": "Nestle India", "NTPC": "NTPC", "ONGC": "ONGC",
    "POWERGRID": "Power Grid Corporation of India", "RELIANCE": "Reliance Industries", "SBILIFE": "SBI Life Insurance",
    "SBIN": "State Bank of India", "SHRIRAMFIN": "Shriram Finance", "SUNPHARMA": "Sun Pharmaceutical Industries",
    "TATACONSUM": "Tata Consumer Products", "TCS": "Tata Consultancy Services", "TECHM": "Tech Mahindra", "TITAN": "Titan Company",
    "TMPV": "Tata Motors Passenger Vehicles", "TATASTEEL": "Tata Steel", "TRENT": "Trent", "ULTRACEMCO": "UltraTech Cement",
    "WIPRO": "Wipro",
}


def yahoo_symbol(symbol: str) -> str:
    value = symbol.strip().upper()
    if value.startswith("^") or value.endswith((".NS", ".BO")):
        return value
    return f"{value}.NS"
