import pandas as pd
from datetime import datetime, date

from .models import Market
from .config import load_markets_from_yaml
from . import settings


def get_url(
        ticker: str,
        date_start: date | None = None,
        date_end: date | None = None
):
    t = ticker.lower()
    date_format = '%Y%m%d'
    url_stooq_path_base = settings.PATH_BASE

    if date_start is None and date_end is None:
        url = f'{url_stooq_path_base}?s={t}&i=d'
    elif date_start is not None and date_end is None:
        d1 = date_start.strftime(date_format)
        d2 = datetime.now().strftime(date_format)

        url = f'{url_stooq_path_base}?s={t}&d1={d1}&d2={d2}&i=d'
    else:
        d1 = date_start.strftime(date_format)
        d2 = date_end.strftime(date_format)

        url = f'{url_stooq_path_base}?s={t}&d1={d1}&d2={d2}&i=d'

    print(url)
    return url


def get_stooq_data(
        market: Market,
        date_start: date | None = None,
        date_end: date | None = None,
) -> pd.DataFrame:

    try:
        url = get_url(market.ticker, date_start=date_start, date_end=date_end)
    except Exception as ex:
        print(f'Exception: {ex}')
        raise ex

    try:
        df = pd.read_csv(url)
    except Exception as ex:
        print(f'Exception: {ex}')
        raise ex

    df.columns = [c.lower() for c in df.columns]
    df['date'] = pd.to_datetime(df['date'])

    # Konwertuje daty na stringi
    df['date'] = df['date'].dt.strftime('%Y-%m-%d')

    # dodaje tickera jako pierwsza kolumna
    df['ticker'] = market.ticker
    cols = ['ticker'] + [c for c in df.columns if c != 'ticker']

    return df[cols]


def add_ticker(
        df: pd.DataFrame,
        ticker: str
) -> pd.DataFrame:
    """
    Dodaje kolumnę 'ticker' z podaną wartością do DataFrame
    i ustawia ją jako pierwszą kolumnę.

    :param df: DataFrame wejściowy
    :param ticker: Stała wartość tickera (np. 'XXX')
    :return: DataFrame z dodaną kolumną 'ticker'
    """
    markets = load_markets_from_yaml()

    # odnajduje market po 'spłaszczonym' tickerze
    market = next(
        (market for market in markets if ticker == market.ticker.lower()),
        None
    )
    print('jestem w add_ticker. market przyjmuje wartość: ', market)

    # pozyskuje poprawną, pełną nazwę tickera
    ticker_full = market.ticker

    df = df.copy()

    # dodaje kolumnę i ustawia porządek zgodny z bazą danych
    df['ticker'] = ticker_full
    cols = ['ticker'] + [c for c in df.columns if c != 'ticker']

    return df[cols]


if __name__ == '__main__':
    ticker = 'wig20'
    date_start = date(2025, 8, 1)
    date_end = date(2025, 9, 1)

    get_url(ticker=ticker, date_start=date_start, date_end=date_end)

    # # get_url(ticker=ticker, date_start=date_start)
    # df = get_stooq_data(
    #     ticker='wig20',
    #     date_start=date_start,
    #     # date_end=date_end
    # )
    # print('---')
    # print(df.head())
    # print('---')
    # print(df.tail())
    # print('---')

    # # user musi być zalogowany na koncie żeby to działało poprawnie

    # df = pd.DataFrame({
    #     "date": ["2025-01-01", "2025-01-02"],
    #     "open": [100, 105],
    #     "close": [110, 115]
    # })

    # # df = add_ticker(df, "XXX")
    # print(df)
