# -*- coding: utf-8 -*-
"""
Interfejs wiersza poleceń (CLI) dla aplikacji.

Definiuje komendy dostępne dla użytkownika (np. inicjalizacja bazy,
populacja danymi, aktualizacja, podgląd zakresu dat) oraz mapuje je
na odpowiednie funkcje logiki biznesowej. Umożliwia wywoływanie
programu bezpośrednio z powłoki systemowej.
"""

# stooq_market_data_in_sqlite_db/src/markets/cli.py
import argparse
from .config import load_markets_data
from .db import create_multiple_tables
from .logic import (
    make_populate_database,
    make_update_db,
    find_update_date_range,
)


def _run_full_pipeline(markets):
    create_multiple_tables(markets=markets)
    make_populate_database(markets=markets)
    make_update_db(markets=markets)


def main():
    parser = argparse.ArgumentParser(prog="markets")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init")       # tworzy tabele
    sub.add_parser("populate")   # duża aktualizacja
    sub.add_parser("update")     # mała aktualizacja
    sub.add_parser("range")      # pokaż sugerowany zakres
    sub.add_parser('full')       # wykonaj cały pipeline init→populate→update

    args = parser.parse_args()

    markets = load_markets_data()
    if args.cmd == "init":
        create_multiple_tables(markets=markets)
    elif args.cmd == "populate":
        make_populate_database(markets=markets)
    elif args.cmd == "update":
        make_update_db(markets=markets)
    elif args.cmd == "range":
        find_update_date_range(markets)
    elif args.cmd == "full":
        _run_full_pipeline(markets=markets)
