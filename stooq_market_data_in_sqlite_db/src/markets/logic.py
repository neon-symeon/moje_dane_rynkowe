# -*- coding: utf-8 -*-
"""
Logika biznesowa aplikacji dla operacji na danych rynkowych.

Zawiera funkcje do populacji bazy historycznymi danymi, aktualizacji na pod-
stawie nowych plików, porównywania schematów oraz ustalania zakresów dat do
pobrania. Łączy warstwę konfiguracji, systemu plików i bazy danych w kompletne
procesy (pipeline'y).
"""
# ###########################################################################
# ## IMPORTS
# ###########################################################################
import pandas as pd
from datetime import date, timedelta

from . import settings
from .models import Market
from .db import (
    with_db_write_connection,
    _get_last_db_dates_for_markets,
    _upsert_df_to_sqlite,
    _db_get_tables,
    get_last_db_date_for_market,
)
from .fs import (
    _get_last_date_from_big_txt,
    _get_file_path_to_update,
    _read_txt_single_market_data,
    _calculate_last_df_data,
)
from .config import (
    load_markets_from_yaml,
)
from .stooqpy import (
    get_stooq_data
)


# ###########################################################################
# ## MAIN LOGIC FUNCTIONS
# ###########################################################################
@with_db_write_connection()
def make_populate_database(*, conn, cur, markets: list[Market]):
    """
    Zarządza procesem zasilenia bazy danych z dużych plików.

    Główna funkcja do "dużej aktualizacji". Waliduje schemat, wczytuje
    konfigurację, a następnie dla każdego rynku sprawdza, czy dane
    w pliku `.txt` są nowsze niż w bazie. Jeśli tak, uruchamia
    proces aktualizacji dla danego rynku.

    Parameters
    ----------
    conn : sqlite3.Connection
        Obiekt połączenia z bazą danych (wstrzykiwany przez dekorator).
    cur : sqlite3.Cursor
        Obiekt kursora bazy danych (wstrzykiwany przez dekorator).

    Returns
    -------
    list[Market]
        Lista rynków ze zaktualizowanymi najstarszymi datami w dużych
        plikach txt
        pobranych ze stooq.pl z danymi od początku rynku.
    """
    # TODO
    # Waliduje schemat bazy danych wobec configu yaml. Przechodzi
    # bezszelestnie (komunikat tekstowy).
    # nie reaguje na niezgodności, choć być może powinien usuwać z bazy
    # te tablice które nie są podane w configu yaml. Choć z drugiej stront
    # skoro tam są, to może user błednie sobie coś wykasował w yamlu, więc
    # może lepiej, zeby tak od razu, być może pochopnie, nie kasować tych
    # danych. są, niech sobie będą, i tak z nich nie korzystamy, jedyny
    # downside ich istnienie to zjamowane miejsce na dysku, czyli koszt nie-
    # wileki w gruncie rzeczy...
    print(
        '\n',
        _compare_db_schema_against_markets_list(markets=markets),
        '\n',
    )

    total_rows_affected = 0

    # create_multiple_tables(markets=markets)
    # # .__wrapped__(
    # #     markets=markets,
    # #     conn=conn,
    # #     cur=cur,
    # #     unique_col_name='date',
    # # )

    for market in markets:
        # Sprawdza, czy dla danego rynku znalazł plik
        if not market.file_path:
            print(f'⚠️  Pomijam {market.ticker} - brak pliku z danymi.')
            continue

        market.last_txt_big_date = _get_last_date_from_big_txt(
            market.file_path
        )

        if (
            market.last_db_date and
            market.last_db_date >= market.last_txt_big_date
        ):
            print(
                f'🛈  INFO: Dane dla {market.ticker} są aktualne. Pomijam; \t'
                f'data w: db {market.last_db_date} vs. '
                f'txt {market.last_txt_big_date}'
            )
            continue

        print(
            f'Przetwarzam: {market.ticker} z pliku {market.file_path.name}...'
        )

        df = _read_txt_single_market_data(market.file_path)

        rows_affected = _upsert_df_to_sqlite.__wrapped__(
            db_table_name=market.db_table_name,
            column_names=settings.COLUMNS_IN_DF_AND_SQL,
            df=df,
            conn=conn,
            cur=cur
        )

        total_rows_affected += rows_affected

    print(
        f"\n🏁 Zakończono! Łącznie zmodyfikowano {total_rows_affected} wierszy."
    )

    return markets


