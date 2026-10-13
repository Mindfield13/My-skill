---
name: diagramming
description: "Create diagrams — dark SVG architecture/infrastructure diagrams as HTML, and hand-drawn Excalidraw JSON diagrams (architectures, flowcharts, sequence diagrams)"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [diagrams, architecture, SVG, excalidraw, flowchart, visualization, infrastructure]
---

# Diagramming

Two diagramming approaches for different needs: **dark SVG architecture diagrams** (for cloud/infra/software architecture rendered as HTML) and **hand-drawn Excalidraw diagrams** (for flowcharts, sequence diagrams, concept maps).

---

## Section 1: Architecture Diagrams (Dark SVG)

Generate professional, dark-themed technical architecture diagrams as standalone HTML files with inline SVG graphics. No external tools, no API keys — just write HTML, open in a browser.

### Best For
- Software system architecture (frontend/backend/database layers)
- Cloud infrastructure (VPC, regions, subnets, managed services)
- Microservice/service-mesh topology
- Database + API maps, deployment diagrams

### Color Palette

| Component | Fill | Stroke |
|-----------|------|--------|
| Frontend | `rgba(8,51,68,0.4)` | `#22d3ee` (cyan) |
| Backend | `rgba(6,78,59,0.4)` | `#34d399` (emerald) |
| Database | `rgba(76,29,149,0.4)` | `#a78bfa` (violet) |
| Cloud/AWS | `rgba(120,53,15,0.3)` | `#fbbf24` (amber) |
| Security | `rgba(136,19,55,0.4)` | `#fb7185` (rose) |
| Message Bus | `rgba(251,146,60,0.3)` | `#fb923c` (orange) |
| External | `rgba(30,41,59,0.5)` | `#94a3b8` (slate) |

### Design System

- **Font:** JetBrains Mono from Google Fonts
- **Background:** Slate-950 (`#020617`) with subtle 40px grid pattern
- **Components:** Rounded rects (`rx="6"`) with 1.5px strokes
- **Arrowheads:** SVG markers
- **Security flows:** Dashed lines in rose
- **Boundaries:** Dashed regions (security groups = 4,4 rose; regions = 8,4 amber)

### Document Structure

1. Header: Title with pulsing dot indicator and subtitle
2. Main SVG: Diagram within rounded border card
3. Summary Cards: 3 cards below for high-level details
4. Footer: Minimal metadata

### Spacing

- Standard height: 60px (services); 80-120px (large components)
- Vertical gap: Minimum 40px
- Legend: Outside all boundary boxes, 20px below lowest boundary

---

## Section 2: Excalidraw Diagrams (Hand-Drawn)

Create diagrams by writing standard Excalidraw element JSON and saving as `.excalidraw` files. Files can be drag-and-dropped onto excalidraw.com for viewing/editing.

### File Format

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "hermes-agent",
  "elements": [...],
  "appState": { "viewBackgroundColor": "#ffffff" }
}
```

### Element Types

| Type | Snippet |
|------|---------|
| Rectangle | `{"type":"rectangle","id":"r1","x":100,"y":100,"width":200,"height":100}` |
| Ellipse | `{"type":"ellipse","id":"e1","x":100,"y":100,"width":150,"height":150}` |
| Diamond | `{"type":"diamond","id":"d1","x":100,"y":100,"width":150,"height":150}` |
| Arrow | `{"type":"arrow","id":"a1","x":300,"y":150,"width":200,"height":0,"points":[[0,0],[200,0]],"endArrowhead":"arrow"}` |
| Text | `{"type":"text","id":"t1","x":150,"y":138,"text":"Hello","fontSize":20,"fontFamily":1,"originalText":"Hello","autoResize":true}` |

### Container Binding (Labels on Shapes)

Shape needs `boundElements` listing the text, text needs `containerId` pointing back:

```json
{ "type": "rectangle", "id": "r1", "x": 100, "y": 100, "width": 200, "height": 80,
  "roundness": { "type": 3 }, "backgroundColor": "#a5d8ff", "fillStyle": "solid",
  "boundElements": [{ "id": "t_r1", "type": "text" }] },
{ "type": "text", "id": "t_r1", "x": 105, "y": 110, "width": 190, "height": 25,
  "text": "Hello", "fontSize": 20, "fontFamily": 1, "strokeColor": "#1e1e1e",
  "textAlign": "center", "verticalAlign": "middle",
  "containerId": "r1", "originalText": "Hello", "autoResize": true }
```

**IMPORTANT:** Do NOT use `"label": {"text": "..."}` on shapes — this is NOT valid Excalidraw and will be silently ignored.

### Arrow Bindings

```json
{ "type": "arrow", "id": "a1", "x": 300, "y": 150, "width": 150, "height": 0,
  "points": [[0,0],[150,0]], "endArrowhead": "arrow",
  "startBinding": { "elementId": "r1", "fixedPoint": [1, 0.5] },
  "endBinding": { "elementId": "r2", "fixedPoint": [0, 0.5] } }
```

### Color Palette

| Use | Fill Color | Hex |
|-----|-----------|-----|
| Primary / Input | Light Blue | `#a5d8ff` |
| Success / Output | Light Green | `#b2f2bb` |
| Warning / External | Light Orange | `#ffd8a8` |
| Processing / Special | Light Purple | `#d0bfff` |
| Error / Critical | Light Red | `#ffc9c9` |
| Notes / Decisions | Light Yellow | `#fff3bf` |
| Storage / Data | Light Teal | `#c3fae8` |

### Tips

- Minimum shape size: 120x60 for labeled shapes
- Minimum fontSize: 16 for body text, 20 for titles
- Draw order (first = back, last = front): shape → its bound text → its arrows
- For uploading: `python3 scripts/upload.py ~/diagrams/my_diagram.excalidraw`
- Never use `fontSize` below 14; never use emoji in text
- Text contrast minimum on white: `#757575`