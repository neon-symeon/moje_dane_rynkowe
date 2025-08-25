# -*- coding: utf-8 -*-
"""
Funkcje i dekoratory do obsługi bazy danych SQLite.

Zawiera narzędzia do zarządzania połączeniami z bazą, tworzenia i aktualizowa-
nia tabel, wstawiania danych oraz odczytu zawartości. Dekoratory db_connection
/db_cursor zapewniają automatyczne otwieranie i zamykanie połączeń, a funkcje
pomocnicze wspierają spójność schematu i ułatwiają operacje na wielu rynkach.
"""
# ###########################################################################
# ## IMPORTS
# ###########################################################################
from functools import wraps
import sqlite3

from datetime import date

import pandas as pd

from . import settings
from .models import Market


# ###########################################################################
# ## DECORATORS
# ###########################################################################
def with_db_write_connection():
    """
    Zarządza transakcyjnym połączeniem z bazą danych (zapis).

    Dekorator, który przyjmuje konfigurację połączenia przy definicji
    i opakowuje funkcję w pełną transakcję. Automatycznie otwiera
    połączenie, zatwierdza zmiany (commit) po sukcesie, wycofuje je
    (rollback) w razie błędu i zawsze zamyka połączenie.

    Parameters
    ----------
    None (settings.DB_PARAMS jest przekazywane wewnątrz funkcji)

    Returns
    -------
    function
        Funkcja dekorująca, która opakowuje oryginalną funkcję.

    Notes
    ------
    Konfiguracja DB_PARAMS jest pobierana automatycznie z pliku settings, co
    upraszcza wywołania funkcji. Bez settings system nie zadziała. DB_PARAMS
    zawiera Słownik konfiguracyjny zawierający klucz 'db_path' ze ścieżką do
    pliku bazy danych SQLite.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            db_params = settings.DB_PARAMS

            # mini kontrola danych na wejściu "bocznymi drzwiami" do funkcji.
            if not isinstance(db_params, dict) or 'db_path' not in db_params:
                raise ValueError(
                    "Błąd: Konfiguracja DB_PARAMS w pliku settings.py jest "
                    "nieprawidłowa lub nie zawiera klucza 'db_path'."
                )

            conn = None
            try:
                conn = sqlite3.connect(db_params['db_path'])
                cur = conn.cursor()
                result = func(*args, **kwargs, conn=conn, cur=cur)
                conn.commit()
                return result
            except Exception as ex:
                if conn:
                    conn.rollback()
                print(f"Błąd w '{func.__name__}': {ex}")
                raise
            finally:
                if conn:
                    conn.close()
        return wrapper
    return decorator


def with_db_read_connection():
    """
    Zarządza połączeniem z bazą danych w trybie tylko do odczytu.

    Dekorator, który przyjmuje konfigurację połączenia przy definicji.
    Otwiera połączenie, udostępnia je dekorowanej funkcji, a następnie
    zawsze je zamyka. Nie wykonuje operacji commit ani rollback.

    Parameters
    ----------
    None (settings.DB_PARAMS jest przekazywane wewnątrz funkcji)


    Returns
    -------
    function
        Funkcja dekorująca, która opakowuje oryginalną funkcję.

    Notes
    ------
    Konfiguracja DB_PARAMS jest pobierana automatycznie z pliku settings, co
    upraszcza wywołania funkcji. Bez settings system nie zadziała. DB_PARAMS
    zawiera Słownik konfiguracyjny zawierający klucz 'db_path' ze ścieżką do
    pliku bazy danych SQLite.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            db_params = settings.DB_PARAMS
            # mini kontrola danych na wejściu "bocznymi drzwiami" do funkcji.
            if not isinstance(db_params, dict) or 'db_path' not in db_params:
                raise ValueError(
                    "Błąd: Konfiguracja DB_PARAMS w pliku settings.py jest "
                    "nieprawidłowa lub nie zawiera klucza 'db_path'."
                )

            conn = None
            try:
                # Nawiązuje połączenie i tworzy kursor
                conn = sqlite3.connect(db_params['db_path'])
                cur = conn.cursor()

                # Wywołuje funkcję i zwraca jej wynik
                return func(*args, **kwargs, conn=conn, cur=cur)

            except sqlite3.Error as ex:
                # Obsługuje błędy specyficzne dla bazy danych
                print(f"Błąd odczytu z bazy danych w '{func.__name__}': {ex}")
                raise

            finally:
                # Zawsze zamyka połączenie
                if conn:
                    conn.close()

        return wrapper
    return decorator


