import aiohttp
import asyncio
import json
import os

from googlewifi import GoogleWifi

def get_refresh_token():
    if get_refresh_token.cached_token is not None:
        return get_refresh_token.cached_token
    get_refresh_token.cached_token = os.getenv('GOOGLE_REFRESH_TOKEN')
    if get_refresh_token.cached_token is None:
        print('GOOGLE_REFRESH_TOKEN is not set', file=sys.stderr)
        sys.exit(1)
    return get_refresh_token.cached_token
get_refresh_token.cached_token = None
    
async def compare_devices(wifi):
    systems = await wifi.get_systems()
    print(json.dumps(systems, indent=3))

async def main():
    async with aiohttp.ClientSession() as session:
        token = get_refresh_token()
        wifi = GoogleWifi(token, session)
        await compare_devices(wifi)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())