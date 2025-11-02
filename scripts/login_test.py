import asyncio
from scamgeo.utils.config import load_config
from scamgeo.tele import make_client

async def main():
    cfg = load_config(".\\config.json")  # moze byc None, jesli jedziesz tylko na ENV
    client = make_client(cfg)
    await client.start()  # wymusi logowanie i utworzy .session, jesli trzeba
    me = await client.get_me()
    print("OK, zalogowano jako:", getattr(me, "username", None) or me.id)
    await client.disconnect()

asyncio.run(main())