# ###########################################################################
# ## DATABASE HELPER FUNCTIONS
# ###########################################################################
@with_db_read_connection()
def get_last_db_date_for_market(
    db_table_name: str, *, conn, cur
) -> date:
    """
    Zwraca pojedynczą, ostatnią datę dla wybranego rynku.

    Parameters
    ----------
    db_table_name: str
        nazwa tabeli w bazie danych

    Returns
    -------
    date.fromisoformat(result[0]) : date
        Najstarszą datę, czyli datę ostatniego wpisu do bazy
        danych.
    """
    try:
        cur.execute(f'SELECT MAX(date) FROM "{db_table_name}"')
        result = cur.fetchone()
        if result and result[0]:
            return date.fromisoformat(result[0])
    except sqlite3.OperationalError as ex:
        print(ex)


@with_db_read_connection()
def _get_last_db_dates_for_markets(
    markets: list[Market], *, conn, cur
) -> list[Market]:
    """
    Pobiera ostatnie daty dla listy rynków i aktualizuje obiekty.

    Funkcja iteruje przez listę obiektów `Market`, wykonuje zapytanie
    `SELECT MAX(date)` dla każdej powiązanej tabeli i uzupełnia
    atrybut `last_db_date` w każdym obiekcie.

    Parameters
    ----------
    markets : list[Market]
        Lista obiektów `Market`, które mają zostać zaktualizowane.
    conn : sqlite3.Connection
        Obiekt połączenia z bazą danych (wstrzykiwany przez dekorator).
    cur : sqlite3.Cursor
        Obiekt kursora bazy danych (wstrzykiwany przez dekorator).

    Returns
    -------
    markets : list[Market]
        Funkcja modyfikuje obiekty `Market` na liście.
    """
    for market in markets:
        try:
            cur.execute(f'SELECT MAX(date) FROM "{market.db_table_name}"')
            result = cur.fetchone()
            if result and result[0]:
                market.last_db_date = date.fromisoformat(result[0])
        except sqlite3.OperationalError as ex:
            print(ex)

    return markets


