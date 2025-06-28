import requests
import re
import win32event
import win32api
import sys
import os
from flask import Flask
import threading
import webview

windowtitle = 'Routes Mod'
items = []
room = None
window = None

# --- Globals for cycling through videos ---
filtered_segments = []
current_index = 0

# --- Mutex check to ensure single instance ---
mutex = win32event.CreateMutex(None, False, "routes_mod")
last_error = win32api.GetLastError()
ERROR_ALREADY_EXISTS = 183

if last_error == ERROR_ALREADY_EXISTS:
    try:
        requests.post("http://localhost:8123/reload")
    except Exception as e:
        print("Could not contact existing instance", e)
    sys.exit(0)

# --- YouTube ID extractor function ---
def extract_youtube_id(_url):
    pattern = r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]{11})"
    match = re.search(pattern, _url)
    if match:
        return match.group(1)
    return None

# --- HTML template for embedded video player UI ---
html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta http-equiv="X-UA-Compatible" content="IE=edge" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Routes Mod Video Player</title>
<style>
  body { margin: 0; background: #000; }
  iframe {
    display: block;
    width: 100vw;
    height: 100vh;
    border: none;
  }
  #controls {
    position: fixed;
    top: 10px;
    left: 0;
    right: 0;
    text-align: center;
    z-index: 9999;
    user-select: none;
  }
  button {
    margin: 0 10px;
    padding: 10px 20px;
    font-size: 16px;
    border-radius: 5px;
    border: none;
    cursor: pointer;
    opacity: 0.8;
  }
  button:disabled {
    opacity: 0.4;
    cursor: default;
  }
  #backBtn { background: #555; color: white; }
  #nextBtn { background: #ff0000; color: white; }
  #closeBtn {
    background: #222;
    color: white;
    position: absolute;
    top: -10px;
    right: 10px;
  }
  #counter {
    color: white;
    font-size: 16px;
    margin-left: 20px;
  }
</style>
</head>
<body>

<div id="controls">
  <button id="closeBtn">X</button>
  <button id="backBtn" disabled>Back</button>
  <button id="nextBtn" disabled>Next</button>
  <span id="counter">0 / 0</span>
</div>

<iframe id="videoFrame" src=""></iframe>
<div id="noVideos" style="color: white; text-align: center; font-size: 24px; margin-top: 20px; display: none;">
  No routes with your items
</div>

<script>
  const backBtn = document.getElementById('backBtn');
  const nextBtn = document.getElementById('nextBtn');
  const closeBtn = document.getElementById('closeBtn');
  const counter = document.getElementById('counter');
  const iframe = document.getElementById('videoFrame');

  backBtn.onclick = () => {
    window.pywebview.api.back();
  };
  nextBtn.onclick = () => {
    window.pywebview.api.next();
  };
  closeBtn.onclick = () => {
    window.pywebview.api.close();
  };

  window.updateCounter = (current, total) => {
    counter.textContent = current + " / " + total;
  };
  window.updateButtons = (current, total) => {
    backBtn.disabled = current <= 1;
    nextBtn.disabled = current >= total;
  };
  window.loadVideo = (url) => {
    iframe.src = url;
  };
  window.showNoVideos = (show) => {
    document.getElementById('noVideos').style.display = show ? 'block' : 'none';
    document.getElementById('videoFrame').style.display = show ? 'none' : 'block';
    document.getElementById('controls').style.display = show ? 'none' : 'block';
  };
</script>

