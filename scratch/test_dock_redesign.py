import asyncio
import json
import base64
import os
from tornado.websocket import websocket_connect

WS_URL = 'ws://127.0.0.1:9222/devtools/page/B752ED124F3EB1DABC3C5B433206A880'
ARTIFACT_DIR = '/Users/x/.gemini/antigravity/brain/d6796ab7-5005-46c9-a548-c1a20069f368'

async def capture_screen(ws, filename):
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
            val = res.get('value')
            return val

async def main():
    ws = await websocket_connect(WS_URL)
    print("Connected to CDP")

    # Reload page
    print("Reloading page...")
    msg_id = int(asyncio.get_event_loop().time() * 10000) % 100000
    await ws.write_message(json.dumps({'id': msg_id, 'method': 'Page.reload'}))
    await asyncio.sleep(2.0)

    # Check removed elements
    res = await eval_js(ws, """(() => {
        return {
            hasProjectTag: !!document.getElementById('dockProjectTag'),
            hasSubbar: !!document.querySelector('.agy-dock-subbar'),
            hasAttachFile: !!document.getElementById('btnAttachFile'),
            hasDockModel: !!document.getElementById('btnDockModel'),
            dockModelText: document.getElementById('dockModelName')?.textContent?.trim(),
            hasDockPolicy: !!document.getElementById('btnDockPolicy'),
            dockPolicyText: document.getElementById('dockPolicyName')?.textContent?.trim(),
            hasEmptyState: !!document.getElementById('emptyState')
        };
    })()""")
    print("Element check:", json.dumps(res, ensure_ascii=False, indent=2))

    # Capture clean dock screenshot
    await capture_screen(ws, "screenshot_dock_cleaned.png")

    # Click model button to open dropdown
    print("Opening model dropdown...")
    await eval_js(ws, "document.getElementById('btnDockModel').click();")
    await asyncio.sleep(0.5)

    model_open = await eval_js(ws, """(() => {
        const menu = document.getElementById('dockModelDropdown');
        const items = Array.from(menu.querySelectorAll('.agy-dropdown-item')).map(el => el.textContent.trim());
        return {
            isActive: menu.classList.contains('active'),
            itemsCount: items.length,
            items: items
        };
    })()""")
    print("Model dropdown status:", json.dumps(model_open, ensure_ascii=False, indent=2))
    await capture_screen(ws, "screenshot_model_dropdown_open.png")

    # Click policy button to open policy dropdown
    print("Opening policy dropdown...")
    await eval_js(ws, "document.getElementById('btnDockPolicy').click();")
    await asyncio.sleep(0.5)

    policy_open = await eval_js(ws, """(() => {
        const menu = document.getElementById('dockPolicyDropdown');
        const items = Array.from(menu.querySelectorAll('.agy-dropdown-item')).map(el => el.textContent.trim());
        return {
            isActive: menu.classList.contains('active'),
            itemsCount: items.length,
            items: items
        };
    })()""")
    print("Policy dropdown status:", json.dumps(policy_open, ensure_ascii=False, indent=2))
    await capture_screen(ws, "screenshot_policy_dropdown_open.png")

    # Click 'Turbo' in policy dropdown
    print("Selecting Turbo policy...")
    await eval_js(ws, "document.querySelector('#dockPolicyDropdownList [data-preset=\"Turbo\"]').click();")
    await asyncio.sleep(0.5)

    policy_after = await eval_js(ws, """(() => {
        return {
            dockPolicyText: document.getElementById('dockPolicyName')?.textContent?.trim(),
            isMenuClosed: !document.getElementById('dockPolicyDropdown').classList.contains('active')
        };
    })()""")
    print("Policy after select:", json.dumps(policy_after, ensure_ascii=False, indent=2))

    # Click 'Auto' in policy dropdown to set back to Auto
    await eval_js(ws, "document.getElementById('btnDockPolicy').click();")
    await asyncio.sleep(0.3)
    await eval_js(ws, "document.querySelector('#dockPolicyDropdownList [data-preset=\"Auto\"]').click();")
    await asyncio.sleep(0.5)

    final_state = await eval_js(ws, """(() => {
        return {
            dockModelText: document.getElementById('dockModelName')?.textContent?.trim(),
            dockPolicyText: document.getElementById('dockPolicyName')?.textContent?.trim()
        };
    })()""")
    print("Final dock state:", json.dumps(final_state, ensure_ascii=False, indent=2))
    await capture_screen(ws, "screenshot_dock_final_verified.png")

    ws.close()

if __name__ == '__main__':
    asyncio.run(main())
