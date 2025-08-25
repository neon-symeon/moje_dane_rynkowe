# -*- coding: utf-8 -*-
"""
Ustawienia aplikacji i parametry domyślne.

Przechowuje:
  - ścieżki do plików bazy danych,
  - nazwy plików konfiguracyjnych, oraz
  - mappingi dla kolumn.

Wspólne źródło konfiguracji dla wszystkich modułów aplikacji.
"""
from pathlib import Path


# ###########################################################################
# ## DANE KONFIGURACYJNE - dostarczane przez usera w pliku yaml
# ###########################################################################


# Plik YAML (domyslnie znajduje się w głównym folderze projektu)
YAML_NAME = 'setup.yaml'
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

YAML_PARAMS = {'yaml_path': PROJECT_ROOT / YAML_NAME}


# ###########################################################################
# ## BAZA DANYCH - NAZWA, LOKALIZACJA BAZY, NAZWY TABEL
# ###########################################################################


# Nazwa bazy danych, w której gromadzone sa dane rynkowe
DATABASE_NAME = 'notowania.sqlite3'
# Lokalizacja bazy danych (domyślnie w głównym folderze projektu)
DATABASE_PATH = Path(__file__).resolve().parent.parent.parent

DB_PARAMS = {
    # Buduje ścieżkę do pliku bazy danych, który ma znajdować się
    # w katalogu nadrzędnym
    'db_path': DATABASE_PATH / DATABASE_NAME
}

# **STRUKTURA TABLIC BAZY DANYCH I DATAFRAME PANDAS**

# Wybrane kolumny z dataframe'u pandasa do bazy danych.
COLUMN_NAMES_REPLACEMENTS_FOR_DF = {
    '<TICKER>': 'ticker',
    '<DATE>': 'date',
    '<OPEN>': 'open',
    '<HIGH>': 'high',
    '<LOW>': 'low',
    '<CLOSE>': 'close',
    # '<VOL>': 'volume',
    # '<OPENINT>': 'open_int'
}

# Nazwy kolumn do db
COLUMNS_IN_DF_AND_SQL = list(COLUMN_NAMES_REPLACEMENTS_FOR_DF.values())

# ###########################################################################
# ## STOOQPY - pobieranie danych przez API stooq
#   - wymagany zalogowany użytkownik,
#   - dane gorszej jakości
# ###########################################################################

# PATHS IN STOOQPY
PATH_BASE = 'https://stooq.com/q/d/l/'
