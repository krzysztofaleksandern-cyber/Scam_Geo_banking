"""
telegram_config.py
Bezpieczny moduÅ‚ konfiguracyjny dla poÅ‚Ä…czeÅ„ MTProto (Telegram).
Autor: Chris & GPT
Wersja: 3.2_PRO
"""

CONFIG = {
    "fcm_credentials": None,
    "mtproto_servers": {
        "test": {
            "host": "149.154.167.40",
            "port": 443,
            "dc": 2,
            "public_key": """-----BEGIN RSA PUBLIC KEY-----
MIIBCgKCAQEAyMEdY1aR+sCR3ZSJrtztKTKqigvO/vBfqACJLZtS7QMgCGXJ6XIR
yy7mx66W0/sOFa7/1mAZtEoIokDP3ShoqF4fVNb6XeqgQfaUHd8wJpDWHcR2OFwv
plUUI1PLTktZ9uW2WE23b+ixNwJjJGwBDJPQEQFBE+vfmH0JP503wr5INS1poWg/
j25sIWeYPHYeOrFp/eXaqhISP6G+q2IeTaWTXpwZj4LzXq5YOpk4bYEQ6mvRq7D1
aHWfYmlEGepfaYR8Q0YqvvhYtMte3ITnuSJs171+GDqpdKcSwHnd6FudwGO4pcCO
j4WcDuXc2CTHgH8gFTNhp/Y8/SpDOhvn9QIDAQAB
-----END RSA PUBLIC KEY-----"""
        },
        "production": {
            "host": "149.154.167.50",
            "port": 443,
            "dc": 2,
            "public_key": """-----BEGIN RSA PUBLIC KEY-----
MIIBCgKCAQEA6LszBcC1LGzyr992NzE0ieY+BSaOW622Aa9Bd4ZHLl+TuFQ4lo4g
5nKaMBwK/BIb9xUfg0Q29/2mgIR6Zr9krM7HjuIcCzFvDtr+L0GQjae9H0pRB2OO
62cECs5HKhT5DZ98K33vmWiLowc621dQuwKWSQKjWf50XYFw42h21P2KXUGyp2y/
+aEyZ+uVgLLQbRA1dEjSDZ2iGRy12Mk5gpYc397aYp438fsJoHIgJ2lgMv5h7WY9
t6N/byY9Nw9p21Og3AoXSL2q/2IJ1WRUhebgAdGVMlV1fkuOQoEzR7EdpqtQD9Cs
5+bfo3Nhmcyvk5ftB0WkJ9z6bNZ7yxrP8wIDAQAB
-----END RSA PUBLIC KEY-----"""
        }
    },
    "notes": "Dane publiczne dla DC 2 (Test i Production). FCM credentials naleÅ¼y uzupeÅ‚niÄ‡ oddzielnie."
}


def get_server(mode: str = "production") -> dict:
    """
    Zwraca konfiguracjÄ™ serwera MTProto w zaleÅ¼noÅ›ci od trybu.
    :param mode: "test" lub "production"
    :return: dict z host, port, dc, public_key
    """
    if mode not in CONFIG["mtproto_servers"]:
        raise ValueError(f"Nieznany tryb: {mode}. DostÄ™pne: {list(CONFIG['mtproto_servers'].keys())}")
    return CONFIG["mtproto_servers"][mode]


def show_summary():
    """Wypisuje krÃ³tkie info o aktualnych ustawieniach."""
    print("=== MTProto Config ===")
    for name, data in CONFIG["mtproto_servers"].items():
        print(f"[{name.upper()}] {data['host']}:{data['port']}  DC{data['dc']}")


if __name__ == "__main__":
    # szybki test uruchomienia
    show_summary()
    print("\nProduction server:")
    print(get_server("production"))