@with_db_read_connection()
def _db_get_tables(*, conn, cur) -> list[str]:
    """
    Zwraca listę tabel z bazy danych.

    Parameters
    ----------
    conn : sqlite3.Connection
        Obiekt połączenia z bazą danych (wstrzykiwany przez dekorator).
    cur : sqlite3.Cursor
        Obiekt kursora bazy danych (wstrzykiwany przez dekorator).

    Returns
    -------
    list[str]
        Lista nazw tabel istniejących w bazie danych.
    """
    cur.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """
    )
    return [item[0] for item in cur.fetchall()]


@with_db_write_connection()
def _upsert_df_to_sqlite(
    db_table_name: str,
    df: pd.DataFrame,
    column_names: list = settings.COLUMNS_IN_DF_AND_SQL,
    report: bool = False,
    conflict_cols: list = ['date'],
    *, conn, cur,
):
    """
    Jedna z podstawowych funkcji. Wstawia lub aktualizuje wiersze w tabeli na
    podstawie DataFrame.

    Wykonuje operację "UPSERT" (`INSERT ... ON CONFLICT DO UPDATE`),
    która wstawia nowe wiersze lub aktualizuje istniejące, jeśli
    wystąpi konflikt na kluczu głównym (kolumna `date`).

    Parameters
    ----------
    table_name : str
        Nazwa tabeli docelowej w bazie danych.
    column_names : list[str]
        Lista nazw kolumn, które mają zostać uwzględnione w operacji.
    df : pd.DataFrame
        DataFrame zawierający dane do wstawienia/aktualizacji.
    conn : sqlite3.Connection
        Obiekt połączenia z bazą danych (wstrzykiwany przez dekorator).
    cur : sqlite3.Cursor
        Obiekt kursora bazy danych (wstrzykiwany przez dekorator).

    Returns
    -------
    int
        Liczba wierszy zmodyfikowanych przez operację.
    """
    placeholders = ', '.join(['?'] * len(column_names))
    updates = ', '.join(
        [
            f"{col} = excluded.{col}" for col in column_names
            if col not in conflict_cols
        ]
    )
    sql = f"""
        INSERT INTO "{db_table_name}" ({', '.join(column_names)})
        VALUES ({placeholders})
        ON CONFLICT ({conflict_cols[0]})
        DO UPDATE SET {updates};
    """

    # Przygotowuje dane do insertu
    data_to_insert = df[column_names].to_numpy().tolist()

    # 'Hurtowe' zasielenie bazy
    cur.executemany(sql, data_to_insert)

    if report:
        print(
            f'✅ Zaktualizowano {cur.rowcount} wierszy w tabeli {db_table_name}.'
        )
    return cur.rowcount


@with_db_write_connection()
def create_multiple_tables(
    markets: list[Market],
    *, conn, cur, unique_col_name: str = 'date',
):
    """
    Tworzy w bazie danych wiele tabel na podstawie podanej listy rynków:
    markets.

    Tworzy tabele i

    Dla każdej nazwy z listy `db_table_names` wykonuje polecenie
    `CREATE TABLE IF NOT EXISTS`, definiując standardowy schemat
    dla danych rynkowych. Kolumna `date` jest ustawiana jako
    klucz główny, co automatycznie tworzy na niej unikalny indeks.

    Parameters
    ----------
    markets : list[Market]
        Lista analizowanych rynkow, z których pobierana jest lista tabel.
    conn : sqlite3.Connection
        Obiekt połączenia z bazą danych (wstrzykiwany przez dekorator).
    cur : sqlite3.Cursor
        Obiekt kursora bazy danych (wstrzykiwany przez dekorator).

    Returns
    -------
    dict
        Zwraca słownik z informacją, czy dana tabela już istniała, czy została
        utworzona.
    """
    creation_status = {}
    table_names = [market.db_table_name for market in markets]

    for table_name in table_names:
        # sprawdza czy tabela już istnieje
        cur.execute(
            f"""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='{table_name}'
            """
        )
        table_existed_before = cur.fetchone() is not None

        # wykonuje bezpieczne polecenie tworzenia tabeli
        sql_command = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                ticker TEXT,
                date DATE PRIMARY KEY,
                open REAL,
                high REAL,
                low REAL,
                close REAL
            );
        """
        cur.execute(sql_command)

        # zwraca info o ingerencji w db
        if table_existed_before:
            creation_status[table_name] = 'istniała'
            print(f"🛈  INFO: Tabela '{table_name}' już istnieje.")
        else:
            creation_status[table_name] = 'utworzona'
            print(
                f"✅ SUKCES: Tabela '{table_name}' została nowo utworzona."
            )

    return creation_status


@with_db_read_connection()
def read_market_data_from_db(
    market: Market, *, conn, cur
) -> pd.DataFrame:
    """
    Wczytuje wszystkie dane dla danego rynku z bazy do DataFrame.

    Funkcja wykonuje zapytanie SQL `SELECT *` do tabeli powiązanej
    z podanym obiektem `Market`. Wynik zapytania jest zwracany jako
    kompletny DataFrame biblioteki pandas.

    Parameters
    ----------
    market : Market
        Obiekt `Market`, dla którego mają zostać wczytane dane.
        Nazwa tabeli jest pobierana z atrybutu `market.table_name`.
    conn : sqlite3.Connection
        Obiekt połączenia z bazą (wstrzykiwany przez dekorator).
    cur : sqlite3.Cursor
        Obiekt kursora bazy (wstrzykiwany przez dekorator).

    Returns
    -------
    pd.DataFrame
        DataFrame zawierający wszystkie historyczne dane dla danego rynku.

    Raises
    ------
    Exception
        Rzuca ogólny wyjątek, jeśli operacja odczytu z bazy danych
        (np. przez `pd.read_sql_query`) nie powiedzie się. Może to być
        spowodowane np. brakiem tabeli.

    """
    # Konfiguruje
    table_to_read = market.db_table_name

    try:
        # Definiuje zapytanie do bazy
        sql_query = (
            f"""
            SELECT * FROM {table_to_read};
            """
        )
        # Wczytuje dane z db do df
        df = pd.read_sql_query(sql_query, conn)
    except Exception as ex:
        print(
            f'❌ Wystąpił błąd: {ex} \n df dla rynku {table_to_read} '
            'nie został wczytany.'
        )
        raise Exception

    return df
