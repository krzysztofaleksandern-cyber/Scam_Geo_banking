# src/scamgeo_banking/cli/app.py
from __future__ import annotations

from pathlib import Path
import io
import zipfile
from datetime import datetime
from typing import List

import typer
from rich.console import Console

# Spójne API z scan.py
from .scan import (
    scan_web_targets,
    sweep_keywords,
    scan_ads,
    write_csv,
)

console = Console()
cli = typer.Typer(
    help="Scam_Geo Banking CLI",
    add_completion=False,
    no_args_is_help=True,
)

# ─── Pomocnicze echo ───────────────────────────────────────────────────────────

def _echo_ok(path: Path, n: int) -> None:
    typer.secho(f"OK: {n} rekordów → {path.as_posix()}", fg=typer.colors.GREEN)

def _echo_alerts(rows: List[dict]) -> None:
    scam = sum(1 for r in rows if r.get("label") == "scam")
    watch = sum(1 for r in rows if r.get("label") == "watch")
    typer.secho(f"ALERTS: scam={scam}, watch={watch}", fg=typer.colors.YELLOW)

# ─── Komendy ──────────────────────────────────────────────────────────────────

@cli.command("version", help="Wypisz wersję narzędzia.")
def version() -> None:
    console.print("Scam_Geo Banking v0.1.0")

@cli.command("scan-web", help="Skan źródeł publicznych (YT/TT/FB – stub/feeds) i zapis do CSV.")
def scan_web(
    targets: str = typer.Option(..., "-t", "--targets", help='Lista: "yt:<id/handle>, tt:<handle>, fb:<page>" (comma-separated)'),
    out: Path = typer.Option(Path("./out"), "-o", "--out", help="Katalog wyjściowy"),
) -> None:
    out.mkdir(parents=True, exist_ok=True)
    parsed_targets = [x.strip() for x in targets.split(",") if x.strip()]
    rows = scan_web_targets(parsed_targets, out)
    csv_path = out / "webscan_scored.csv"
    write_csv(csv_path, rows)
    _echo_ok(csv_path, len(rows))
    _echo_alerts(rows)
    typer.secho(f"OK: zapisano → {csv_path.as_posix()}", fg=typer.colors.GREEN)

@cli.command("sweep", help="Skan fraz w wyszukiwarce (stub) i zapis do CSV.")
def sweep(
    keywords: str = typer.Option(..., "-k", "--keywords", help='Frazy/zdania, comma-separated, np. "binance bonus, t.me/bot"'),
    out: Path = typer.Option(Path("./out"), "-o", "--out", help="Katalog wyjściowy"),
) -> None:
    out.mkdir(parents=True, exist_ok=True)
    qs = [x.strip() for x in keywords.split(",") if x.strip()]
    rows = sweep_keywords(qs, out)
    csv_path = out / "webkw_scored.csv"
    write_csv(csv_path, rows)
    _echo_ok(csv_path, len(rows))
    _echo_alerts(rows)
    typer.secho(f"OK: zapisano → {csv_path.as_posix()}", fg=typer.colors.GREEN)

@cli.command("ads", help="Pseudo-inspekcja reklam (stub) i zapis do CSV.")
def ads(
    targets: str = typer.Option(..., "-t", "--targets", help='Tak jak w scan-web, np. "yt:UC_x5..., tt:some_handle, fb:narodowy.bank.kosmiczny"'),
    out: Path = typer.Option(Path("./out"), "-o", "--out", help="Katalog wyjściowy"),
) -> None:
    out.mkdir(parents=True, exist_ok=True)
    parsed_targets = [x.strip() for x in targets.split(",") if x.strip()]
    rows = scan_ads(parsed_targets, out)
    csv_path = out / "webads_scored.csv"
    write_csv(csv_path, rows)
    _echo_ok(csv_path, len(rows))
    _echo_alerts(rows)
    typer.secho(f"OK: zapisano → {csv_path.as_posix()}", fg=typer.colors.GREEN)

@cli.command("package", help="Spakuj wskazane CSV do ZIP (manifest + pliki).")
def package_cmd(
    inputs: str = typer.Option(..., "-i", "--inputs", help="Lista plików CSV rozdzielona przecinkami"),
    out: Path = typer.Option(Path("./out"), "-o", "--out", help="Katalog wyjściowy"),
    zip_path: Path = typer.Option(Path("./out/web_evidence.zip"), "--zip", help="Ścieżka do ZIP"),
) -> None:
    out.mkdir(parents=True, exist_ok=True)
    files = [Path(p.strip()) for p in inputs.split(",") if p.strip()]
    missing = [str(p) for p in files if not p.exists()]
    if missing:
        typer.secho(f"ERR: brak plików: {missing}", fg=typer.colors.RED)
        raise typer.Exit(code=2)

    manifest = io.StringIO()
    manifest.write("Scam_Geo Banking — manifest\n")
    manifest.write(f"Utworzone: {datetime.now().isoformat()}\n")
    manifest.write("Pliki:\n")
    for p in files:
        manifest.write(f" - {p.resolve()}\n")

    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("MANIFEST.txt", manifest.getvalue().encode("utf-8"))
        for p in files:
            z.write(p, arcname=p.name)

    typer.secho(f"OK: ZIP → {zip_path.as_posix()}", fg=typer.colors.GREEN)

# Alias dla kompatybilności
def app():
    cli()

if __name__ == "__main__":
    cli()
