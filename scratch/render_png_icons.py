import asyncio
import base64
import json
import os
import urllib.request
import tornado.websocket
from PIL import Image

WORKSPACE = "/Users/x/Desktop/Anti Projects/Mani/antigravity_all_files"

# 1. HTML wrapper to render icon.svg exactly 512x512 transparent
render_html_path = "/private/tmp/render_icon.html"
with open(render_html_path, "w") as f:
    f.write(f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: 512px;
    height: 512px;
    background: transparent;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
  }}
  img {{
    width: 512px;
    height: 512px;
    display: block;
  }}
</style>
</head>
<body>
  <img src="file://{WORKSPACE}/icons/icon.svg">
</body>
</html>''')

# HTML wrapper for maskable icon
render_maskable_html_path = "/private/tmp/render_maskable.html"

# Read defs and mark elements again for maskable
import xml.etree.ElementTree as ET
tree = ET.parse('/private/tmp/google_antigravity_logo.svg')
root = tree.getroot()
defs = root.find('{http://www.w3.org/2000/svg}defs')
g = root.find('{http://www.w3.org/2000/svg}g')

mark_elements = []
for child in list(g):
    tag = child.tag.split('}')[-1]
    if tag == 'path' and child.attrib.get('fill') == '#3186FF':
        mark_elements.append(child)
    elif tag == 'mask':
        mark_elements.append(child)
    elif tag == 'g' and child.attrib.get('mask'):
        mark_elements.append(child)

defs_str = ''.join(ET.tostring(child, encoding='unicode') for child in defs)
mark_str = ''.join(ET.tostring(child, encoding='unicode') for child in mark_elements)

maskable_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512" fill="none">
  <defs>
    <radialGradient id="maskableBg" cx="50%" cy="35%" r="65%">
      <stop offset="0%" stop-color="#0c0e14" />
      <stop offset="55%" stop-color="#050608" />
      <stop offset="100%" stop-color="#010203" />
    </radialGradient>
    <radialGradient id="ambientAuraM" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#3186FF" stop-opacity="0.25" />
      <stop offset="50%" stop-color="#FC413D" stop-opacity="0.12" />
      <stop offset="100%" stop-color="#000000" stop-opacity="0" />
    </radialGradient>
    <filter id="archShadowM" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="12" stdDeviation="16" flood-color="#000000" flood-opacity="0.7" />
    </filter>
{defs_str}
  </defs>
  <!-- Full bleed background for Android adaptive masking -->
  <rect width="512" height="512" fill="url(#maskableBg)" />
  <ellipse cx="256" cy="260" rx="160" ry="150" fill="url(#ambientAuraM)" />
  <!-- Safe zone scaled glyph (scale 3.0 instead of 3.6 to stay within 80% safe circle) -->
  <g filter="url(#archShadowM)">
    <g transform="translate(89.4, 83.5) scale(3.0)">
{mark_str}
    </g>
  </g>
</svg>'''

with open("/private/tmp/maskable.svg", "w") as f:
    f.write(maskable_svg)

with open(render_maskable_html_path, "w") as f:
    f.write(f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ margin: 0; padding: 0; }}
  body {{ width: 512px; height: 512px; background: #000; overflow: hidden; }}
  img {{ width: 512px; height: 512px; display: block; }}
</style>
</head>
<body>
  <img src="file:///private/tmp/maskable.svg">
</body>
</html>''')

async def render():
    req = urllib.request.urlopen('http://127.0.0.1:9222/json/list')
    targets = json.loads(req.read().decode())
    page_target = [t for t in targets if t.get('type') == 'page'][0]
    ws_url = page_target['webSocketDebuggerUrl']
    conn = await tornado.websocket.websocket_connect(ws_url)

    # 1. Set viewport to 512x512
    await conn.write_message(json.dumps({
        "id": 1,
        "method": "Emulation.setDeviceMetricsOverride",
        "params": {
            "width": 512,
            "height": 512,
            "deviceScaleFactor": 1.0,
            "mobile": False
        }
    }))
    await asyncio.sleep(0.5)

    # 2. Render standard icon
    await conn.write_message(json.dumps({
        "id": 2,
        "method": "Page.navigate",
        "params": {"url": f"file://{render_html_path}"}
    }))
    await asyncio.sleep(1.0)

    await conn.write_message(json.dumps({
        "id": 3,
        "method": "Page.captureScreenshot",
        "params": {"format": "png", "fromSurface": True}
    }))
    while True:
        msg = await conn.read_message()
        data = json.loads(msg)
        if data.get("id") == 3:
            img_bytes = base64.b64decode(data['result']['data'])
            out_512 = os.path.join(WORKSPACE, "icons", "icon-512.png")
            with open(out_512, "wb") as f:
                f.write(img_bytes)
            print("Saved icons/icon-512.png")
            # Also save to artifact directory for inspection
            with open("/Users/x/.gemini/antigravity/brain/d6796ab7-5005-46c9-a548-c1a20069f368/icon_512_preview.png", "wb") as f:
                f.write(img_bytes)
            break

    # 3. Create icon-192.png via Pillow (LANCZOS downsampling)
    im = Image.open(out_512)
    im_192 = im.resize((192, 192), Image.Resampling.LANCZOS)
    im_192.save(os.path.join(WORKSPACE, "icons", "icon-192.png"), "PNG")
    print("Saved icons/icon-192.png")

    # 4. Render maskable icon
    await conn.write_message(json.dumps({
        "id": 4,
        "method": "Page.navigate",
        "params": {"url": f"file://{render_maskable_html_path}"}
    }))
    await asyncio.sleep(1.0)

    await conn.write_message(json.dumps({
        "id": 5,
        "method": "Page.captureScreenshot",
        "params": {"format": "png", "fromSurface": True}
    }))
    while True:
        msg = await conn.read_message()
        data = json.loads(msg)
        if data.get("id") == 5:
            img_bytes = base64.b64decode(data['result']['data'])
            out_maskable = os.path.join(WORKSPACE, "icons", "icon-maskable.png")
            with open(out_maskable, "wb") as f:
                f.write(img_bytes)
            print("Saved icons/icon-maskable.png")
            with open("/Users/x/.gemini/antigravity/brain/d6796ab7-5005-46c9-a548-c1a20069f368/icon_maskable_preview.png", "wb") as f:
                f.write(img_bytes)
            break

    # Restore navigation back to http://127.0.0.1:7681/
    await conn.write_message(json.dumps({
        "id": 6,
        "method": "Page.navigate",
        "params": {"url": "http://127.0.0.1:7681/"}
    }))
    await asyncio.sleep(0.5)

    conn.close()
    print("Done generating all PNG icons!")

asyncio.run(render())
