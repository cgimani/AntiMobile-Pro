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
            return res.get('value')

async def main():
    ws = await websocket_connect(WS_URL)
    print("Connected to CDP")

    # Reload page
    print("Reloading page...")
    msg_id = int(asyncio.get_event_loop().time() * 10000) % 100000
    await ws.write_message(json.dumps({'id': msg_id, 'method': 'Page.reload'}))
    await asyncio.sleep(2.0)

    # Open Drawer
    print("Opening drawer...")
    await eval_js(ws, "window.openDrawer();")
    await asyncio.sleep(0.5)

    drawer_info = await eval_js(ws, """(() => {
        const drawer = document.getElementById('drawer');
        const projFolders = Array.from(document.querySelectorAll('.agy-project-folder')).map(f => {
            const name = f.querySelector('.agy-project-name')?.textContent?.trim();
            const chats = Array.from(f.querySelectorAll('.agy-chat-item')).map(c => c.querySelector('.agy-chat-title')?.textContent?.trim());
            return { name, chatCount: chats.length, chats: chats.slice(0, 5) };
        });
        const computedBg = window.getComputedStyle(drawer).backgroundColor;
        return {
            isOpen: document.getElementById('drawerBackdrop').classList.contains('open'),
            backgroundColor: computedBg,
            projectFolders: projFolders
        };
    })()""")
    print("Drawer Info:", json.dumps(drawer_info, ensure_ascii=False, indent=2))
    await capture_screen(ws, "screenshot_drawer_real_projects.png")

    # Test Project Creation via Modal
    print("Testing Project Creation...")
    await eval_js(ws, """(async () => {
        const res = await fetch('/api/projects', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                name: 'Fatemeh SH Project 3',
                path: '~/projects/fatemeh-sh-project-3'
            })
        });
        return await res.json();
    })()""")
    await asyncio.sleep(1.0)

    # Update drawer after new project created
    await eval_js(ws, "window.updateDrawerChatList();")
    await asyncio.sleep(0.5)

    projects_after = await eval_js(ws, """(() => {
        const folders = Array.from(document.querySelectorAll('.agy-project-folder')).map(f => {
            return {
                name: f.querySelector('.agy-project-name')?.textContent?.trim(),
                isOpen: f.classList.contains('open'),
                chats: Array.from(f.querySelectorAll('.agy-chat-item')).map(c => c.querySelector('.agy-chat-title')?.textContent?.trim())
            };
        });
        return folders;
    })()""")
    print("Projects after adding Fatemeh SH Project 3:", json.dumps(projects_after, ensure_ascii=False, indent=2))
    await capture_screen(ws, "screenshot_drawer_multi_projects.png")

    ws.close()

if __name__ == '__main__':
    asyncio.run(main())
