from functools import wraps
from datetime import date, timedelta
import psycopg2
import pandas as pd

from settings import DB_PARAMS


def read_txt_market_data(
        path_to_file: str,
        column_replacements: dict) -> pd.DataFrame:
    """Wczytuje dane z plików .csv pobranych ze stooq.pl."""
    # Reads the data
    df = pd.read_csv(
        path_to_file,
        usecols=[col for col in column_replacements.keys()],
        parse_dates=['<DATE>'],
    )
    # Inserts new column names
    df.rename(columns=column_replacements, inplace=True)
    # Konwertuje dane do formatu float
    cols_t_convert_t_float = [col for col in column_replacements.values()][-4:]
    df[cols_t_convert_t_float] = df[cols_t_convert_t_float].astype('float32')

    return df


def with_db_connection(db_params_key='db_params'):
    """
    Podstawowy DEKORATOR do zarządzania połączeniem z bazą danych.
    ---
    Warunek konieczny: funkcja dekorowana musi mieć argument docelowy
    'db_params' definiujący parametry łączenia z bazą danych. Ewentualnie
    nazwany inaczej, ale wówczas explicite wymieniony parametrach dekoratora
    i przypisany do argumentu `db_params_key`.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Odbiera argument'db_params'
            db_params = kwargs.get(db_params_key)
            if db_params is None:
                raise ValueError(
                    f"Błąd: brak '{db_params_key}' w argumentach"
                    f"'{func.__name__}'."
                )
            conn = None
            cur = None
            try:
                # Makes connection to the database
                conn = psycopg2.connect(**db_params)
                cur = conn.cursor()

                # Calls the main, decorated function
                result = func(*args, **kwargs, conn=conn, cur=cur)

                # Commits the transaction
                conn.commit()

                # Returns the result of the main, decorated function
                return result

            except Exception as ex:
                # Handles exceptions
                if conn:
                    conn.rollback()
                print(f"Błąd w '{func.__name__}': {ex}")
                raise

            finally:
                # Context manager clenas it all up by closing the connection
                if cur:
                    cur.close()
                if conn:
                    conn.close()

        return wrapper

    return decorator


@with_db_connection()
def create_multiple_tables(
    table_names: list,
    *,
    conn,
    cur,
    db_params: dict,
    unique_col_name: str = 'date',
):
    """
    Funkcja główna, tworzy tabele w bazie danych.
    ---
    Tworzy wielokrotne tabele w bazie danych PostgreSQL z listy nazw tabel
    'table_names' Defaultowo lista powinna być spisana w pliku settings.
    Aktualna jej nazwa (stan na 9 kwi 2025) to 'TABLE_NAMES_PSQL_INDIRECT'.
    """
    for table_name in table_names:
        # Cytuje nazwę tabeli, jeśli zawiera znaki specjalne lub spacje
        if not table_name.isalnum():
            quoted_table_name = f'"{table_name}"'
        else:
            quoted_table_name = table_name

        sql_command = f"""
            CREATE TABLE {quoted_table_name} (
                ticker VARCHAR(6),
                date DATE,
                open DOUBLE PRECISION,
                high DOUBLE PRECISION,
                low DOUBLE PRECISION,
                close DOUBLE PRECISION
            );
        """
        cur.execute(sql_command)
        print(f"Tabela '{table_name}' została utworzona.")

        # Tworzy unikalny indeks na kolumnie date
        sql_index = f"""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_{table_name}_date_unique
            ON {quoted_table_name}({unique_col_name});
        """
        cur.execute(sql_index)
        print(
            f"🔐 Indeks unikalny na kolumnie 'date' w tabeli '{table_name}'"
            f" został utworzony."
        )


def first_database_data_feed_from_dataframe_to_postgres(
    table_name: str,
    column_names: list,
    df: pd.DataFrame,
    *,
    conn,
    cur,
    db_params: dict,
):
    """
    Funkcja główna.
    ---
    Wstawia pierwsze dane do bazy danychPostgreSQL.
    """
    values_placeholder = ', '.join(['%s'] * len(column_names))
    sql = f'''
    INSERT INTO "{table_name}" ({", ".join(column_names)})
    VALUES ({values_placeholder})
    '''

    for index, row in df.iterrows():
        values = list(row[column_names])
        cur.execute(sql, values)


def upsert_database(
    path_to_file: str,
    column_replacements: dict,
    market_tickers: list,
    table_names: list,
    db_params: dict,
    column_names: list,
):
    """
    Funkcja pomocnicza.
    ---
    Reads data from txt file for many markets in one df.
    For every table and its ticker updates and inserts into database
    """
    # Reads data from txt file for many markets in one df.
    df = read_txt_market_data(
            path_to_file=path_to_file,
            column_replacements=column_replacements,
        )

    # For every table and its ticker updates and inserts into database
    for ticker, table_name in zip(market_tickers, table_names):
        df_ = df[df['ticker'] == ticker]

        if df_.empty:
            print(f"⚠️ Brak danych dla tickera {ticker}, pomijam.")
            continue

        upsert_df_to_psql(
            table_name=table_name,
            column_names=column_names,
            df=df_,
            db_params=db_params,
        )


@with_db_connection()
def upsert_df_to_psql(
    table_name: str,
    column_names: list,
    df: pd.DataFrame,
    conflict_cols: list = ['date'],
    *,
    conn,
    cur,
    db_params: dict
):
    """
    Funkcja główna.
    ---
    Inserts and Updates data from DataFrame into PostgreSQL database.
    """
    placeholders = ', '.join(['%s'] * len(column_names))
    updates = ', '.join(
        [f"{col} = EXCLUDED.{col}" for col in column_names if col not in conflict_cols]
    )
    print(f'📦 Przygotowanie danych do wstawienia do tabeli "{table_name}"...')
    # ON CONFLICT (date) — jeśli rekord z taką datą istnieje, zaktualizuj
    sql = f"""
        INSERT INTO "{table_name}" ({', '.join(column_names)})
        VALUES ({placeholders})
        ON CONFLICT ({conflict_cols[0]})
        DO UPDATE SET {updates};
    """

    for _, row in df.iterrows():
        values = [row[col] for col in column_names]
        cur.execute(sql, values)

    print(f"✅ Wstawiono dane do tabeli '{table_name}' z UPSERT.")
    return True


@with_db_connection()
def drop_multiple_tables(table_names: list, *, conn, cur, db_params: dict):
    """
    Funkcja główna.
    ---
    🧨 🧨 🧨
    Usuwa bezpowrotnie tabele z bazy danych PostgreSQL
    o nazwach podanych w liście 'table_names'.
    """
    for table_name in table_names:
        # Cytuje nazwę tabeli, jeśli zawiera znaki specjalne lub spacje
        if not table_name.isalnum():
            quoted_table_name = f'"{table_name}"'
        else:
            quoted_table_name = table_name

        cur.execute(f'DROP TABLE IF EXISTS {quoted_table_name};')
        print(
            f"Tabela {quoted_table_name} została usunięta z bazy danych "
            f"(jeśli istaniała)."
        )


@with_db_connection()
def last_table_date(table_name: str, *, conn, cur, db_params: dict) -> str:
    """
    Funkcja pomocnicza.
    ---
    Pobiera ostatni dzien z tabeli w bazie danych PostgreSQL. Przydatna do
    określania zakresu danych potrzebnych do pobrania ze stooq.pl
    w calu aktualizacji bazy danych o najnowsze kursy na pojedynczym rynku.
    """
    cur.execute(
        f"""
            SELECT MAX(date)
            FROM "{table_name}";
        """
    )

    return cur.fetchone()[0]


def find_date_from_which_update_is_needed(
        table_names: list,
        db_params: dict) -> list:
    """
    Funkcja główna.
    ---
    Generalizuje działanie funkcji pomocniczej `last_table_date`.
    Finds the date from which the database should be updated from stooq.pl.
    """
    latest_earilest_date = date.today() + timedelta(days=1)
    for table in table_names:
        last_date = last_table_date(
            table_name=table,
            db_params=db_params,
        )
        if last_date < latest_earilest_date:
            latest_earilest_date = last_date

    latest_earilest_date_shifted = latest_earilest_date - timedelta(days=1)

    print(
        f'Aktualizuj od: {latest_earilest_date_shifted} '
        f'sprawdzenie wykonane: {latest_earilest_date}'
    )

    return (latest_earilest_date_shifted, latest_earilest_date)


# FUNKCJE POMOCNICZE


@with_db_connection()
def check_if_connected(conn, cur, db_params: dict):
    cur.execute('SELECT 1')
    result = cur.fetchone()
    if result and result[0] == 1:
        print("✅ Połączenie z bazą danych działa prawidłowo.")
    else:
        print("⚠️ Coś poszło nie tak z testowym zapytaniem.")
    return result


if __name__ == '__main__':
    check_if_connected(db_params=DB_PARAMS)
