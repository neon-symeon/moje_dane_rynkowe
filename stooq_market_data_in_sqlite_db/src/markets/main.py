# -*- coding: utf-8 -*-
"""
Główny moduł aplikacji do pobierania, przetwarzania i zapisywania
danych rynkowych. Zawiera logikę do obsługi konfiguracji, interakcji
z systemem plików oraz operacji na bazie danych SQLite.
"""
# ###########################################################################
# ## IMPORTS
# ###########################################################################
from .db import create_multiple_tables
from .logic import (
    make_populate_database,
    make_update_db,
    find_update_date_range,
)
from .config import load_markets_data


# Ten blok wykona się tylko przy uruchomieniu z -m
if __name__ == '__main__':

    markets = load_markets_data()

    create_multiple_tables(markets=markets)

    # pipeline 1 - populate database
    print('\n--- populate database ---\n')
    markets = make_populate_database(markets=markets)

    # pipeline 2 - ustal wymagany zakres aktualizacji
    print('\n--- find database date range ---\n')
    find_update_date_range(markets)

    # # pipeline 3 - update database
    print('\n--- update database ---\n')
    make_update_db(markets=markets)
