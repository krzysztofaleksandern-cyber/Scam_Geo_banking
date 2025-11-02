def main():
    from importlib.metadata import version, PackageNotFoundError
    try:
        v = version('scamgeo_banking')
    except PackageNotFoundError:
        v = '0.0.0-dev'
    print(f'Scam_Geo CLI {v}')
    return 0




