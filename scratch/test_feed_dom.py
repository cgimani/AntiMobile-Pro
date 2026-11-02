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

    # Inject message with steps matching Image 7
    js_code = """
    (() => {
      const steps = [
        { action: 'Analyzed', file_name: 'App.tsx', file_ext: 'tsx', line_range: '#L60-150', snippet: '  60 | export function App() {\\n  61 |   return <div>App</div>\\n  62 | }' },
        { action: 'Analyzed', file_name: 'App.tsx', file_ext: 'tsx', line_range: '#L150-200', snippet: ' 150 | const styles = {};\\n 151 | export default App;' },
        { action: 'Analyzed', file_name: 'data.ts', file_ext: 'ts', line_range: '#L1-140', snippet: '   1 | export interface ProjectData { id: string; }' },
        { action: 'Analyzed', file_name: 'data.ts', file_ext: 'ts', line_range: '#L300-520', snippet: ' 300 | export function loadData() {}' },
        { action: 'Created', file_name: 'DataContext.tsx', file_ext: 'tsx', add_lines: 341, del_lines: 0, snippet: 'import React from "react";\\nexport const DataContext = React.createContext(null);' },
        { action: 'Created', file_name: 'AdminPage.tsx', file_ext: 'tsx', add_lines: 1605, del_lines: 0, snippet: 'import React from "react";\\nexport function AdminPage() { return <div>Admin</div>; }' },
        { action: 'Analyzed', file_name: 'main.tsx', file_ext: 'tsx', line_range: '#L1-10', snippet: '   1 | import React from "react";\\n   2 | import ReactDOM from "react-dom/client";' },
        { action: 'Edited', file_name: 'main.tsx', file_ext: 'tsx', add_lines: 4, del_lines: 1, target: 'root.render(<App />);', replacement: 'root.render(\\n  <DataProvider>\\n    <App />\\n  </DataProvider>\\n);' },
        { action: 'Analyzed', file_name: 'App.tsx', file_ext: 'tsx', line_range: '#L1-30', snippet: '   1 | import React from "react";' },
        { action: 'Analyzed', file_name: 'App.tsx', file_ext: 'tsx', line_range: '#L40-85', snippet: '  40 | function SubComponent() {}' }
      ];

      const meta = {
        thinking: 'Investigated components, generated data providers and created the complete admin page layout.',
        duration: 28,
        steps: steps
      };

      appendMessageBubble('assistant', 'پروژه و بخش‌های مرتبط با موفقیت تحلیل، ایجاد و بروزرسانی گردید.', Date.now() / 1000, true, false, meta);
      
      // Also add Working status indicator
      const feeds = document.querySelectorAll('.agy-live-feed');
      const lastFeed = feeds[feeds.length - 1];
      if (lastFeed) {
        const workingEl = document.createElement('div');
        workingEl.className = 'agy-feed-status';
        workingEl.innerHTML = '<span class="agy-feed-status-text">Working</span>';
        lastFeed.appendChild(workingEl);
      }
      
      scrollToBottom();
      return true;
    })()
    """
    await eval_js(ws, js_code)
    await asyncio.sleep(0.6)
    await capture_screen(ws, 'screenshot_verified_exact_image7_complete.png')

    # Expand the Edited main.tsx +4 -1 item to show real unified diff
    await eval_js(ws, """
      const items = document.querySelectorAll('.agy-feed-item.edited');
      if (items.length > 0) items[0].classList.add('expanded');
      scrollToBottom();
    """)
    await asyncio.sleep(0.5)
    await capture_screen(ws, 'screenshot_verified_diff_expanded.png')

    ws.close()

if __name__ == '__main__':
    asyncio.run(main())