def make_update_db(markets: list[Market]):
    """
    Aktualizuje wszystkie rynki na podstawie jednego pliku aktualizacyjnego.

    Główna funkcja realizująca proces "małej aktualizacji". Wyszukuje
    najnowszy plik z danymi (np. `dane_d*.txt`), wczytuje jego
    zawartość, a następnie dla każdego rynku z podanej listy filtruje
    odpowiednie dane i zapisuje je do bazy danych za pomocą operacji
    "upsert".

    Parameters
    ----------
    markets : list[Market]
        Lista obiektów `Market`, które mają zostać poddane procesowi
        aktualizacji.

    Returns
    -------
    bool | None
        Zwraca `True` w przypadku pomyślnego zakończenia procesu
        aktualizacji. Zwraca `None`, jeśli nie znaleziono pliku do
        aktualizacji.

    Notes
    -----
    - Funkcja silnie modyfikuje stan bazy danych.
    - Wszystkie postępy i podsumowania są wypisywane na standardowe
      wyjście (konsolę).
    - Zależy od funkcji pomocniczych, takich jak `_get_file_path_to_update`
      i `_upsert_df_to_sqlite`.

    """
    path_to_small_data_file = _get_file_path_to_update()

    if not path_to_small_data_file:
        print('brak pliku do aktualizacji')
        return None

    df = _read_txt_single_market_data(path_to_small_data_file)

    total_rows_affected = 0

    for market in markets:
        market_df = df[df['ticker'] == market.ticker]
        rows_affected = _upsert_df_to_sqlite(
            db_table_name=market.db_table_name,
            column_names=settings.COLUMNS_IN_DF_AND_SQL,
            df=market_df,
        )

        total_rows_affected += rows_affected

    print(
        '\n🏁 Zakończono aktualizację! Łącznie zmodyfikowano '
        f'{total_rows_affected} wierszy.')

    return True


def make_update_db_with_stooqpy():
    """
    Aktualizuje rynki w bazie danych.

    Główna funkcja realizująca proces "małej aktualizacji".

    - wczytuje nazwę tablicy,
    - wczytuje brakujący zakres danych,
    - znajduje korespondujący z nią plik csv na stooq.py,
    - pobiera odpowiedni zakres danych do uzupełnienia,
    - uzupełnia dane w tabeli db. za pomocą operacji "upsert".

    Parameters
    ----------
    Potrzebujemy linku do bazy danych (dostępnego w settings.py)

    Returns
    -------
    bool | None
        Zwraca `True` w przypadku pomyślnego zakończenia procesu
        aktualizacji. Zwraca `None`, jeśli nie znaleziono pliku do
        aktualizacji.

    Notes
    -----
    - Funkcja silnie modyfikuje stan bazy danych.
    - Wszystkie postępy i podsumowania są wypisywane na standardowe
      wyjście (konsolę).
    - Zależy od funkcji pomocniczych:
      -
      - `_upsert_df_to_sqlite`.

    """
    # pobiera listę tablic z bazy danych
    db_tables_to_update = _db_get_tables()
    print(db_tables_to_update)

    # wczytuje rynki z pliku yaml
    markets = load_markets_from_yaml()

    for db_table in db_tables_to_update:

        # ustala datę od której dla tego rynku pobierze dane
        date_from_missing_data = (
            _adjust_date_to_last_weekday(
                get_last_db_date_for_market(db_table),
                shift_one_day=True,
            )
        )
        print('date_from_missing_data', date_from_missing_data)

        # odnajduje obiekt Market dla tego rynku
        market = get_market_by_db_name(db_table, markets)

        print(market)

        # pobiera dane
        df = get_stooq_data(
            market=market, date_start=date_from_missing_data,
        )

        print(df)

        # aktualizuje bazę danych
        _upsert_df_to_sqlite(
            db_table_name=db_table,
            df=df,
            column_names=settings.COLUMNS_IN_DF_AND_SQL,
            report=True,
        )

        print(f'**po aktualizacji last_db_date_for {market.name}')
        print(
            f'{market.db_table_name}: '
            f'{get_last_db_date_for_market(db_table)}'
        )

    return True


