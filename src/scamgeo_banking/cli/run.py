# src/scamgeo_banking/cli/run.py
from __future__ import annotations
import argparse, json, logging, sys, zipfile
from pathlib import Path
import importlib

def setup_logger(log_path: Path | None, verbose: bool) -> logging.Logger:
    logger = logging.getLogger()
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s", "%Y-%m-%d %H:%M:%S")

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    sh.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.addHandler(sh)

    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setFormatter(fmt)
        fh.setLevel(logging.DEBUG)
        logger.addHandler(fh)

    return logger

def load_config(path: Path | None, logger: logging.Logger) -> dict:
    if not path:
        logger.info("No config provided; using defaults.")
        return {}
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        logger.info("Config loaded: %s", path)
        return data
    except Exception as e:
        logger.error("Failed to read config %s: %s", path, e)
        return {}

def try_import_pipeline(logger: logging.Logger):
    try:
        mod = importlib.import_module("scamgeo_banking.cli.app")
        fn = getattr(mod, "pipeline", None)
        if callable(fn):
            logger.info("Using pipeline from app.py")
            return fn
        logger.debug("No callable pipeline found in app.py; will use stub.")
    except Exception as e:
        logger.debug("Cannot import pipeline from app.py: %s", e)
    return None

def stub_pipeline(out_dir: Path, cfg: dict, logger: logging.Logger, make_zip: Path | None, evidence: bool):
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "iocs.csv").write_text("indicator,type,score\nexample.com,domain,80\n", encoding="utf-8")
    if evidence:
        (out_dir / "evidence.txt").write_text("stub evidence\n", encoding="utf-8")
    if make_zip:
        with zipfile.ZipFile(make_zip, "w", zipfile.ZIP_DEFLATED) as z:
            for p in out_dir.iterdir():
                if p.is_file():
                    z.write(p, p.name)

def main() -> int:
    ap = argparse.ArgumentParser(prog="scamgeo_banking", description="Run Scam_Geo Banking pipeline")
    ap.add_argument("-i", "--input", required=True, dest="input")
    ap.add_argument("-o", "--out",   required=True, dest="out")
    ap.add_argument("--zip", dest="zip_path")
    ap.add_argument("--config", dest="config_path")
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--log", dest="log_path")
    ap.add_argument("--evidence", action="store_true", help="emit evidence.txt in out")

    args = ap.parse_args()

    log = setup_logger(Path(args.log_path) if args.log_path else None, args.verbose)
    log.info("RUN start: Telegram pipeline -> artifacts")

    cfg = load_config(Path(args.config_path) if args.config_path else None, log)
    out_dir = Path(args.out).resolve()
    zip_path = Path(args.zip_path).resolve() if args.zip_path else None

    # spróbuj wziąć pipeline z app.py
    pipe = try_import_pipeline(log)

    if pipe is None:
        log.info("STUB: generating %s", out_dir / "iocs.csv")
        stub_pipeline(out_dir, cfg, log, zip_path, args.evidence)
    else:
        pipe(out_dir=out_dir, cfg=cfg, logger=log, zip_path=zip_path, evidence=args.evidence)

    log.info("RUN done: artifacts in %s", out_dir)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