</body>
</html>
"""

# --- Reload video list and update UI ---
def reload_video():
    global room, items, window, filtered_segments, current_index
    items.clear()
    filtered_segments.clear()
    current_index = 0

    try:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        text_path = os.path.join(base_path, 'text.txt')
        if not os.path.exists(text_path):
            raise FileNotFoundError(f"text.txt not found in: {base_path}")

        with open(text_path, 'r') as file:
            for i, line in enumerate(file):
                line = line.strip()
                if i == 0:
                    room = line
                else:
                    items.append(line)

        if not room:
            raise ValueError("Room name missing in text.txt")

        response = requests.get('http://159.65.35.198/' + room)

        if response.status_code == 406:
            raise Exception("Server returned 406: Invalid request or unsupported room")

        if response.status_code != 200:
            raise Exception(f"Unexpected API error: {response.status_code}")

        data = response.json().get('data', {}).get('segments', [])

        for segment in data:
            required = segment.get('required_items', [])
            if isinstance(required, str):
                required = [required]
            if "nothing" in required or all(req_item in items for req_item in required):
                filtered_segments.append(segment)

        if filtered_segments:
            video_url = filtered_segments[0]['video']
            video_id = extract_youtube_id(video_url)
            if video_id and window:
                new_url = 'https://www.youtube.com/embed/' + video_id + '?enablejsapi=1'
                window.evaluate_js(f"""
                    document.getElementById('noVideos').textContent = 'No routes with your items';
                    loadVideo('{new_url}');
                    updateCounter(1, {len(filtered_segments)});
                    updateButtons(1, {len(filtered_segments)});
                    showNoVideos(false);
                """)
                return new_url
        else:
            if window:
                window.evaluate_js("""
                    document.getElementById('noVideos').textContent = 'No routes with your items';
                    showNoVideos(true);
                """)

    except Exception as e:
        print("Failed to load video info:", e)
        if window:
            error_msg = str(e).replace("'", "\\'")
            window.evaluate_js(f"""
                document.getElementById('noVideos').textContent = 'Error: {error_msg}';
                showNoVideos(true);
            """)

    return ''

# --- Move to next video ---
def cycle_video_next():
    global current_index, filtered_segments, window
    if not filtered_segments:
        return
    current_index = min(current_index + 1, len(filtered_segments) - 1)
    video_url = filtered_segments[current_index]['video']
    video_id = extract_youtube_id(video_url)
    if video_id:
        new_url = 'https://www.youtube.com/embed/' + video_id + '?enablejsapi=1'
        if window:
            window.evaluate_js(f"""
                loadVideo('{new_url}');
                updateCounter({current_index+1}, {len(filtered_segments)});
                updateButtons({current_index+1}, {len(filtered_segments)});
            """)

# --- Move to previous video ---
def cycle_video_back():
    global current_index, filtered_segments, window
    if not filtered_segments:
        return
    current_index = max(current_index - 1, 0)
    video_url = filtered_segments[current_index]['video']
    video_id = extract_youtube_id(video_url)
    if video_id:
        new_url = 'https://www.youtube.com/embed/' + video_id + '?enablejsapi=1'
        if window:
            window.evaluate_js(f"""
                loadVideo('{new_url}');
                updateCounter({current_index+1}, {len(filtered_segments)});
                updateButtons({current_index+1}, {len(filtered_segments)});
            """)

# --- Python API exposed to JS ---
class Api:
    def next(self):
        cycle_video_next()
    def back(self):
        cycle_video_back()
    def close(self):
        webview.windows[0].destroy()

# --- Flask API to handle reload requests ---
app = Flask(__name__)

@app.route('/reload', methods=['POST'])
def reload_window():
    reload_video()
    return 'OK'

# --- Run Flask server in a separate thread ---
def run_server():
    app.run(port=8123)

threading.Thread(target=run_server, daemon=True).start()

# --- Create pywebview window with overlay behavior ---
api = Api()

base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
text_path = os.path.join(base_path, 'settings.txt')

screen_width = 1920
overlay_width = 640
overlay_height = 360
overlay_x = screen_width - overlay_width
overlay_y = 0
overlay_mode = True


# --- Get settings from settings.txt or create settings.txt if it does not exist ---
if not os.path.exists(text_path):
    with open(text_path, 'w') as f:
        f.write('overlay_mode: true \noverlay_width: 640 \noverlay_height: 480 \nscreen_width: 1920')
else:
    with open(text_path, 'r') as file:
        for i, line in enumerate(file):
            line = line.strip()
            if i == 0 & line.startswith('overlay_mode:'):
                _overlay_mode = line.replace('overlay_mode: ', '')
                if _overlay_mode == 'false': overlay_mode = False
            if i == 1 & line.startswith('overlay_width:') & overlay_mode == True:
                _overlay_width = line.replace('overlay_width: ', '')
                overlay_width = int(_overlay_width)
            if i == 2 & line.startswith('overlay_height:') & overlay_mode == True:
                _overlay_height = line.replace('overlay_height: ', '')
                overlay_height = int(_overlay_height)
            if i== 3 & line.startswith('screen_width:') & overlay_mode == True:
                _screen_width = line.replace('screen_width: ', '')
                screen_width = int(_screen_width)

# --- Draw the webview either as overlay or normal ---
if overlay_mode:
    window = webview.create_window(
        windowtitle,
        html=html_template,
        js_api=api,
        width=overlay_width,
        height=overlay_height,
        resizable=False,
        frameless=True,
        on_top=True
    )
else:
    window = webview.create_window(windowtitle,
        html=html_template,
        js_api=api)



# --- Load initial video after window is ready ---
def on_loaded():
    reload_video()
    if overlay_mode:
        webview.windows[0].move(overlay_x, overlay_y)

webview.start(on_loaded, gui='edgechromium')
