# -*- coding: utf-8 -*-
"""
Punkt wejścia aplikacji przy uruchamianiu jako moduł (`python -m markets`).

Importuje i uruchamia funkcję główną CLI, umożliwiając obsługę
argumentów z wiersza poleceń i delegowanie zadań do właściwych modułów.
"""

# stooq_market_data_in_sqlite_db/src/__main__.py
from .cli import main

if __name__ == "__main__":
    main()
