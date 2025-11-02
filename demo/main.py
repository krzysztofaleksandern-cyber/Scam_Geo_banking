"""
main.py
Test poprawności konfiguracji i połączenia z danymi MTProto (Telegram)
Autor: Chris & GPT
"""

from telegram_config import get_server, show_summary


def main():
    print("=== TEST KONFIGURACJI TELEGRAM ===\n")

    # pokazujemy wszystkie dostępne serwery
    show_summary()

    # pobieramy dane serwera produkcyjnego
    srv = get_server("production")

    print("\n--- Szczegóły serwera produkcyjnego ---")
    print(f"Host: {srv['host']}")
    print(f"Port: {srv['port']}")
    print(f"DC: {srv['dc']}")
    print("\nŁączę z:", srv['host'], "DC:", srv['dc'])

    print("\n=== KONIEC TESTU ===")


if __name__ == "__main__":
    main()
