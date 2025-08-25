# -*- coding: utf-8 -*-
"""
Definicje modeli danych używanych w aplikacji.

Zawiera klasę `Market` reprezentującą rynek wraz z metodami pomocniczymi
do generowania nazw tabel w bazie danych oraz nazw plików z danymi źródłowymi.
Moduł ten stanowi warstwę abstrakcji między danymi konfiguracyjnymi a logiką
aplikacji.
"""
# ###########################################################################
# ## IMPORTS
# ###########################################################################
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


# ###########################################################################
# ## CLASSES
# ###########################################################################
@dataclass
class Market:
    """
    Reprezentuje pojedynczy rynek finansowy w aplikacji.

    Klasa przechowuje wszystkie kluczowe informacje dotyczące jednego rynku,
    włączając w to jego identyfikatory, nazwy, a także dynamicznie
    odnalezione ścieżki do plików z danymi oraz daty ostatniej
    aktualizacji.

    Attributes
    ----------
    number : int
        Liczba porządkowa z pliku konfiguracyjnego, używana do sortowania.
    ticker : str
        Unikalny identyfikator rynkowy (np. '^DAX', 'WIG20').
    name : str | None
        Czytelna nazwa rynku, ustalana przez użytkownika.
    file_path : Path | None, optional
        Ścieżka do pliku z danymi historycznymi dla tego rynku.
        Uzupełniana dynamicznie przez funkcję `load_market_config`.
    last_db_date : date | None, optional
        Data ostatniego wpisu dla tego rynku w bazie danych.
    last_txt_big_date : date | None, optional
        Data ostatniego wpisu w dużym pliku aktualizacyjnym dla tego rynku.
    last_txt_small_date: date | None, optional
        Data ostatniego wpisu w małym pliku aktualizacyjnym dla tego rynku.

    """
    number: int
    ticker: str
    name: str | None = field(default=None)
    file_path: Path | None = field(default=None, repr=False)
    last_db_date: date | None = field(default=None, repr=False)
    # te daty będą do automatycznego obliczenia.
    last_txt_big_date: date | None = field(
        default=None,
        repr=False,
    )
    # last_txt_small_date: date | None = field(default=None, repr=False)

    @property
    def db_table_name(self) -> str:
        """Zwraca nazwę tabeli w bazie danych (np. 'dax')."""
        return self.ticker.lower().replace('^', '').replace('.', '_')

    @property
    def txt_file_name(self) -> str:
        """Zwraca oczekiwaną nazwę pliku z danymi (np. '^dax.txt')."""
        return self.ticker.lower() + '.txt'
