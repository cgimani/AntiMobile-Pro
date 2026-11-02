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

    # 2. Open Storage Explorer Modal
    print("Opening Storage Explorer Modal...")
    await eval_js(ws, "window.promptNewProject();")
    await asyncio.sleep(1.0)

    browser_info = await eval_js(ws, """(() => {
        const curPath = document.getElementById('fpCurrentPathDisplay')?.textContent;
        const roots = Array.from(document.querySelectorAll('.agy-fp-root-chip')).map(c => c.textContent.trim());
        const folders = Array.from(document.querySelectorAll('.agy-fp-folder-item')).map(f => f.querySelector('.agy-fp-folder-name')?.textContent.trim());
        return { curPath, roots, foldersCount: folders.length, folders: folders.slice(0, 8) };
    })()""")
    print("Storage Browser Info:", json.dumps(browser_info, ensure_ascii=False, indent=2))
    await capture(ws, "screenshot_storage_browser_initial.png")

    # 3. Toggle New Folder Panel
    print("Opening Create Folder Panel...")
    await eval_js(ws, "window.toggleFpMkdir(true);")
    await asyncio.sleep(0.3)
    await eval_js(ws, "document.getElementById('fpNewFolderName').value = 'my-mobile-telebot';")
    await asyncio.sleep(0.3)
    await capture(ws, "screenshot_storage_browser_mkdir_input.png")

    # 4. Submit Create Folder
    print("Submitting New Folder Creation...")
    await eval_js(ws, "window.submitFpMkdir();")
    await asyncio.sleep(1.0)

    after_mkdir = await eval_js(ws, """(() => {
        return {
            curPath: document.getElementById('fpCurrentPathDisplay')?.textContent,
            projectName: document.getElementById('fpProjectName')?.value
        };
    })()""")
    print("After Mkdir Info:", json.dumps(after_mkdir, ensure_ascii=False, indent=2))
    await capture(ws, "screenshot_storage_browser_new_folder.png")

    # 5. Confirm Project in this folder
    print("Confirming and creating project in this folder...")
    await eval_js(ws, "window.submitFolderPicker();")
    await asyncio.sleep(1.2)

    # 6. Open Drawer to check the newly created project
    await eval_js(ws, "window.openDrawer();")
    await asyncio.sleep(0.6)
    await capture(ws, "screenshot_drawer_with_created_folder.png")

    # 7. Mobile Viewport (390x844)
    print("Testing Mobile Viewport...")
    await ws.write_message(json.dumps({
        'id': 201,
        'method': 'Emulation.setDeviceMetricsOverride',
        'params': {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True}
    }))
    await asyncio.sleep(0.4)

    await eval_js(ws, "window.closeDrawer(); window.promptNewProject();")
    await asyncio.sleep(1.0)
    await capture(ws, "screenshot_mobile_storage_browser.png")

    await ws.write_message(json.dumps({'id': 202, 'method': 'Emulation.clearDeviceMetricsOverride'}))
    await eval_js(ws, "window.closeFolderPickerModal();")
    print("All tests completed successfully!")

if __name__ == '__main__':
    asyncio.run(main())
