# -*- coding: utf-8 -*-
"""
Ładowanie i walidacja konfiguracji aplikacji z pliku YAML.

Udostępnia funkcje do wczytywania listy rynków i ich parametrów z pliku konfi-
guracyjnego `setup.yaml`, walidacji poprawności danych oraz przekształcania
ich w obiekty klasy `Market`.
"""
# ###########################################################################
# ## IMPORTS
# ###########################################################################
from ruamel.yaml import YAML

from . import settings
from .models import Market
from .db import (
    _get_last_db_dates_for_markets,
)
from .fs import (
    _build_file_path_map,
)


# ###########################################################################
# ## CONFIGURATION FUNCTIONS
# ###########################################################################
def _fetch_markets_data_from_yaml(
        yaml_params: dict = settings.YAML_PARAMS
) -> dict:
    """
    Wczytuje i waliduje konfigurację rynków z pliku YAML.

    Funkcja jest odpowiedzialna za odczytanie pliku konfiguracyjnego,
    którego ścieżka jest zdefiniowana w `YAML_PARAMS`. Parsuje zawartość
    przy użyciu biblioteki `ruamel.yaml` i sprawdza, czy plik nie jest pusty.

    Parameters
    ----------
    yaml_params : dict, optional
        Słownik konfiguracyjny zawierający klucz 'yaml_path'.
        Jeśli nie zostanie podany, domyślnie używana jest globalna
        konfiguracja `YAML_PARAMS` z modułu `settings`.

    Returns
    -------
    list[dict]
        Lista słowników, gdzie każdy słownik reprezentuje jeden rynek
        zdefiniowany przez użytkownika w pliku konfiguracyjnym.

    Raises
    ------
    FileNotFoundError
        Jeśli plik, do którego prowadzi ścieżka w `yaml_params`, nie
        zostanie znaleziony na dysku.
    ValueError
        Jeśli słownik `yamls_params` nie zawiera klucza, jeśli plik
        konfiguracyjny jest pusty lub jego zawartość jest niepoprawna.
    Exception
        W przypadku ogólnych błędów parsowania pliku YAML.

    Notes
    -----
    Funkcja powinna być ściśle powiązana z globalną konfiguracją `YAML_PARAMS`
    zdefiniowaną w module `settings.py`, skąd pobiera ścieżkę do pliku.
    """
    # Inicjalizuje obiekt YAML (dba o formatowanie).
    yaml = YAML()
    yaml.preserve_quotes = True

    # Bezpiecznie pobiera ścieżkę do pliku konfiguracyjnego.
    yaml_path = yaml_params.get('yaml_path')

    if yaml_path is None:
        raise ValueError(
            '\n\n⚠️  Błąd konfiguracji: Słownik `yaml_params` musi zawierać '
            'klucz "yaml_path".'
        )

    yaml_raw_data = []
    try:
        with open(yaml_path, 'r') as f:
            yaml_raw_data = yaml.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(
            f'\n\n⚠️  Plik konfiguracyjny: "{yaml_path}" nie istnieje.\n'
            f'File exists: {yaml_path.exists()}\n'
            f'Path exists: {yaml_path.is_file()}'
        )
    except Exception as ex:
        raise Exception(
            f'❌ BŁĄD: Nie można wczytać pliku YAML {yaml_path}:\n    {ex}'
        )

    if not yaml_raw_data:
        raise ValueError(
            '\n\n⚠️  Plik konfiguracyjny jest pusty lub nie został poprawnie '
            'wczytany. Aplikacja nie może kontynuować bez tych danych.'
        )

    return yaml_raw_data


# TODO: gemini z tej i wcześniejszej funcji tworzy jedną zgrabną ale gubi
# proces walidacyjny.
def load_markets_from_yaml():
    """
    Tworzy listę obiektów Market ze surowych danych YAML.

    Przekształca listę słowników wczytaną z pliku konfiguracyjnego
    YAML w listę w pełni zainicjalizowanych obiektów `Market`.

    Parameters
    ----------
    yaml_raw_data : list[dict]
        Lista słowników, gdzie każdy słownik reprezentuje jeden rynek.

    Returns
    -------
    list[Market]
        Lista obiektów `Market` gotowa do dalszego przetwarzania.
    """
    yaml_data = _fetch_markets_data_from_yaml()

    #  Tworzy objekty Market z danych z YAML w liście markets
    markets = []
    for market_data in yaml_data:
        market = Market(**market_data)
        markets.append(market)

    return markets


def load_markets_data() -> list[Market]:
    """
    Wczytuje dane o obserwowanych rynkach i wzbogaca je o ścieżki
    do plików danych.

    Główna funkcja orkiestrująca, która koordynuje całym procesem
    przygotowania konfiguracji. Odpowiada za wczytanie danych z pliku YAML,
    przeszukanie dysku w poszukiwaniu odpowiednich plików z danymi, a następnie
    połączenie tych dwóch źródeł w jedną, spójną listę obiektów `Market`.

    Parameters
    ----------
    None

    Returns
    -------
    list[Market]
        Lista obiektów `Market`, gdzie każdy obiekt jest w pełni uzupełniony
        o ścieżkę do pliku z danymi (`file_path`), jeśli taki plik został
        znaleziony.

    Raises
    ------
    FileNotFoundError
        Rzucany przez `read_data_from_yaml_config_file`, jeśli plik
        konfiguracyjny YAML nie zostanie znaleziony.
    ValueError
        Rzucany przez `read_data_from_yaml_config_file`, jeśli plik
        konfiguracyjny YAML jest pusty.

    """
    markets = load_markets_from_yaml()

    # Dodaje ścieżki do dużych danych an dysku
    file_path_map = _build_file_path_map()
    if file_path_map == {}:
        print(
            'load_markets_data.'
            '🛈  Na dysku nie ma ścieżek do dużych plików z danymi.'
        )
    else:
        for market in markets:
            if market.txt_file_name in file_path_map:
                market.file_path = file_path_map[market.txt_file_name]
            else:
                print(
                    '⚠️  nie znalazłem dopasowania ścieżki do dużego pliku z '
                    f'danymi dla {market.name}.'
                )

    # Dodaje daty 'last_db_date' z bazy danych do obiektów Market
    # w liście markets
    markets = _get_last_db_dates_for_markets(markets=markets)

    # Zwraca zaktualizowane rynki
    return markets
