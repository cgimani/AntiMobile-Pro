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

    # 1. Test live steps rendering via frontend events to confirm 100% exact match to Image 7
    script = """
    (() => {
      // Create a fresh test chat container
      const testRow = document.createElement('div');
      testRow.className = 'msg-row assistant minimal-turn';
      testRow.id = 'testAgyFeedRow';
      
      const feed = document.createElement('div');
      feed.className = 'agy-live-feed';
      testRow.appendChild(feed);
      
      const emptyState = document.getElementById('emptyState');
      if (emptyState) emptyState.style.display = 'none';
      
      const chatInner = document.getElementById('chatInner');
      if (chatInner) chatInner.appendChild(testRow);
      
      window.currentLiveFeedEl = feed;
      
      // Status indicator
      const st = document.createElement('div');
      st.className = 'agy-feed-status';
      st.innerHTML = '<span class="agy-feed-status-text">Working</span>';
      feed.appendChild(st);
      window.currentFeedStatusEl = st;
      
      // Test items matching Image 7:
      // 1. Analyzed ⚛ App.tsx #L60-150
      handleStepStart({
        step_index: 101,
        action: 'Analyzed',
        file_name: 'App.tsx',
        file_ext: 'tsx',
        line_range: '#L60-150',
        snippet: '  60 | export function App() {\\n  61 |   return <div>App</div>\\n  62 | }'
      });
      
      // 2. Analyzed ⚛ App.tsx #L150-200
      handleStepStart({
        step_index: 102,
        action: 'Analyzed',
        file_name: 'App.tsx',
        file_ext: 'tsx',
        line_range: '#L150-200',
        snippet: ' 150 | const styles = {};\\n 151 | export default App;'
      });
      
      // 3. Thought for 28s >
      handleThinkingStep({
        duration: 28,
        thinking: 'Investigating state hooks and component hierarchy in App.tsx.'
      });
      
      // 4. Analyzed TS data.ts #L1-140
      handleStepStart({
        step_index: 103,
        action: 'Analyzed',
        file_name: 'data.ts',
        file_ext: 'ts',
        line_range: '#L1-140',
        snippet: '   1 | export interface ProjectData { id: string; }'
      });
      
      // 5. Thought for 49s >
      handleThinkingStep({
        duration: 49,
        thinking: 'Formulating data structures for data context and admin page.'
      });
      
      // 6. Created ⚛ DataContext.tsx +341 -0
      handleStepStart({
        step_index: 104,
        action: 'Created',
        file_name: 'DataContext.tsx',
        file_ext: 'tsx',
        add_lines: 341,
        del_lines: 0,
        snippet: 'import React from "react";\\nexport const DataContext = React.createContext(null);'
      });
      
      // 7. Thought for 142s >
      handleThinkingStep({
        duration: 142,
        thinking: 'Completed full architecture for admin panel and context providers.'
      });
      
      // 8. Created ⚛ AdminPage.tsx +1605 -0
      handleStepStart({
        step_index: 105,
        action: 'Created',
        file_name: 'AdminPage.tsx',
        file_ext: 'tsx',
        add_lines: 1605,
        del_lines: 0,
        snippet: 'import React from "react";\\nexport function AdminPage() { return <div>Admin</div>; }'
      });
      
      // 9. Analyzed ⚛ main.tsx #L1-10
      handleStepStart({
        step_index: 106,
        action: 'Analyzed',
        file_name: 'main.tsx',
        file_ext: 'tsx',
        line_range: '#L1-10',
        snippet: '   1 | import React from "react";\\n   2 | import ReactDOM from "react-dom/client";'
      });
      
      // 10. Edited ⚛ main.tsx +4 -1
      handleStepStart({
        step_index: 107,
        action: 'Edited',
        file_name: 'main.tsx',
        file_ext: 'tsx',
        add_lines: 4,
        del_lines: 1,
        target: 'root.render(<App />);',
        replacement: 'root.render(\\n  <DataProvider>\\n    <App />\\n  </DataProvider>\\n);'
      });
      
      // Scroll to bottom
      window.scrollToBottom();
      return true;
    })()
    """
    await eval_js(ws, script)
    await asyncio.sleep(0.8)
    await capture_screen(ws, 'screenshot_verified_exact_image7_feed.png')

    # Expand one Analyzed item and one Edited item to verify real contents expand
    await eval_js(ws, """
      const items = document.querySelectorAll('.agy-feed-item');
      if (items[0]) items[0].classList.add('expanded'); // Analyzed
      if (items[9]) items[9].classList.add('expanded'); // Edited
      window.scrollToBottom();
    """)
    await asyncio.sleep(0.5)
    await capture_screen(ws, 'screenshot_verified_feed_expanded_diff.png')

    ws.close()

if __name__ == '__main__':
    asyncio.run(main())
