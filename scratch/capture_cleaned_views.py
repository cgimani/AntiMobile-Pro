import asyncio
import base64
import json
import urllib.request
import tornado.websocket

async def capture_views():
    req = urllib.request.urlopen('http://127.0.0.1:9222/json/list')
    targets = json.loads(req.read().decode())
    page_target = [t for t in targets if t.get('type') == 'page'][0]
    ws_url = page_target['webSocketDebuggerUrl']
    conn = await tornado.websocket.websocket_connect(ws_url)

    # 1. Mobile viewport (390x844)
    await conn.write_message(json.dumps({
        "id": 1,
        "method": "Emulation.setDeviceMetricsOverride",
        "params": {
            "width": 390,
            "height": 844,
            "deviceScaleFactor": 2.0,
            "mobile": True
        }
    }))
    await asyncio.sleep(0.3)

    await conn.write_message(json.dumps({
        "id": 2,
        "method": "Page.navigate",
        "params": {"url": "http://127.0.0.1:7681/"}
    }))
    await asyncio.sleep(1.5)

    # Capture Mobile Screenshot
    await conn.write_message(json.dumps({
        "id": 3,
        "method": "Page.captureScreenshot",
        "params": {"format": "png"}
    }))
    while True:
        msg = await conn.read_message()
        data = json.loads(msg)
        if data.get("id") == 3:
            img_bytes = base64.b64decode(data['result']['data'])
            with open("/Users/x/.gemini/antigravity/brain/d6796ab7-5005-46c9-a548-c1a20069f368/screenshot_mobile_header_cleaned.png", "wb") as f:
                f.write(img_bytes)
            print("Saved screenshot_mobile_header_cleaned.png")
            break

    # 2. Desktop viewport (1200x800)
    await conn.write_message(json.dumps({
        "id": 4,
        "method": "Emulation.setDeviceMetricsOverride",
        "params": {
            "width": 1200,
            "height": 800,
            "deviceScaleFactor": 1.0,
            "mobile": False
        }
    }))
    await asyncio.sleep(0.5)

    # Capture Desktop Screenshot
    await conn.write_message(json.dumps({
        "id": 5,
        "method": "Page.captureScreenshot",
        "params": {"format": "png"}
    }))
    while True:
        msg = await conn.read_message()
        data = json.loads(msg)
        if data.get("id") == 5:
            img_bytes = base64.b64decode(data['result']['data'])
            with open("/Users/x/.gemini/antigravity/brain/d6796ab7-5005-46c9-a548-c1a20069f368/screenshot_desktop_header_cleaned.png", "wb") as f:
                f.write(img_bytes)
            print("Saved screenshot_desktop_header_cleaned.png")
            break

    conn.close()

asyncio.run(capture_views())
