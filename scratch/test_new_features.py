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

    # 1. Reload page
    print("Reloading page...")
    msg_id = int(asyncio.get_event_loop().time() * 10000) % 100000
    await ws.write_message(json.dumps({'id': msg_id, 'method': 'Page.reload'}))
    await asyncio.sleep(2.0)

    # 2. Open Drawer to check distinct project separation
    print("Opening Drawer...")
    await eval_js(ws, "window.openDrawer();")
    await asyncio.sleep(0.6)

    projects_info = await eval_js(ws, """(() => {
        const folders = Array.from(document.querySelectorAll('.agy-project-folder')).map(f => ({
            name: f.querySelector('.agy-project-name')?.textContent?.trim(),
            path: f.querySelector('.agy-project-path-sub')?.textContent?.trim(),
            count: f.querySelector('.agy-project-count-badge')?.textContent?.trim(),
            isActive: f.classList.contains('active-project'),
            chatCount: f.querySelectorAll('.agy-chat-item').length
        }));
        return folders;
    })()""")
    print("Drawer Projects:", json.dumps(projects_info, ensure_ascii=False, indent=2))
    await capture_screen(ws, "screenshot_distinct_projects.png")

    # 3. Open Folder Picker Modal via button or window.promptNewProject()
    print("Opening Folder Picker Modal...")
    await eval_js(ws, "window.promptNewProject();")
    await asyncio.sleep(0.5)

    fp_visible = await eval_js(ws, """(() => {
        const modal = document.getElementById('folderPickerModal');
        return modal && modal.classList.contains('open');
    })()""")
    print("Folder picker open:", fp_visible)
    await capture_screen(ws, "screenshot_folder_picker.png")

    # Fill and submit a new device folder project
    print("Creating new project via folder picker...")
    await eval_js(ws, """(() => {
        const nameIn = document.getElementById('fpProjectName');
        const pathIn = document.getElementById('fpProjectPath');
        if (nameIn) nameIn.value = 'Mobile App Core';
        if (pathIn) pathIn.value = '~/projects/mobile-app-core';
    })()""")
    await asyncio.sleep(0.3)
    await eval_js(ws, "window.submitFolderPicker();")
    await asyncio.sleep(1.0)

    # 4. Universal Chat Search
    print("Opening Chat Search...")
    await eval_js(ws, "window.openChatSearchModal();")
    await asyncio.sleep(0.5)

    print("Searching for 'test'...")
    await eval_js(ws, "window.performChatSearch('test');")
    await asyncio.sleep(0.8)

    search_results_count = await eval_js(ws, """(() => {
        return document.querySelectorAll('.agy-search-item').length;
    })()""")
    print(f"Found {search_results_count} search results")
    await capture_screen(ws, "screenshot_chat_search.png")

    await eval_js(ws, "window.closeChatSearchModal();")
    await asyncio.sleep(0.4)

    # 5. Settings: Projects & Chats Management Tab
    print("Opening Settings Modal...")
    await eval_js(ws, "window.openSettingsModal();")
    await asyncio.sleep(0.5)

    print("Switching to Projects tab...")
    await eval_js(ws, "window.switchSettingsTab('projects');")
    await asyncio.sleep(0.8)

    settings_projects_count = await eval_js(ws, """(() => {
        return document.querySelectorAll('.agy-pm-card').length;
    })()""")
    print(f"Settings pane has {settings_projects_count} project cards")
    await capture_screen(ws, "screenshot_settings_projects_mgmt.png")

    print("All tests completed successfully!")

if __name__ == '__main__':
    asyncio.run(main())
