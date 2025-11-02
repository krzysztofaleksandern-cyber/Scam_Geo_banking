from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import List

import typer
from rich.console import Console

from .scan import (
    scan_web_targets,
    sweep_keywords,
    scan_ads,
    write_csv,
)
from ..enrichment import enrich_reputation
from ..report import generate_pdf

cli = typer.Typer(add_completion=False, help="Scam_Geo Banking CLI")
console = Console()


@cli.command("version", help="Wypisz wersję narzędzia.")
def version() -> None:
    console.print("Scam_Geo Banking v0.1.0")


@cli.command("scan-web", help="Skan źródeł publicznych (YT/TT/FB – stub/feeds) i zapis do CSV.")
def scan_web(
    targets: str = typer.Option(..., "--targets", "-t", help='Lista: yt:<id>, tt:<handle>, fb:<page> (comma sep)'),
    out: Path = typer.Option(Path("./out"), "--out", "-o", help="Katalog output"),
) -> None:
    t = [x.strip() for x in targets.split(",") if x.strip()]
    out_path = scan_web_targets(t, out)
    console.print(f"OK: zapisano → {out_path}")


@cli.command("sweep", help="Skan fraz w wyszukiwarce (stub) i zapis do CSV.")
def sweep(
    keywords: str = typer.Option(..., "--keywords", "-k", help="Frazy/zdania, comma separated"),
    out: Path = typer.Option(Path("./out"), "--out", "-o", help="Katalog output"),
) -> None:
    qs = [x.strip() for x in keywords.split(",") if x.strip()]
    out_path = sweep_keywords(qs, out)
    console.print(f"OK: zapisano → {out_path}")


@cli.command("ads", help="Pseudo-inspekcja reklam (stub) i zapis do CSV.")
def ads(
    targets: str = typer.Option(..., "--targets", "-t", help="yt:/tt:/fb: jak w scan-web"),
    out: Path = typer.Option(Path("./out"), "--out", "-o", help="Katalog output"),
) -> None:
    t = [x.strip() for x in targets.split(",") if x.strip()]
    out_path = scan_ads(t, out)
    console.print(f"OK: zapisano → {out_path}")


@cli.command("package", help="Spakuj wskazane CSV do ZIP (manifest + pliki).")
def package(
    inputs: str = typer.Option(..., "--inputs", "-i", help="CSV,CSV,..."),
    out: Path = typer.Option(Path("./out"), "--out", "-o", help="Katalog output"),
    zip_path: Path = typer.Option(Path("./out/web_evidence.zip"), "--zip", help="Ścieżka ZIP"),
) -> None:
    out.mkdir(parents=True, exist_ok=True)
    files: List[Path] = [Path(p.strip()) for p in inputs.split(",") if p.strip()]
    # manifest
    rows = [["name", "size"]]
    for p in files:
        rows.append([p.name, str(p.stat().st_size if p.exists() else 0)])
    manifest = out / "manifest.csv"
    write_csv(manifest, rows)
    # zip
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(manifest, manifest.name)
        for p in files:
            if p.exists():
                z.write(p, p.name)
    console.print(f"OK: ZIP → {zip_path}")


@cli.command("enrich", help="Enrichment reputacji URL/DOMEN (VT/OTX z fallbackiem).")
def enrich(
    inputs: str = typer.Option(..., "--inputs", "-i", help="CSV,CSV,... (z kolumną url)"),
    out: Path = typer.Option(Path("./out"), "--out", "-o", help="Katalog output"),
    vt_key: str | None = typer.Option(None, envvar="VT_API_KEY", help="VirusTotal API Key (opcjonalnie)"),
    otx_key: str | None = typer.Option(None, envvar="OTX_API_KEY", help="AlienVault OTX API Key (opcjonalnie)"),
) -> None:
    paths = [Path(p.strip()) for p in inputs.split(",") if p.strip()]
    rep_csv = enrich_reputation(paths, out, vt_key=vt_key, otx_key=otx_key)
    console.print(f"OK: reputacja → {rep_csv}")


@cli.command("report", help="Wygeneruj PDF (executive summary + tabele) z CSV.")
def report(
    inputs: str = typer.Option(..., "--inputs", "-i", help="CSV,CSV,..."),
    pdf: Path = typer.Option(Path("./out/report.pdf"), "--pdf", help="Ścieżka wyjściowa PDF"),
) -> None:
    paths = [Path(p.strip()) for p in inputs.split(",") if p.strip()]
    generate_pdf(paths, pdf)
    console.print(f"OK: raport → {pdf}")


def main() -> None:
    # alias do uruchamiania z -m
    cli()


if __name__ == "__main__":
    cli()
