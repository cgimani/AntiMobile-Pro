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

    # 1. Reload clean chat
    await ws.write_message(json.dumps({'id': 100, 'method': 'Page.reload', 'params': {'ignoreCache': True}}))
    await asyncio.sleep(2.0)

    # 2. Type message into inputMessage
    prompt = "read lines 1-15 of README.md and inspect git status"
    js_type = f"""
    (() => {{
      const inp = document.getElementById('inputMessage');
      if (inp) {{
        inp.value = '{prompt}';
        inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
        sendMessage();
        return true;
      }}
      return false;
    }})()
    """
    res = await eval_js(ws, js_type)
    print("Sent message:", res)

    # 3. Wait 3s and capture while running
    await asyncio.sleep(3.0)
    await capture_screen(ws, 'screenshot_real_turn_running.png')

    # 4. Wait for turn to finish (up to 15s)
    for _ in range(25):
        await asyncio.sleep(1.0)
        is_active = await eval_js(ws, "document.querySelector('.agy-feed-status') !== null")
        feed_items = await eval_js(ws, "document.querySelectorAll('.agy-feed-item').length")
        print(f"Polling... active={is_active}, feed_items={feed_items}")
        if feed_items and feed_items > 0 and not is_active:
            break

    await asyncio.sleep(1.0)
    await capture_screen(ws, 'screenshot_real_turn_done.png')

    # 5. Click on the first feed item to expand it
    await eval_js(ws, """
      const items = document.querySelectorAll('.agy-feed-item');
      if (items.length > 0) {
        items[0].querySelector('.agy-feed-header').click();
      }
    """)
    await asyncio.sleep(0.5)
    await capture_screen(ws, 'screenshot_real_turn_expanded.png')

    ws.close()

if __name__ == '__main__':
    asyncio.run(main())
