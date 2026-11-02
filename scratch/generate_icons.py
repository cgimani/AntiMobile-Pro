import xml.etree.ElementTree as ET
import os

# Read the official SVG file to get defs and mark elements
tree = ET.parse('/private/tmp/google_antigravity_logo.svg')
root = tree.getroot()
ns = {'svg': 'http://www.w3.org/2000/svg'}
ET.register_namespace('', 'http://www.w3.org/2000/svg')

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

# Serialize defs and mark children to strings
defs_str = ''.join(ET.tostring(child, encoding='unicode') for child in defs)
mark_str = ''.join(ET.tostring(child, encoding='unicode') for child in mark_elements)

# 1. Master icon.svg (512x512)
icon_svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512" fill="none">
  <defs>
    <!-- Deep Cosmic Background Gradient -->
    <radialGradient id="agyBgGradient" cx="50%" cy="35%" r="65%">
      <stop offset="0%" stop-color="#0c0e14" />
      <stop offset="55%" stop-color="#050608" />
      <stop offset="100%" stop-color="#010203" />
    </radialGradient>
    
    <!-- Atmospheric Ambient Glow behind the Arch -->
    <radialGradient id="ambientAura" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#3186FF" stop-opacity="0.22" />
      <stop offset="45%" stop-color="#FC413D" stop-opacity="0.10" />
      <stop offset="75%" stop-color="#FFE432" stop-opacity="0.04" />
      <stop offset="100%" stop-color="#000000" stop-opacity="0" />
    </radialGradient>

    <!-- Glass Rim Linear Gradient -->
    <linearGradient id="glassRim" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0.18" />
      <stop offset="40%" stop-color="#ffffff" stop-opacity="0.05" />
      <stop offset="100%" stop-color="#ffffff" stop-opacity="0.02" />
    </linearGradient>

    <!-- Drop Shadow Filter for Arch -->
    <filter id="archShadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="12" stdDeviation="16" flood-color="#000000" flood-opacity="0.65" />
    </filter>

    <!-- Official SVG Defs (Gaussian Blurs and Filters) -->
{defs_str}
  </defs>

  <!-- Squircle Base (Apple/Android PWA Master 112px radius) -->
  <rect x="8" y="8" width="496" height="496" rx="112" fill="url(#agyBgGradient)" stroke="url(#glassRim)" stroke-width="2" />

  <!-- Ambient Glow Aura -->
  <ellipse cx="256" cy="260" rx="180" ry="170" fill="url(#ambientAura)" />

  <!-- Scaled & Centered Official Google Antigravity Glyph -->
  <!-- Original bounds: x ~ 10..101 (center 55.5), y ~ 18..97 (center 57.5) -->
  <!-- Scale factor = 3.6 => width = 300, height = 277 -->
  <g filter="url(#archShadow)">
    <g transform="translate(56.2, 49) scale(3.6)">
{mark_str}
    </g>
  </g>
</svg>'''

with open('/Users/x/Desktop/Anti Projects/Mani/antigravity_all_files/icons/icon.svg', 'w') as f:
    f.write(icon_svg_content)
print("Saved icons/icon.svg")

# 2. Crisp favicon.svg (64x64)
# Optimized for tab bars: slightly punchier scale and tighter radius
favicon_svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64" fill="none">
  <defs>
    <radialGradient id="favBg" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#0d1017" />
      <stop offset="100%" stop-color="#010203" />
    </radialGradient>
    <linearGradient id="favRim" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0.22" />
      <stop offset="100%" stop-color="#ffffff" stop-opacity="0.04" />
    </linearGradient>
{defs_str}
  </defs>
  <rect width="64" height="64" rx="15" fill="url(#favBg)" stroke="url(#favRim)" stroke-width="1.2" />
  <!-- Center: scale = 0.55, offset = (64 - 84*0.55)/2 = 8.9, y offset = (64 - 78*0.55)/2 = 10.5 -->
  <!-- Original center 55.5, 57.5 -> 55.5*0.55 = 30.5 => 32 - 30.5 = 1.5 => x=1.5 - 13*0.55? No, translate directly -->
  <g transform="translate(1.5, 0.4) scale(0.55)">
{mark_str}
  </g>
</svg>'''

with open('/Users/x/Desktop/Anti Projects/Mani/antigravity_all_files/icons/favicon.svg', 'w') as f:
    f.write(favicon_svg_content)
print("Saved icons/favicon.svg")