def _compare_db_schema_against_markets_list(
        markets: list[Market]) -> dict[str, set[str]]:
    """
    Porównuje listę rynków z konfiguracji z tabelami w bazie danych.

    Funkcja generuje dwie listy nazw tabel: jedną na podstawie przekazanej
    konfiguracji obiektów `Market`, a drugą na podstawie aktualnego stanu
    bazy danych. Następnie porównuje je, aby znaleźć rozbieżności.

    Parameters
    ----------
    markets : list[Market]
        Lista obiektów `Market` reprezentująca oczekiwaną konfigurację.

    Returns
    -------
    dict[str, set]
        Słownik zawierający dwa klucze: 'missing_tables_in_db' oraz
        'extra_tables_in_db'. Wartościami są zbiory (set) nazw tabel,
        które stanowią różnicę między konfiguracją a stanem bazy.

    """
    markets_table_names_as_set = {market.db_table_name for market in markets}
    db_table_names_as_set = set(_db_get_tables())

    return {
        'missing_tables_in_db': (
            markets_table_names_as_set - db_table_names_as_set),
        'extra_tables_in_db': (
            db_table_names_as_set - markets_table_names_as_set)
    }


def _adjust_date_to_last_weekday(
        start_date: date,
        shift_one_day: bool = False
) -> date:
    """
    Dopasowuje podaną datę do ostatniego dnia roboczego.

    Funkcja sprawdza, czy podana data jest dniem roboczym (pon-pt).
    Jeśli tak, zwraca ją bez zmian. Jeśli data wypada w weekend
    (sobota lub niedziela), funkcja zwraca datę poprzedzającego ją
    piątku.

    Parameters
    ----------
    start_date : date
        Data wejściowa do sprawdzenia i ewentualnej korekty.

    Returns
    -------
    date
        Oryginalna data, jeśli jest dniem roboczym, lub data
        najbliższego poprzedzającego piątku, jeśli jest weekendem.

    Examples
    --------
    >>> _adjust_date_to_last_weekday(date(2025, 8, 8)) # Piątek
    datetime.date(2025, 8, 8)

    >>> _adjust_date_to_last_weekday(date(2025, 8, 9)) # Sobota
    datetime.date(2025, 8, 8)

    >>> _adjust_date_to_last_weekday(date(2025, 8, 10)) # Niedziela
    datetime.date(2025, 8, 8)

    """
    # Słownik definiujący dodatkowe przesunięcie dla każdego dnia tygodnia
    # Klucz: wynik .weekday() (0=pon, ..., 5=sob, 6=nie)
    # Wartość: o ile dodatkowych dni należy się cofnąć
    WEEKEND_SHIFT_MAP = {
        5: timedelta(days=1),  # Sobota -> cofnij o 1 dodatkowy dzień
        6: timedelta(days=2),  # Niedziela -> cofnij o 2 dodatkowe dni
    }

    # Cofamy o jeden dzień
    if shift_one_day:
        start_date = start_date - timedelta(days=1)
    # Pobieramy dodatkowe przesunięcie ze słownika.
    # Używamy .get(key, default), aby dla dni roboczych dostać 0.
    shift = WEEKEND_SHIFT_MAP.get(start_date.weekday(), timedelta(days=0))

    return start_date - shift


