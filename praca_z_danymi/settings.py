from pathlib import Path
from pprint import pprint

# Nazwa bazy danych
DATABASE_NAME = 'notowania'

# Parameters for connecting to the PostgreSQL database
DB_PARAMS = {
    'host': '127.0.0.1',
    'database': DATABASE_NAME,
    'user': 'postgres',
    'password': 'postgres',
}

# Ścieżki do folderów i plików z danymi giełdowymi
DIR_PATH = '/home/simon/Downloads/data'
FILE_PATH_FOR_UPDATE = '/home/simon/Downloads/dane_d.txt'

# Obserwowane instrumenty finansowe
MARKET_TICKERS_DICT_NAMES = {
    # ticker: name
    '^DJI': 'DOW JONES INDUSTRIAL AVERAGE',
    '^DJT': 'DOW JONES TRANSPORTATION AVERAGE',
    '^DAX': 'DAX',
    '^FTM': 'FTSE',
    'XAUUSD': 'XAU/USD',  # kontrakty na złoto w $
    'XAGUSD': 'XAG/USD',  # kontrakty srebro w $
    'EURUSD': 'EUR/USD',
    'GBPUSD': 'GBP/USD',
    'GBPJPY': 'GBP/JPY',
    'USDJPY': 'USD/JPY',
    'USDCAD': 'USD/CAD',
    'USDPLN': 'USD/PLN',
    'EURPLN': 'EUR/PLN',
    'GBPPLN': 'GBP/PLN',
    'CHFPLN': 'CHF/PLN',
    'WIG': 'WIG',
    'WIG20': 'WIG20',
}

# Definicje nazw kolumn tablicach PostgreSQL
TABLE_COLUMN_DEFINITION_PSQL = [
    "ticker VARCHAR(6)",
    "date DATE",
    "time VARCHAR(6)",
    "open DOUBLE PRECISION",
    "high DOUBLE PRECISION",
    "low DOUBLE PRECISION",
    "close DOUBLE PRECISION"
]

# Tickery używane w plikach txt
# [
#    '^DJI', '^DJT', '^DAX', '^FTM', 'XAUUSD', 'XAGUSD', 'EURUSD', 'GBPUSD', 'GBPJPY',
#    'USDJPY', 'USDCAD', 'USDPLN', 'EURPLN', 'GBPPLN', 'CHFPLN', 'WIG', 'WIG20'
# ]
MARKET_TICKERS = [ticker for ticker in MARKET_TICKERS_DICT_NAMES.keys()]

# Nazwy plików txt
# [
#    '^dji.txt', '^djt.txt', '^dax.txt', '^ftm.txt', 'xauusd.txt', 'xagusd.txt',
#    'eurusd.txt', 'gbpusd.txt', 'gbpjpy.txt', 'usdjpy.txt', 'usdcad.txt', 'usdpln.txt',
#    'eurpln.txt', 'gbppln.txt', 'chfpln.txt', 'wig.txt', 'wig20.txt'
# ]
FILE_NAMES_DATA_TXT = [ticker.lower() + '.txt' for ticker in MARKET_TICKERS]

# Automatyczne ścieżki do plikow txt - ułatwiają wydobywanie danych
# [
#    PosixPath('/home/simon/with_my_jupyter/astro_again_2025_03_29/astro_in_vsc/data/daily/world/indices/^dji.txt'),
#    PosixPath('/home/simon/with_my_jupyter/astro_again_2025_03_29/astro_in_vsc/data/daily/world/indices/^djt.txt'),
#    ...
#    PosixPath('/home/simon/with_my_jupyter/astro_again_2025_03_29/astro_in_vsc/data/daily/pl/wse/indices/wig20.txt'),
# ]
PATH_TO_FILES_DATA_TXT = [
    list(Path(DIR_PATH).rglob(file_to_find))[0]for file_to_find in FILE_NAMES_DATA_TXT
]

# Ustanownione nazwy tabel w PostgreSQL
# [
#    'dji', 'djt', 'dax', 'ftm', 'xauusd', 'xagusd', 'eurusd', 'gbpusd', 'gbpjpy',
#    'usdjpy', 'usdcad', 'usdpln', 'eurpln', 'gbppln', 'chfpln', 'wig', 'wig20'
# ]
TABLE_NAMES_PSQL_INDIRECT = [ticker.lower().replace('^', '') for ticker in MARKET_TICKERS]

# Wybrane kolumny w dataframe'ach pandasa
COLUMN_NAMES_REPLACEMENTS_FOR_DF = {
    '<TICKER>': 'ticker',
    '<DATE>': 'date',
    '<OPEN>': 'open',
    '<HIGH>': 'high',
    '<LOW>': 'low',
    '<CLOSE>': 'close',
}

# Ustanownione nazwy kolumn w tabelach PostreSQL
# ['ticker', 'date', 'open', 'high', 'low', 'close']
COLUMNS_IN_DF_AND_PSQL = [
    val for val in COLUMN_NAMES_REPLACEMENTS_FOR_DF.values()
]


# FUNCJE POMOCNICZE


def check_paths():
    if Path(DIR_PATH).exists():
        print(f"Folder '{DIR_PATH}' istnieje.")
    else:
        print(f"Folder '{DIR_PATH}' nie istnieje.")

    if Path(FILE_PATH_FOR_UPDATE).exists():
        print(f"Folder '{FILE_PATH_FOR_UPDATE}' istnieje.")
    else:
        print(f"Folder '{FILE_PATH_FOR_UPDATE}' nie istnieje.")


def check_selected_markets():
    pprint(MARKET_TICKERS_DICT_NAMES)


def check_column_names_in_df():
    col_names = list(COLUMN_NAMES_REPLACEMENTS_FOR_DF.values())
    print(col_names)


if __name__ == '__main__':
    print()
    print('Sprawdza ścieżki do plików:')
    check_paths()
    print('------------------')

    print('Sprawdza wybrne rynki:')
    check_selected_markets()
    print('Sprawdza nominalne nazwy kolumn w DataFrame:')
    check_column_names_in_df()
    print('------------------')

    print('Sprawdza nominalne nazwy kolumn w tabelach PostgreSQL:')
    print(COLUMNS_IN_DF_AND_PSQL)
    print('------------------')

    print('Sprawdza nominalne nazwy tabel w PostgreSQL:')
    print(TABLE_NAMES_PSQL_INDIRECT)
    print('------------------')

    print('Koniec.')
    print()
