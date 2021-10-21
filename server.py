import asyncio
import aiohttp
import jinja2
import aiohttp_jinja2
import json
import os

from aiohttp import web
from googlewifi import GoogleWifi

allowlist_filename = os.path.expanduser('~/.tmp/allowlist')

current_systems = {}
current_systems_lock = asyncio.Lock()

def get_allowed_devices():
    if get_allowed_devices.cached_list is not None:
        return get_allowed_devices.cached_list
    if not os.path.exists(allowlist_filename):
        return None
    with open(allowlist_filename, 'r') as allowlist_file:
        allowlist = json.load(allowlist_file)
    get_allowed_devices.cached_list = allowlist
    return get_allowed_devices.cached_list

get_allowed_devices.cached_list = None

def save_allowed_devices():
    allowed_devices = get_allowed_devices()
    if allowed_devices is not None:
        with open(allowlist_filename, 'w') as allowlist_file:
            json.dump(allowed_devices, allowlist_file, indent=3)

async def get_current_devices():
    async with current_systems_lock:
        systems = current_systems
    devices = {}
    for system_id in systems:
        devices.update(systems[system_id].get('devices'))
    return devices

def pause_new_devices():
    allowed_devices = get_allowed_devices()
    if allowed_devices is None:
        return
    current_devices = get_current_devices()
    for device in current_devices:
        if device not in allowed_devices:
            print('Pausing device') 

def get_refresh_token():
    if get_refresh_token.cached_token is not None:
        return get_refresh_token.cached_token
    get_refresh_token.cached_token = os.getenv('GOOGLE_REFRESH_TOKEN')
    if get_refresh_token.cached_token is None:
        print('GOOGLE_REFRESH_TOKEN is not set', file=sys.stderr)
        sys.exit(1)
    return get_refresh_token.cached_token
get_refresh_token.cached_token = None

async def update_systems():
    print('updating systems')
    async with aiohttp.ClientSession() as session:
        token = get_refresh_token()
        wifi = GoogleWifi(token, session)
        systems = await wifi.get_systems()
        async with current_systems_lock:
            global current_systems
            current_systems = systems
    print('systems updated')
    pause_new_devices()

async def poll_google_wifi():
    while True:
        await update_systems()
        await asyncio.sleep(5 * 60)

async def start_polling(app):
    app['google_polling_task'] = asyncio.create_task(poll_google_wifi())

async def stop_polling(app):
    app['google_polling_task'].cancel()
    await app['google_polling_task']

async def list_devices(request):
    return web.json_response(await get_current_devices())

async def hello(request):
    name = request.match_info.get('name', 'Anonymous')
    text = 'Hello, ' + name
    return web.Response(text=text)

async def page_device_list(request: web.Request) -> web.Response:
    context = {
        'devices': await get_current_devices()
    }
    response = aiohttp_jinja2.render_template(
        'device_list.html', request, context=context
    )
    return response

if __name__ == '__main__':
    app = web.Application()
    aiohttp_jinja2.setup(
        app, loader=jinja2.FileSystemLoader(os.path.join(os.getcwd(), 'templates'))
    )
    app.add_routes([
        web.get('/hello/{name}', hello),
        web.get('/devices', page_device_list),
        web.get('/api/devices', list_devices),
    ])
    app.on_startup.append(start_polling)
    app.on_cleanup.append(stop_polling)
    web.run_app(app)
