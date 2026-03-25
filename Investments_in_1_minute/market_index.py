import pandas as pd


# INDEX → constituents source
INDEX_SOURCES = {

    "SP500": "https://datahub.io/core/s-and-p-500-companies/r/constituents.csv",

    "NASDAQ100": "https://datahub.io/core/nasdaq-listings/r/nasdaq-listed-symbols.csv",

}


# ETF → INDEX mapping
ETF_INDEX_MAP = {

    "VOO": "SP500",
    "SPY": "SP500",
    "IVV": "SP500",

    "QQQ": "NASDAQ100",

}


async def load_sp500():

    df = pd.read_csv(INDEX_SOURCES["SP500"])

    weight = 1.0 / len(df)

    holdings = []

    for symbol in df["Symbol"]:

        holdings.append({
            "ticker": symbol.upper(),
            "weight": weight
        })

    print("SP500 loaded:", len(holdings))

    return holdings


async def load_nasdaq100():

    url = "https://en.wikipedia.org/wiki/Nasdaq-100"

    tables = pd.read_html(url)

    df = tables[4]

    weight = 1.0 / len(df)

    holdings = []

    for symbol in df["Ticker"]:

        holdings.append({
            "ticker": symbol.upper(),
            "weight": weight
        })

    print("NASDAQ100 loaded:", len(holdings))

    return holdings


INDEX_LOADERS = {

    "SP500": load_sp500,
    "NASDAQ100": load_nasdaq100,

}


async def get_etf_holdings(ticker):

    ticker = ticker.upper()

    index = ETF_INDEX_MAP.get(ticker)

    if not index:

        print("Unknown ETF index")
        return None

    loader = INDEX_LOADERS[index]

    holdings = await loader()

    print("ETF holdings via INDEX:", len(holdings))

    return holdings