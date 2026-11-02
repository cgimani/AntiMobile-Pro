import asyncio
import json
import base64
import os
from tornado.websocket import websocket_connect

WS_URL = 'ws://127.0.0.1:9222/devtools/page/B752ED124F3EB1DABC3C5B433206A880'
ARTIFACT_DIR = '/Users/x/.gemini/antigravity/brain/d6796ab7-5005-46c9-a548-c1a20069f368'

async def capture(ws, filename):
    msg_id = int(asyncio.get_event_loop().time() * 10000) % 100000
    await ws.write_message(json.dumps({
        'id': msg_id,
        'method': 'Page.captureScreenshot',
        'params': {'format': 'png'}
    }))
    while True:
        resp = await ws.read_message()
        data = json.loads(resp)
        if data.get('id') == msg_id:
            img_b64 = data.get('result', {}).get('data', '')
            out_path = os.path.join(ARTIFACT_DIR, filename)
            with open(out_path, 'wb') as f:
                f.write(base64.b64decode(img_b64))
            print(f"Captured: {filename}")
            break

async def eval_js(ws, expr):
    msg_id = int(asyncio.get_event_loop().time() * 10000) % 100000
    await ws.write_message(json.dumps({
        'id': msg_id,
        'method': 'Runtime.evaluate',
        'params': {'expression': expr, 'returnByValue': True}
    }))
    while True:
        resp = await ws.read_message()
        data = json.loads(resp)
        if data.get('id') == msg_id:
            res = data.get('result', {}).get('result', {})
            return res.get('value')

async def main():
    ws = await websocket_connect(WS_URL)
    print("Connected to CDP")

    # 1. Reload page
    print("Reloading page...")
    msg_id = int(asyncio.get_event_loop().time() * 10000) % 100000
    await ws.write_message(json.dumps({'id': msg_id, 'method': 'Page.reload'}))
    await asyncio.sleep(2.0)

    # 2. Open Settings Modal (Desktop)
    print("Opening Settings Modal...")
    await eval_js(ws, "window.openSettingsModal();")
    await asyncio.sleep(0.8)

    nav_tabs = await eval_js(ws, """(() => {
        return Array.from(document.querySelectorAll('.agy-settings-nav-item')).map(b => ({
            tab: b.getAttribute('data-tab'),
            text: b.textContent.trim(),
            isActive: b.classList.contains('active')
        }));
    })()""")
    print("Settings Tabs:", json.dumps(nav_tabs, ensure_ascii=False, indent=2))

    # Projects Tab Screenshot
    await capture(ws, "screenshot_settings_cleaned_projects.png")

    # 3. Switch to General Tab
    print("Switching to General Tab...")
    await eval_js(ws, "window.switchSettingsTab('general');")
    await asyncio.sleep(0.5)
    await capture(ws, "screenshot_settings_cleaned_general.png")

    # 4. Switch to Models Tab
    print("Switching to Models Tab...")
    await eval_js(ws, "window.switchSettingsTab('models');")
    await asyncio.sleep(0.5)
    await capture(ws, "screenshot_settings_cleaned_models.png")

    # 5. Mobile Viewport (390x844)
    print("Testing Mobile Viewport...")
    await ws.write_message(json.dumps({
        'id': 201,
        'method': 'Emulation.setDeviceMetricsOverride',
        'params': {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True}
    }))
    await asyncio.sleep(0.5)

    await eval_js(ws, "window.switchSettingsTab('projects');")
    await asyncio.sleep(0.5)
    await capture(ws, "screenshot_mobile_settings_cleaned_projects.png")

    await eval_js(ws, "window.switchSettingsTab('general');")
    await asyncio.sleep(0.5)
    await capture(ws, "screenshot_mobile_settings_cleaned_general.png")

    await ws.write_message(json.dumps({'id': 202, 'method': 'Emulation.clearDeviceMetricsOverride'}))
    await eval_js(ws, "window.closeSettingsModal();")
    print("All tests completed successfully!")

if __name__ == '__main__':
    asyncio.run(main())
