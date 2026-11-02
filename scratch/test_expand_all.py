import asyncio
import json
import base64
import os
from tornado.websocket import websocket_connect

WS_URL = 'ws://127.0.0.1:9222/devtools/page/B752ED124F3EB1DABC3C5B433206A880'
ARTIFACT_DIR = '/Users/x/.gemini/antigravity/brain/d6796ab7-5005-46c9-a548-c1a20069f368'

async def capture_screen(ws, filename):
    msg_id = int(asyncio.get_event_loop().time() * 1000) % 100000
    await ws.write_message(json.dumps({
        'id': msg_id,
        'method': 'Page.captureScreenshot',
        'params': {'format': 'png'}
    }))
    while True:
        resp = await ws.read_message()
        if not resp:
            break
        data = json.loads(resp)
        if data.get('id') == msg_id:
            img_b64 = data.get('result', {}).get('data', '')
            out_path = os.path.join(ARTIFACT_DIR, filename)
            with open(out_path, 'wb') as f:
                f.write(base64.b64decode(img_b64))
            print(f"Captured: {filename}")
            break

async def eval_js(ws, expr):
    msg_id = int(asyncio.get_event_loop().time() * 1000) % 100000
    await ws.write_message(json.dumps({
        'id': msg_id,
        'method': 'Runtime.evaluate',
        'params': {'expression': expr, 'returnByValue': True}
    }))
    while True:
        resp = await ws.read_message()
        if not resp:
            return None
        data = json.loads(resp)
        if data.get('id') == msg_id:
            return data.get('result', {}).get('result', {}).get('value')

async def main():
    ws = await websocket_connect(WS_URL)

    # Click to expand all feed items
    await eval_js(ws, """
      const items = document.querySelectorAll('.agy-feed-item');
      items.forEach(it => it.classList.add('expanded'));
      scrollToBottom();
    """)
    await asyncio.sleep(0.6)
    await capture_screen(ws, 'screenshot_all_feed_items_expanded.png')

    ws.close()

if __name__ == '__main__':
    asyncio.run(main())
