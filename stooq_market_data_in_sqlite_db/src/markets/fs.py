# -*- coding: utf-8 -*-
"""
Operacje na systemie plików związane z danymi rynkowymi.

Odpowiada za budowanie map ścieżek do plików, wczytywanie danych z plików teks-
towych, ustalanie dat granicznych oraz przygotowanie danych do aktualizacji ba-
zy. Zapewnia spójny dostęp do źródeł danych w formacie TXT.
"""
# ###########################################################################
# ## IMPORTS
# ###########################################################################
from platformdirs import user_downloads_path  # syst. ścieżka do Downloads
from pathlib import Path
import pandas as pd
from datetime import date

from . import settings
# from .logic import (
#     find_update_date_range
# )


# ###########################################################################
# ## FILE SYSTEM HELPER FUNCTIONS
# ###########################################################################
def _read_txt_single_market_data(path_to_file: str) -> pd.DataFrame:
    """
    Wczytuje i przygotowuje dane z pojedynczego pliku .txt.

    Funkcja wczytuje dane rynkowe z pliku tekstowego (format: stooq.pl),
    zmienia nazwy kolumn zgodnie z konfiguracją, konwertuje typy danych
    numerycznych na `float32` oraz formatuje kolumnę daty na string
    w formacie ISO 'YYYY-MM-DD'.

    Parameters
    ----------
    path_to_file : Path
        Ścieżka do pliku `.txt` z danymi.

    Returns
    -------
    pd.DataFrame
        DataFrame gotowy do zapisu w bazie danych.
    """
    column_replacements = settings.COLUMN_NAMES_REPLACEMENTS_FOR_DF

    # Wczytuje dane z pliku csv
    df = pd.read_csv(
        path_to_file,
        usecols=[col for col in column_replacements.keys()],
        parse_dates=['<DATE>'],
    )

    # Nadpisuje / dodaje i nadaje nazwy kolumn
    df.rename(columns=column_replacements, inplace=True)

    # Konwertuje dane do formatu float
    cols_t_convert_t_float = [col for col in column_replacements.values()][-4:]
    df[cols_t_convert_t_float] = df[cols_t_convert_t_float].astype('float32')

    # Konwertuje daty na stringi
    df['date'] = df['date'].dt.strftime('%Y-%m-%d')

    return df


def _get_last_date_from_big_txt(path_to_file: Path) -> date | None:
    """
    Wczytuje plik .txt i zwraca najnowszą datę.

    Parameters
    ----------
    path_to_file : Path | None
        Ścieżka do pliku z danymi. Może być None.

    Returns
    -------
    date | None
        Najnowsza data znaleziona w pliku jako obiekt `datetime.date`
        lub `None`, jeśli plik nie istnieje lub jest pusty.
    """
    if not path_to_file or not path_to_file.exists():
        return None

    df = _read_txt_single_market_data(path_to_file)

    if not df.empty and 'date' in df.columns:
        # Konwertuje z powrotem na obiekty daty na potrzeby porównania
        return pd.to_datetime(df['date']).max().date()

    return None


def _build_file_path_map() -> dict[str, Path]:
    """
    Przeszukuje dysk i tworzy mapowanie: nazwa_pliku -> pełna_ścieżka.

    Funkcja skanuje podkatalogi systemowego folderu Pobrane/Downloads
    w poszukiwaniu folderów o nazwie 'data'. Następnie rekursywnie
    znajduje wszystkie pliki .txt w tych folderach i tworzy z nich słownik.

    Parameters
    ----------
    None

    Returns
    -------
    dict[str, Path]
        Słownik, w którym kluczem jest nazwa plik, a wartością jest pełny
        obiekt `pathlib.Path` do tego pliku.Jeśli na dysku nie ma plików
        .txt z danymi, funkcja zwraca pusty dict `{}`.
    """
    downloads_dir = user_downloads_path()
    file_path_map = {
        path.name: path
        for data_dir in downloads_dir.glob('*/data') if data_dir.is_dir()
        for path in data_dir.rglob('*.txt')
    }

    return file_path_map


def _get_file_path_to_update() -> list[Path]:
    """
    Wyszukuje najnowszyt plik źródłowy do aktualizacji.

    Funkcja przeszukuje systemowy folder Pobrane/Downloads w poszukiwaniu
    plików pasujących do wzorca `dane_d*.txt`. Znalezione pliki są następnie
    sortowane na podstawie ich czasu ostatniej modyfikacji w porządku
    malejącym, i najnowszy z nich zwracany.

    Parameters
    ----------
    None

    Returns
    -------
    Path
        Obiekt `pathlib.Path`, reprezentujący znaleziony najnowszy plik
        lub None, jesli pliku nie ma na dysku w oczekiwanej lokalizacji.

    Notes
    -----
    Funkcja do działania wymaga dostępu do systemu plików. Lokalizacja
    folderu Pobrane jest odnajdywana automatycznie za pomocą biblioteki
    `platformdirs`.

    """
    global markets

    downloads_dir = user_downloads_path()
    search_pattern = 'dane_d*.txt'

    found_files = list(downloads_dir.glob(search_pattern))

    sorted_files = sorted(
        found_files,
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    response = sorted_files[0] if sorted_files else None

    if response is None:
        print(
            'Brak pliku źródłowego do data update.'
            # ' Pobierz dane za okres'
            # f'{find_update_date_range(markets)}'
        )

    return response


def _calculate_last_df_data(market_df: pd.DataFrame) -> date | None:
    """
    Odnajduje najnowszą datę w podanym obiekcie DataFrame.

    Funkcja analizuje kolumnę 'date' w DataFrame, aby znaleźć
    maksymalną (najpóniejszą) datę. Przed wykonaniem operacji
    upewnia się, że DataFrame nie jest pusty i zawiera wymaganą kolumnę.

    Parameters
    ----------
    market_df : pd.DataFrame
        DataFrame zawierający kolumnę 'date' do przeszukania.

    Returns
    -------
    date | None
        Najnowsza data znaleziona w DataFrame jako obiekt `datetime.date`
        lub `None`, jeśli DataFrame jest pusty lub nie zawiera
        kolumny 'date'.
    """
    if not market_df.empty and 'date' in market_df.columns:
        # Konwertuje z powrotem na obiekty daty na potrzeby porównania
        return pd.to_datetime(market_df['date']).max().date()

    return None
