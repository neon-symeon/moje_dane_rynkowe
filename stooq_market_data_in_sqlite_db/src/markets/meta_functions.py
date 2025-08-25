import inspect
import re


# pobiera i normalizuje pojedyncze docstringi.
def get_func_docstring(func):
    """
    Pobiera i normalizuje dosctringa z funkcji.
    ---
    Narzędzie pomocnicze do pracy z kodem, z rekonstrukcją i budowaniem
    zależności między funkcjami.
    """
    # Wczytuje treść docstringa z funkcji
    txt = inspect.getdoc(func)
    # Normalizuje spacje
    txt = re.sub(r'\s+', ' ', txt)
    # Usuwa zbędne przecież kreski
    txt = txt.replace('-', '')
    # Bolduje nagłówki sekcji dosctringa
    keywords_to_bold = ['Parameters', 'Returns', 'Raises', 'Notes']
    for keyword in keywords_to_bold:
        txt = txt.replace(keyword, f'**{keyword}**')

    # Drukuje oczyszczony tekst docstringa.
    print('\n', txt, '\n')

    # Zwraca oczyszczony tekst docstringa.
    return txt


if __name__ == '__main__':
    pass