def find_update_date_range(
        markets: list[Market]) -> tuple[date, date] | None:
    """
    Określa optymalny zakres dat do pobrania aktualizacji danych.

    Funkcja analizuje listę rynków, aby znaleźć najwcześniejszą spośród
    ostatnich dat zapisu dla każdego z nich w bazie danych. Na tej
    podstawie oblicza i zwraca sugerowany zakres (od, do) dla pobrania
    nowych danych, tak aby uzupełnić braki we wszystkich tabelach.
    Uwzględnia pomijanie weekendów przy wyznaczaniu daty początkowej.

    Parameters
    ----------
    markets : list[Market]
        Lista obiektów `Market` do przeanalizowania. Uwaga: funkcja
        modyfikuje te obiekty w miejscu, uzupełniając ich atrybut
        `last_db_date`.

    Returns
    -------
    tuple[date, date] | None
        Krotka zawierająca datę początkową i końcową (`od`, `do`) dla
        sugerowanej aktualizacji, lub `None`, jeśli baza danych jest
        pusta lub w pełni aktualna.

    Notes
    -----
    Funkcja wypisuje komunikaty informacyjne o stanie aktualności danych
    oraz sugerowanym zakresie na standardowe wyjście (konsolę).

    """
    # TODO: sprwdzić o co chodzi z markets
    # Wczytuje ostatnie daty z bazy dla wszystkich rynków
    markets = _get_last_db_dates_for_markets(markets)

    # Zbiera wszystkie istniejące daty z atrybutów obiektów
    last_dates_in_db = [m.last_db_date for m in markets if m.last_db_date]

    if not last_dates_in_db:
        print("🛈  Baza danych jest pusta. Sugerowane pełne zasilenie danych.")
        return None

    # Znajduje najwcześniejszą z ostatnich dat
    earliest_latest_date = min(last_dates_in_db)
    latest_latest_date = max(last_dates_in_db)

    # Określa zakres dat do pobrania
    start_date_for_update = (
        _adjust_date_to_last_weekday(earliest_latest_date - timedelta(days=1))
    )
    end_date_for_update = date.today()

    # Zabezpieczenie, jeśli dane są już w pełni aktualne
    if start_date_for_update > end_date_for_update:
        print(
            '✅ Dane są aktualne (najstarsza ostatnia data w bazie: '
            f'{earliest_latest_date} - {latest_latest_date}).'
        )
        return None

    print(
        '\n------\n'
        f'Dane w bazie są aktualne do {earliest_latest_date}'
        f' - {latest_latest_date}.\n'
        'Sugerowany zakres danych do pobrania i aktualizacji: '
        f'od {start_date_for_update} do {end_date_for_update}.\n'
        '------\n'

    )

    return (start_date_for_update, end_date_for_update)


def _control_udpate(market: Market, market_df: pd.DataFrame = None):
    """
    Sprawdza, porównuje daty w pliku update w danych rynkowych,
    informuje o tym co podmieniamy, co zostało ew. do podmianki,
    czy plik aktualizacyjny sam jest aktualny.
    """
    last_db_data = market.last_db_date
    last_df_data = _calculate_last_df_data(market_df)

    adjusted_last_df_data = _adjust_date_to_last_weekday(last_df_data)
    adjusted_today = _adjust_date_to_last_weekday(date.today())

    if adjusted_today > adjusted_last_df_data:
        print(
            'Widzę potrzebę aktualizacji pliku do atkualizacji najnowsze dni.')

    return (
        last_db_data,
        adjusted_last_df_data,
        adjusted_today,
    )


def get_market_by_db_name(db_table_name, markets: list[Market]) -> Market:
    """
    Wyszukuje obiekt Market na podstawie nazwy tabeli w bazie danych.

    Funkcja przeszukuje globalną listę skonfigurowanych rynków i zwraca
    ten, którego nazwa tabeli w bazie danych (`db_table_name`) pasuje do
    podanego argumentu.

    Parameters
    ----------
    db_table_name : str
        Nazwa tabeli w bazie danych (np. 'dax'), która ma zostać
        odnaleziona.

    Returns
    -------
    Market
        Obiekt `Market`, który odpowiada podanej nazwie tabeli.

    Raises
    ------
    ValueError
        Jeśli na liście `markets` nie zostanie znaleziony żaden rynek
        z pasującą nazwą tabeli.

    Notes
    -----
    Funkcja do działania wymaga istnienia globalnej zmiennej `markets`,
    która zawiera listę wszystkich obiektów `Market`.

    """
    market = next(
            (
                market for market in markets
                if market.db_table_name == db_table_name
            ), None)

    if market is None:
        raise ValueError(
            f'Nie znaleziono rynku na podstawie nazwy tabeli {db_table_name}. '
            'Sprawdź pisownię.'
        )

    return market


if __name__ == '__main__':
    make_update_db_with_stooqpy()
