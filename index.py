import os
import re
import sys
import time
import threading
import requests
import win32api
import win32event
import screeninfo
import webview
from flask import Flask

# ---------------------- Constants & Globals ----------------------

windowtitle = "Routes Mod"
base_path = os.path.dirname(os.path.abspath(sys.argv[0]))

items = []
room = None
window = None
filtered_segments = []
current_index = 0

text_path = os.path.join(base_path, "settings.txt")
allowed_scales = [round(x * 0.1, 1) for x in range(1, 21)]
scale = 1.0
overlay_mode = True
base_width = 640
base_height = 360

# ---------------------- Single Instance Check ----------------------

mutex = win32event.CreateMutex(None, False, "routes_mod")
if win32api.GetLastError() == 183:
    try:
        requests.post("http://localhost:8123/reload")
    except Exception as e:
        print("Could not contact existing instance", e)
    sys.exit(0)

# ---------------------- HTML Template ----------------------

html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset=\"UTF-8\">
    <title>Routes Mod</title>
    <style>
        html, body { margin: 0; padding: 0; background: black; width: 100%; height: 100%; overflow: hidden; font-family: Arial; }
        #container { position: relative; width: 100%; height: 100%; }
        iframe { width: 100%; height: 100%; border: none; }
        #controls { position: absolute; bottom: 50px; left: 10px; display: flex; gap: 10px; z-index: 999; }
        button { background: rgba(255,255,255,0.3); color: white; border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer; }
        button:hover { background: rgba(255,255,255,0.8); }
        button:disabled { background: rgba(255,255,255,0.1); color: #888; cursor: default;}
        #scaleDisplay, #counter { position: absolute; top: 10px; right: 10px; color: white; font-size: 14px; background: rgba(0,0,0,0.4); padding: 5px 10px; border-radius: 5px; }
        #counter { top: 40px; }
        #noVideos { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: red; font-size: 20px; display: none; text-align: center; }
    </style>
</head>
<body>
    <div id=\"container\">
        <iframe id=\"player\" allow=\"autoplay; encrypted-media\" allowfullscreen></iframe>
        <div id=\"controls\">
            <button id="backBtn" onclick=\"window.pywebview.api.back()\">⏮ Back</button>
            <button id="nextBtn" onclick=\"window.pywebview.api.next()\">⏭ Next</button>
            <button id="downscale" onclick=\"window.pywebview.api.scaleDown()\">➖ Scale</button>
            <button id="upscale" onclick=\"window.pywebview.api.scaleUp()\">➕ Scale</button>
            <button onclick=\"window.pywebview.api.close()\">❌ Close</button>
        </div>
        <div id=\"scaleDisplay\">Scale: 1.0x</div>
        <div id=\"counter\">0 / 0</div>
        <div id=\"noVideos\">Error: No routes available with your item</div>
    </div>
    <script>
        function loadVideo(url) {
            document.getElementById('player').src = url;
        }
        function updateCounter(index, total) {
            document.getElementById('counter').textContent = `${index} / ${total}`;
            document.title = `Routes Mod (${index}/${total})`;
            const backBtn = document.getElementById('backBtn');
            const nextBtn = document.getElementById('nextBtn');
            nextBtn.disabled = index == total
            backBtn.disabled = index == 1 ||index == 0
        }
        
        function updateScale(scale) {
            document.getElementById('scaleDisplay').textContent = `Scale: ${scale.toFixed(1)}x`;
        }
        
        function showNoVideos(show) {
            document.getElementById('noVideos').style.display = show ? 'block' : 'none';
            document.getElementById('player').style.display = show ? 'none' : 'block';
        }
        
        function noScale() {
            document.getElementById('downscale').disabled = true
            document.getElementById('upscale').disabled = true
        }
        
    </script>
</body>
</html>
"""

# ---------------------- Helper Functions ----------------------

def extract_youtube_id(_url):
    pattern = r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]{11})"
    match = re.search(pattern, _url)
    return match.group(1) if match else None

def get_monitor():
    monitors = screeninfo.get_monitors()
    for monitor in monitors:
        if getattr(monitor, "is_primary", True):
            return monitor
    return monitors[0]

def get_screen_size():
    try:
        monitor = get_monitor()
        return monitor.width, monitor.height
    except:
        return 1920, 1080

def get_nearest_scale(input_scale):
    return min(allowed_scales, key=lambda x: abs(x - input_scale))

# ---------------------- App Logic ----------------------

def reload_video():
    global room, items, window, filtered_segments, current_index
    items.clear()
    filtered_segments.clear()
    current_index = 0

    try:
        path = os.path.join(base_path, "text.txt")
        if not os.path.exists(path):
            raise FileNotFoundError("text.txt missing")

        with open(path, "r") as f:
            lines = [line.strip() for line in f if line.strip()]
            room, *items[:] = lines

        response = requests.get(f"http://159.65.35.198/{room}")
        if response.status_code != 200:
            raise Exception(f"{response.json().get("data", {}).get("error", [])}")

        data = response.json().get("data", {}).get("segments", [])
        for segment in data:
            required = segment.get("required_items", [])
            if isinstance(required, str):
                required = [required]
            if "nothing" in required or all(i in items for i in required):
                filtered_segments.append(segment)

        if filtered_segments:
            play_segment(0)
        else:
            raise Exception(f"No routes available with your item")


    except Exception as e:
        if window:
            error_message = "Error: " + str(e).replace("'", "").replace('"', "")
            window.evaluate_js(f"document.getElementById('noVideos').textContent = '{error_message}'; showNoVideos(true); updateCounter(0, 0); loadVideo('https://www.youtube.com')")

def play_segment(index):
    global current_index
    current_index = index
    video_url = filtered_segments[index]["video"]
    video_id = extract_youtube_id(video_url)
    if video_id:
        embed_url = f"https://www.youtube.com/embed/{video_id}?enablejsapi=1"
        try:
            js = f"loadVideo('{embed_url}'); updateCounter({index+1}, {len(filtered_segments)}); showNoVideos(false);"
            window.evaluate_js(js)
        except Exception as e:
            print("JS Error:", e)

def cycle_video_next():
    if filtered_segments and current_index + 1 < len(filtered_segments):
        play_segment(current_index + 1)

def cycle_video_back():
    if filtered_segments and current_index > 0:
        play_segment(current_index - 1)

# ---------------------- Flask API ----------------------

app = Flask(__name__)

@app.route("/reload", methods=["POST"])
def reload_window():
    reload_video()
    return "OK"

threading.Thread(target=lambda: app.run(port=8123), daemon=True).start()

# ---------------------- PyWebView API ----------------------

class Api:
    def next(self): cycle_video_next()
    def back(self): cycle_video_back()
    def close(self): webview.windows[0].destroy()

    def scaleDown(self): self.adjust_scale(-0.1)
    def scaleUp(self): self.adjust_scale(0.1)

    def redraw(self, scale):
        overlay_width = int(base_width * scale)
        overlay_height = int(base_height * scale)
        overlay_x = screen_width - overlay_width
        overlay_y = 0
        window.resize(overlay_width, overlay_height)
        window.move(overlay_x, overlay_y)
        window.evaluate_js(f"updateScale({scale})")

    def adjust_scale(self, delta):
        global scale
        index = allowed_scales.index(scale) if scale in allowed_scales else 9
        new_index = max(0, min(len(allowed_scales) - 1, index + int(delta * 10)))
        new_scale = allowed_scales[new_index]
        if new_scale != scale:
            scale = new_scale
            self.redraw(scale)

api = Api()

# ---------------------- Settings Init ----------------------

if not os.path.exists(text_path):
    with open(text_path, "w") as f:
        f.write("overlay_mode: true\nscale: 1.0")
else:
    with open(text_path, "r") as file:
        for line in file:
            line = line.strip()
            if line.startswith("overlay_mode:"):
                overlay_mode = line.split(":", 1)[1].strip().lower() == "true"
            elif line.startswith("scale:"):
                try:
                    scale = get_nearest_scale(float(line.split(":", 1)[1].strip()))
                except ValueError:
                    scale = 1.0

screen_width, screen_height = get_screen_size()

if overlay_mode:
    window = webview.create_window(
        windowtitle, html=html_template, js_api=api,
        height=0, width=0, resizable=False, frameless=True, on_top=False
    )
else:
    window = webview.create_window(windowtitle, html=html_template, js_api=api)

def on_loaded():
    time.sleep(0.5)
    reload_video()
    if overlay_mode:
        window.on_top = True
        api.redraw(scale)
    else:
        window.evaluate_js("noScale()")

webview.start(on_loaded, gui="edgechromium")