import requests
import re
import win32event
import win32api
import sys
import os
from flask import Flask
import threading
import webview
import screeninfo

windowtitle = "Routes Mod"
items = []
room = None
window = None
base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
filtered_segments = []
current_index = 0

mutex = win32event.CreateMutex(None, False, "routes_mod")
last_error = win32api.GetLastError()
ERROR_ALREADY_EXISTS = 183

if last_error == ERROR_ALREADY_EXISTS:
    try:
        requests.post("http://localhost:8123/reload")
    except Exception as e:
        print("Could not contact existing instance", e)
    sys.exit(0)

def extract_youtube_id(_url):
    pattern = r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]{11})"
    match = re.search(pattern, _url)
    return match.group(1) if match else None

html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset=\"UTF-8\">
    <title>Routes Mod</title>
    <style>
        html, body { margin: 0; padding: 0; background-color: black; overflow: hidden; width: 100%; height: 100%; font-family: Arial, sans-serif; }
        #container { position: relative; width: 100%; height: 100%; }
        iframe { width: 100%; height: 100%; border: none; }
        #controls { position: absolute; bottom: 10px; left: 10px; display: flex; gap: 10px; z-index: 999; }
        button { background-color: rgba(255, 255, 255, 0.2); color: white; border: none; padding: 5px 10px; font-size: 14px; cursor: pointer; border-radius: 5px; }
        button:hover { background-color: rgba(255, 255, 255, 0.4); }
        #scaleDisplay { position: absolute; top: 10px; right: 10px; color: white; font-size: 14px; background: rgba(0, 0, 0, 0.4); padding: 5px 10px; border-radius: 5px; }
        #noVideos { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: red; font-size: 20px; display: none; text-align: center; max-width: 90%; word-wrap: break-word; }
    </style>
</head>
<body>
    <div id=\"container\">
        <iframe id=\"videoFrame\" allow=\"autoplay; encrypted-media\" allowfullscreen></iframe>
        <div id=\"controls\">
            <button onclick=\"window.pywebview.api.back()\">\u23ee Back</button>
            <button onclick=\"window.pywebview.api.next()\">\u23ed Next</button>
            <button onclick=\"window.pywebview.api.scaleDown()\">\u2796 Scale</button>
            <button onclick=\"window.pywebview.api.scaleUp()\">\u2795 Scale</button>
            <button onclick=\"window.pywebview.api.close()\">\u274c Close</button>
        </div>
        <div id=\"scaleDisplay\">Scale: 1.0x</div>
        <div id=\"noVideos\">No routes available</div>
    </div>
    <script>
        function loadVideo(url) { document.getElementById('videoFrame').src = url; }
        function updateCounter(index, total) { document.title = `Routes Mod (${index}/${total})`; }
        function updateScale(scale) { document.getElementById('scaleDisplay').textContent = `Scale: ${scale.toFixed(1)}x`; }
        function showNoVideos(show) { document.getElementById('noVideos').style.display = show ? 'block' : 'none'; }
    </script>
</body>
</html>
"""

def reload_video():
    global room, items, window, filtered_segments, current_index
    items.clear()
    filtered_segments.clear()
    current_index = 0
    try:
        text_path = os.path.join(base_path, "text.txt")
        if not os.path.exists(text_path): raise FileNotFoundError("text.txt missing")
        with open(text_path, "r") as f:
            lines = [line.strip() for line in f if line.strip()]
            room, *items[:] = lines
        response = requests.get("http://159.65.35.198/" + room)
        if response.status_code != 200: raise Exception(f"Server error: {response.status_code}")
        data = response.json().get("data", {}).get("segments", [])
        for segment in data:
            required = segment.get("required_items", [])
            if isinstance(required, str): required = [required]
            if "nothing" in required or all(i in items for i in required):
                filtered_segments.append(segment)
        if filtered_segments:
            play_segment(0)
        else:
            window.evaluate_js("showNoVideos(true);")
    except Exception as e:
        print("Error loading video:", e)
        if window:
            window.evaluate_js(f"document.getElementById('noVideos').textContent = 'Error: {str(e)}'; showNoVideos(true);")

def play_segment(index):
    global current_index
    current_index = index
    video_url = filtered_segments[index]["video"]
    video_id = extract_youtube_id(video_url)
    if video_id:
        new_url = f"https://www.youtube.com/embed/{video_id}?enablejsapi=1"
        window.evaluate_js(f"loadVideo('{new_url}'); updateCounter({index+1}, {len(filtered_segments)}); showNoVideos(false);")

def cycle_video_next():
    if filtered_segments and current_index + 1 < len(filtered_segments):
        play_segment(current_index + 1)

def cycle_video_back():
    if filtered_segments and current_index > 0:
        play_segment(current_index - 1)

class Api:
    def next(self): cycle_video_next()
    def back(self): cycle_video_back()
    def close(self): webview.windows[0].destroy()
    def scaleDown(self): self.adjust_scale(-0.1)
    def scaleUp(self): self.adjust_scale(0.1)

    def adjust_scale(self, delta):
        global scale, overlay_width, overlay_height, overlay_x, overlay_y
        index = allowed_scales.index(scale) if scale in allowed_scales else 9
        new_index = max(0, min(len(allowed_scales) - 1, index + int(delta * 10)))
        new_scale = allowed_scales[new_index]
        if new_scale != scale:
            scale = new_scale
            overlay_width = int(base_width * scale)
            overlay_height = int(base_height * scale)
            overlay_x = screen_width - overlay_width
            overlay_y = 0
            window.resize(overlay_width, overlay_height)
            window.move(overlay_x, overlay_y)
            window.evaluate_js(f"updateScale({scale})")

app = Flask(__name__)

@app.route("/reload", methods=["POST"])
def reload_window():
    reload_video()
    return "OK"

def run_server():
    app.run(port=8123)

threading.Thread(target=run_server, daemon=True).start()

api = Api()
text_path = os.path.join(base_path, "settings.txt")
scale = 1.0
overlay_mode = True
base_width = 640
base_height = 360
allowed_scales = [round(x * 0.1, 1) for x in range(1, 21)]


def get_screen_size():
    try:
        monitor = screeninfo.get_monitors()[0]
        return monitor.width, monitor.height
    except:
        return 1920, 1080

screen_width, screen_height = get_screen_size()

def get_nearest_scale(input_scale):
    return min(allowed_scales, key=lambda x: abs(x - input_scale))

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

overlay_width = int(base_width * scale)
overlay_height = int(base_height * scale)
overlay_x = screen_width - overlay_width
overlay_y = 0

window = webview.create_window(
    windowtitle, html=html_template, js_api=api,
    width=overlay_width, height=overlay_height,
    resizable=False, frameless=True, on_top=True
)

def on_loaded():
    reload_video()
    if overlay_mode:
        window.move(overlay_x, overlay_y)
        window.evaluate_js(f"updateScale({scale})")

webview.start(on_loaded, gui="edgechromium")
