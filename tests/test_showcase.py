"""showcase: the scripts parse, the storyboards validate, a fixture app renders to stills and mp4, the ElevenLabs layer
runs against a local stub, and the key never leaks. Rendering skips with the reason when ffmpeg or Playwright is missing."""
import base64
import json
import math
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from conftest import PLUGIN

SKILL = PLUGIN / "skills" / "showcase"
SCRIPTS = SKILL / "scripts"
CLINIDECK_DECKS = os.path.expanduser("~/dev/lipe/clinideck/marketing/decks")
FAKE_KEY = "sk_test_FAKEKEY_9f8e7d6c5b4a3210"


def node(script, *args, cwd, env=None, timeout=300):
    full = {**os.environ, **(env or {})}
    full.pop("ELEVENLABS_API_KEY", None) if env is None or "ELEVENLABS_API_KEY" not in env else None
    return subprocess.run(["node", str(SCRIPTS / script), *map(str, args)], cwd=cwd, env=full,
                          capture_output=True, text=True, timeout=timeout)


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def ffprobe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def video_stream(info):
    return next(s for s in info["streams"] if s["codec_type"] == "video")


def has_audio(info):
    return any(s["codec_type"] == "audio" for s in info["streams"])


# ── static checks ───────────────────────────────────────────────────────────────────────────────────────────────────

def all_scripts():
    return sorted(str(p.relative_to(SCRIPTS)) for p in SCRIPTS.rglob("*.mjs"))


def test_the_skill_ships_every_script():
    assert {"doctor.mjs", "capture.mjs", "compose.mjs", "audio.mjs", "art.mjs"} <= set(all_scripts())


@pytest.mark.parametrize("script", all_scripts() or ["missing"])
def test_script_passes_node_check(script):
    r = subprocess.run(["node", "--check", str(SCRIPTS / script)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_the_plugin_names_no_project():
    hits = []
    for path in SKILL.rglob("*"):
        if path.is_file():
            text = path.read_text(errors="ignore")
            for word in ("clinideck", "#2dd4bf", "#10151c", "manrope", "zzportal"):
                if word in text.lower():
                    hits.append(f"{path.relative_to(SKILL)}: {word}")
    assert not hits


def test_masking_presets_hide_br_documents_phone_and_email(tmp_path):
    probe = tmp_path / "probe.mjs"
    probe.write_text(
        f"import {{ maskText }} from {json.dumps((SCRIPTS / 'lib' / 'mask.mjs').as_uri())};\n"
        "const r = maskText('CPF 123.456.789-09, CNPJ 12.345.678/0001-90, +55 (11) 98765-4321, ana.silva@example.com');\n"
        "console.log(JSON.stringify(r));\n")
    r = subprocess.run(["node", str(probe)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    for raw in ("123.456.789-09", "12.345.678/0001-90", "98765", "ana.silva"):
        assert raw not in out["text"]
    assert out["count"] == 4 and "example.com" in out["text"] and "4321" in out["text"]


# ── storyboard validation ───────────────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("deck", ["area-do-paciente-reel.json", "novidades-2026-10-24.json"])
def test_existing_storyboards_validate_unchanged(deck, tmp_path):
    path = os.path.join(CLINIDECK_DECKS, deck)
    if not os.path.isfile(path):
        pytest.skip(f"source storyboard not on this machine: {path}")
    before = open(path, "rb").read()
    r = node("compose.mjs", "--validate", "--storyboard", path, cwd=tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert re.search(r"^ok: \d+ scenes", r.stdout, re.M)
    assert open(path, "rb").read() == before


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) if not isinstance(data, str) else data)
    return path


PORTRAIT = {
    "theme": "dark", "fps": 30, "cover": {"scene": "gancho", "at": 0.8},
    "scenes": [
        {"id": "gancho", "duration": 1.2,
         "caption": {"text": "Your week in one screen", "accent": ["one", "screen"], "sub": "Demo data"},
         "narration": {"text": "Your week in one screen."},
         "shots": [{"shot": "inicio", "at": 0}], "taps": [{"at": 0.7, "point": "tap"}],
         "camera": [{"at": 0, "s": 1}, {"at": 1.0, "s": 1.25, "focus": {"point": "title"}}]},
        {"id": "rola", "duration": 1.0, "caption": {"text": "Scroll to any day"},
         "narration": {"text": "Scroll to any day, 7 days ahead."},
         "shots": [{"shot": "lista", "at": 0, "in": "push", "scroll": [0, {"point": "item", "top": 80}],
                    "scrollAt": [0.1, 0.9]}]},
        {"id": "detalhe", "duration": 0.8, "narration": {"text": "Open the detail."},
         "shots": [{"shot": "detalhe", "at": 0, "in": "rise"}]},
        {"id": "fecho", "device": False, "duration": 1.0, "narration": {"text": "Try Demo free for 7 days."},
         "cta": {"title": "Try <em>Demo</em>", "lines": ["Free for 7 days"], "pill": "demo.example",
                 "footer": "demo.example"}},
    ],
    "carousel": [{"eyebrow": "Demo", "title": "One screen", "sub": "All of it",
                  "shots": [{"shot": "inicio", "at": 0}], "camera": [{"at": 0, "s": 1}]}],
}

LANDSCAPE = {
    "format": "landscape", "theme": "dark", "fps": 30, "output": "novidades-demo.mp4",
    "poster": {"scene": "abertura", "at": 0.5},
    "voice": {"voice_id": "stub-voice", "name": "Stub", "model_id": "eleven_v4", "language_code": "en",
              "settings": {"speed": 1.0}, "pronounce": {"7": "seven"}},
    "music": {"model_id": "music_v2_5", "prompt": "calm instrumental"},
    "audio": {"leadIn": 0.15, "sceneLead": 0.18, "tail": 0.6},
    "scenes": [
        {"id": "abertura", "device": False, "duration": 1.0, "narration": {"text": "What is new in Demo."},
         "cta": {"title": "What is new in <em>Demo</em>", "lines": ["October"], "footer": "demo.example"}},
        {"id": "painel", "duration": 1.0, "narration": {"text": "The panel shows 7 days at once."},
         "caption": {"text": "Seven days at once"},
         "shots": [{"shot": "painel", "at": 0, "in": "fade", "url": "/home"}],
         "taps": [{"at": 0.5, "point": "tap"}], "camera": [{"at": 0, "s": 1}, {"at": 0.9, "s": 1.1, "fx": 640}]},
    ],
}


@pytest.mark.parametrize("board", [PORTRAIT, LANDSCAPE], ids=["portrait", "landscape"])
def test_storyboard_of_each_format_validates(board, tmp_path):
    sb = write(tmp_path / "sb.json", board)
    r = node("compose.mjs", "--validate", "--storyboard", sb, cwd=tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"format {board.get('format', 'portrait')}" in r.stdout


def test_validate_reports_every_broken_field(tmp_path):
    bad = {"format": "square", "cover": {"scene": "nope", "at": 1},
           "scenes": [{"duration": -1, "shots": [{"in": "spin"}]}, {"id": "a", "duration": 1, "taps": [{"point": 3}]}]}
    sb = write(tmp_path / "bad.json", bad)
    r = node("compose.mjs", "--validate", "--storyboard", sb, cwd=tmp_path)
    assert r.returncode == 1
    for needle in ("format", "scenes[0].id", "scenes[0].duration", "scenes[0].shots[0].shot",
                   "scenes[0].shots[0].in", "scenes[1].taps[0]", "cover.scene"):
        assert needle in r.stderr, needle


def test_validate_checks_shot_and_point_names_against_captured_scenes(tmp_path):
    sb = write(tmp_path / "sb.json", PORTRAIT)
    cenas = {"viewport": {"width": 390, "height": 844}, "dsf": 2, "theme": "dark",
             "scenes": {"inicio": {"file": "inicio.png", "width": 390, "height": 844, "scrollY": 0,
                                   "points": {"tap": {"x": 1, "y": 1, "w": 1, "h": 1}}}}}
    write(tmp_path / "out" / "cenas" / "cenas.json", cenas)
    r = node("compose.mjs", "--validate", "--storyboard", sb, "--out", tmp_path / "out", cwd=tmp_path)
    assert r.returncode == 1
    assert "lista" in r.stderr and "title" in r.stderr


# ── fixture app and full render ─────────────────────────────────────────────────────────────────────────────────────

LOGIN_HTML = """<!doctype html><html><head><meta charset="utf-8"><title>Login</title></head><body>
<form id="f"><input id="email" type="email"><input id="password" type="password">
<button id="go" type="submit" disabled>Sign in</button></form>
<script>
const f = document.getElementById('f'), go = document.getElementById('go');
setTimeout(() => {
  const check = () => (go.disabled = !(email.value && password.value));
  email.addEventListener('input', check); password.addEventListener('input', check); check();
}, 300);
f.addEventListener('submit', (e) => { e.preventDefault(); localStorage.setItem('token', email.value); location.href = '/home.html'; });
</script></body></html>"""

HOME_HTML = """<!doctype html><html><head><meta charset="utf-8"><title>Home</title>
<meta name="viewport" content="width=device-width, initial-scale=1"><style>
html{background:#fff;color:#111;font:16px system-ui} html.dark{background:#16181d;color:#eee}
body{margin:0;padding:16px 16px 90px} li{padding:14px 0;border-bottom:1px solid #8884}
nav.bottom{position:fixed;left:0;right:0;bottom:0;height:64px;background:#2b6;color:#fff;display:flex;align-items:center;justify-content:center}
#cta{padding:12px 20px;font-size:18px} #detail{display:none;padding:20px;background:#8882;margin-top:12px}
.skeleton{height:20px;background:#8884}
</style><script>document.documentElement.classList.toggle('dark', localStorage.getItem('demo_theme') === 'dark');</script>
</head><body><main>
<div id="loading" class="skeleton"></div>
<script>
if (!localStorage.getItem('token')) document.write('<p>signed out</p>');
else setTimeout(() => {
  document.getElementById('loading').remove();
  const items = Array.from({length: 40}, (_, i) => '<li id="item-' + i + '">Appointment ' + i + ' at 10:00, room ' + (i % 4 + 1) + '</li>').join('');
  document.querySelector('main').insertAdjacentHTML('beforeend',
    '<h1>Your week</h1><p>Ana, CPF 123.456.789-09, ana.silva@example.com, +55 (11) 98765-4321</p>' +
    '<button id="cta">Open detail</button><div id="detail">Detail of the appointment</div><ul>' + items + '</ul>');
  document.getElementById('cta').addEventListener('click', () => (document.getElementById('detail').style.display = 'block'));
}, 400);
</script></main><nav class="bottom">Home · Agenda · Profile</nav></body></html>"""


def toolchain():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        return "ffmpeg/ffprobe not on PATH"
    r = subprocess.run(["node", str(SCRIPTS / "doctor.mjs"), "--json"], capture_output=True, text=True,
                       cwd=SCRIPTS, env={**os.environ, "HOME": os.environ.get("HOME", "")})
    try:
        report = json.loads(r.stdout)
    except ValueError:
        return f"doctor.mjs did not answer JSON: {r.stderr[-300:]}"
    if not report.get("playwright", {}).get("ok"):
        return "Playwright not resolvable: run `node doctor.mjs --install`"
    return None


@pytest.fixture(scope="module")
def project(tmp_path_factory):
    reason = toolchain()
    if reason:
        pytest.skip(reason)
    root = tmp_path_factory.mktemp("project")
    site = root / "site"
    write(site / "login.html", LOGIN_HTML)
    write(site / "home.html", HOME_HTML)
    port = free_port()
    server = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1", "-d", str(site)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.1)
    write(root / ".claude" / "showcase.json", {
        "product": "Demo", "site": "demo.example", "locale": "en-US", "timezone": "UTC",
        "baseUrl": f"http://127.0.0.1:{port}",
        "theme": {"default": "dark", "localStorage": "demo_theme", "darkClass": "dark"},
        "login": {"url": "/login.html", "user": "#email", "password": "#password", "submit": "#go",
                  "success": "/home", "userEnv": "DEMO_USER", "passwordEnv": "DEMO_PASSWORD"},
        "output": "marketing",
    })
    yield root
    server.terminate()


ENV = {"DEMO_USER": "demo@example.com", "DEMO_PASSWORD": "demo-password"}


@pytest.fixture(scope="module")
def portrait(project):
    out = project / "marketing" / "videos" / "demo-reel"
    plan = write(project / "plan-portrait.json", {
        "viewport": {"width": 390, "height": 844}, "dsf": 2, "mobile": True, "theme": "dark", "login": True,
        "scenes": [
            {"name": "inicio", "url": "/home.html", "wait": [{"selector": "#cta"}, {"content": True}],
             "points": {"tap": "#cta", "title": "h1"}},
            {"name": "lista", "url": "/home.html", "wait": [{"selector": "#item-30"}], "full": True,
             "bar": "nav.bottom", "points": {"item": "#item-20"}},
            {"name": "detalhe", "url": "/home.html", "wait": [{"selector": "#cta"}],
             "actions": [{"click": "#cta"}, {"wait": {"selector": "#detail"}}], "points": {"detail": "#detail"}},
        ]})
    r = node("capture.mjs", "--plan", plan, "--out", out, cwd=project, env=ENV)
    assert r.returncode == 0, r.stdout + r.stderr
    sb = write(project / "marketing" / "decks" / "demo-reel.json", PORTRAIT)
    r = node("compose.mjs", "--storyboard", sb, "--out", out, cwd=project)
    assert r.returncode == 0, r.stdout + r.stderr
    return out


@pytest.fixture(scope="module")
def landscape(project):
    out = project / "marketing" / "videos" / "demo-novidades"
    plan = write(project / "plan-landscape.json", {
        "viewport": {"width": 1280, "height": 720}, "dsf": 1, "theme": "dark", "login": True,
        "scenes": [{"name": "painel", "url": "/home.html", "wait": [{"selector": "#cta"}], "points": {"tap": "#cta"}}]})
    r = node("capture.mjs", "--plan", plan, "--out", out, cwd=project, env=ENV)
    assert r.returncode == 0, r.stdout + r.stderr
    music = out / "music.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=330:duration=4",
                    "-ac", "2", str(music)], check=True)
    sb = write(project / "marketing" / "decks" / "demo-novidades.json", LANDSCAPE)
    r = node("compose.mjs", "--storyboard", sb, "--out", out, "--music", music, cwd=project)
    assert r.returncode == 0, r.stdout + r.stderr
    return out


def test_capture_writes_the_scenes_in_the_compositor_shape(portrait):
    cenas = json.loads((portrait / "cenas" / "cenas.json").read_text())
    assert cenas["viewport"] == {"width": 390, "height": 844} and cenas["dsf"] == 2 and cenas["theme"] == "dark"
    inicio, lista = cenas["scenes"]["inicio"], cenas["scenes"]["lista"]
    assert inicio["file"] == "inicio.png" and inicio["width"] == 390 and inicio["height"] == 844
    assert set(inicio["points"]["tap"]) == {"x", "y", "w", "h"} and inicio["url"] == "/home.html"
    assert inicio["masked"] >= 3
    assert lista["height"] > 844 and lista["bar"]["file"] == "lista-barra.png" and round(lista["bar"]["h"]) == 64
    for name in ("inicio", "lista", "lista-barra", "detalhe"):
        assert ffprobe(portrait / "cenas" / f"{name}.png")["streams"][0]["width"] == 780


def test_portrait_reel_and_stills(portrait):
    info = ffprobe(portrait / "reel.mp4")
    v = video_stream(info)
    assert (v["width"], v["height"], v["r_frame_rate"], v["pix_fmt"]) == (1080, 1920, "30/1", "yuv420p")
    assert abs(float(info["format"]["duration"]) - 4.0) < 0.1
    assert not has_audio(info), "no narration and no music: the reel is silent"
    for still, size in (("capa-1080x1920.png", (1080, 1920)), ("capa-1080x1350.png", (1080, 1350)),
                        ("carrossel-01.png", (1080, 1350))):
        s = ffprobe(portrait / still)["streams"][0]
        assert (s["width"], s["height"]) == size, still
    frames = sorted(p.name for p in (portrait / "frames").glob("*.png"))
    assert frames == ["01-gancho.png", "02-rola.png", "03-detalhe.png", "04-fecho.png"]


def test_landscape_video_mixes_music_without_narration(landscape):
    info = ffprobe(landscape / "novidades-demo.mp4")
    v = video_stream(info)
    assert (v["width"], v["height"], v["r_frame_rate"], v["pix_fmt"]) == (1920, 1080, "30/1", "yuv420p")
    assert abs(float(info["format"]["duration"]) - 2.0) < 0.15
    audio = next(s for s in info["streams"] if s["codec_type"] == "audio")
    assert audio["codec_name"] == "aac" and audio["sample_rate"] == "48000"
    assert ffprobe(landscape / "poster.jpg")["streams"][0]["width"] == 1920
    assert not (landscape / "legendas.vtt").exists(), "WebVTT needs spoken words"


def test_record_mode_makes_a_band_reel(project):
    out = project / "marketing" / "videos" / "demo-gravado"
    plan = write(project / "plan-record.json", {
        "viewport": {"width": 1024, "height": 768}, "theme": "dark", "login": True,
        "record": {"seconds": 3, "eyebrow": "Agenda", "headline": "Your week", "sub": "Demo data", "name": "agenda"},
        "scenes": [{"name": "agenda", "url": "/home.html", "wait": [{"selector": "#cta"}],
                    "actions": [{"scroll": {"by": 90, "steps": 3, "pause": 500}}]}]})
    r = node("capture.mjs", "record", "--plan", plan, "--out", out, cwd=project, env=ENV)
    assert r.returncode == 0, r.stdout + r.stderr
    info = ffprobe(out / "agenda-reel.mp4")
    v = video_stream(info)
    assert (v["width"], v["height"], v["pix_fmt"]) == (1080, 1920, "yuv420p")
    assert abs(float(info["format"]["duration"]) - 3.0) < 0.15


def test_art_typographic_and_deck_with_shot(project):
    out = project / "marketing" / "posts" / "demo-post"
    r = node("art.mjs", "--no-shot", "--headline", "One screen for the week", "--sub", "Demo", "--out", out,
             cwd=project)
    assert r.returncode == 0, r.stdout + r.stderr
    s = ffprobe(out / "post-feed.png")["streams"][0]
    assert (s["width"], s["height"]) == (1080, 1350)
    deck = write(project / "deck.json", {"eyebrow": "Agenda", "format": "story", "theme": "light",
                                         "shot": {"path": "/home.html", "focus": "#cta"},
                                         "slides": [{"headline": "A", "sub": "a"}, {"headline": "B", "withShot": True}]})
    r = node("art.mjs", "--deck", deck, "--out", out, "--name", "car", cwd=project, env=ENV)
    assert r.returncode == 0, r.stdout + r.stderr
    for name in ("car-01.png", "car-02.png"):
        s = ffprobe(out / name)["streams"][0]
        assert (s["width"], s["height"]) == (1080, 1920)


# ── ElevenLabs layer against a local stub ───────────────────────────────────────────────────────────────────────────

class Stub:
    def __init__(self, audio_bytes=b"ID3-fake-mp3", fail=False):
        self.calls, self.audio, self.fail = [], audio_bytes, fail
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                stub.calls.append((self.path, dict(self.headers), body))
                if stub.fail:
                    msg = json.dumps({"detail": f"invalid key {self.headers['xi-api-key']}"}).encode()
                    self.send_response(401)
                    self.end_headers()
                    self.wfile.write(msg)
                    return
                if self.path.startswith("/v1/text-to-speech/"):
                    text = body["text"]
                    payload = {"audio_base64": base64.b64encode(stub.audio).decode(),
                               "alignment": {"characters": list(text),
                                             "character_start_times_seconds": [i * 0.05 for i in range(len(text))],
                                             "character_end_times_seconds": [i * 0.05 + 0.04 for i in range(len(text))]}}
                    data = json.dumps(payload).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("character-cost", str(round(len(text) * 0.4)))
                else:
                    data = b"ID3-fake-music"
                    self.send_response(200)
                    self.send_header("Content-Type", "audio/mpeg")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()


@pytest.fixture
def stub():
    s = Stub()
    yield s
    s.close()


def expected_words(board):
    """Rebuild, independently of audio.mjs, the char range of every shown word in the text sent to the voice."""
    pronounce = board["voice"].get("pronounce", {})
    voice_text, out = "", []
    for scene in board["scenes"]:
        shown = scene["narration"]["text"].split(" ")
        spoken = []
        for token in shown:
            m = re.match(r"^(\w+)(.*)$", token)
            spoken.append(pronounce[m.group(1)] + m.group(2) if m and m.group(1) in pronounce else token)
        if voice_text:
            voice_text += " "
        for i, token in enumerate(spoken):
            start = len(voice_text)
            voice_text += token + (" " if i < len(spoken) - 1 else "")
            core = re.match(r"^\W*(.*?)[^\w%]*$", token).group(1) or token
            first = start + token.index(core)
            out.append((scene["id"], shown[i], first, first + len(core) - 1))
    return voice_text, out


def leaked(root, *texts):
    found = [t for t in texts if FAKE_KEY in t]
    for path in root.rglob("*"):
        if path.is_file() and FAKE_KEY.encode() in path.read_bytes():
            found.append(str(path))
    return found


def test_narration_maps_every_word_to_the_alignment(stub, tmp_path):
    sb = write(tmp_path / "sb.json", LANDSCAPE)
    env = {"ELEVENLABS_API_KEY": FAKE_KEY, "ELEVENLABS_BASE_URL": stub.url, "HOME": str(tmp_path / "home")}
    r = node("audio.mjs", "narration", "--storyboard", sb, "--out", tmp_path / "out", cwd=tmp_path, env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    path, headers, body = stub.calls[0]
    assert path.startswith("/v1/text-to-speech/stub-voice/with-timestamps")
    assert headers["xi-api-key"] == FAKE_KEY and body["model_id"] == "eleven_v4" and body["language_code"] == "en"
    voice_text, words = expected_words(LANDSCAPE)
    assert body["text"] == voice_text and "seven" in voice_text
    meta = json.loads((tmp_path / "out" / "audio" / "narracao.json").read_text())
    assert meta["voiceText"] == voice_text and meta["audio"] == "narracao.mp3"
    got = [(s["id"], w["text"], w["start"], w["end"]) for s in meta["scenes"] for w in s["words"]]
    assert got == [(sid, text, a * 0.05, b * 0.05 + 0.04) for sid, text, a, b in words]
    assert meta["speechEnd"] == pytest.approx((len(voice_text) - 1) * 0.05 + 0.04)
    assert (tmp_path / "out" / "audio" / "narracao.mp3").read_bytes() == b"ID3-fake-mp3"
    usage = json.loads((tmp_path / "out" / "audio" / "consumo.json").read_text())
    assert usage["totalCharacters"] == len(voice_text) and usage["totalCost"] == round(len(voice_text) * 0.4)
    assert not leaked(tmp_path / "out", r.stdout, r.stderr)

    again = node("audio.mjs", "narration", "--storyboard", sb, "--out", tmp_path / "out", cwd=tmp_path, env=env)
    assert again.returncode == 0 and len(stub.calls) == 1, "idempotent without --force"

    music = node("audio.mjs", "music", "--storyboard", sb, "--out", tmp_path / "out", cwd=tmp_path, env=env)
    assert music.returncode == 0, music.stderr
    length = stub.calls[1][2]["music_length_ms"]
    assert length == math.ceil(0.15 + meta["speechEnd"] + 0.6 + 1) * 1000
    assert stub.calls[1][2]["force_instrumental"] is True
    assert not leaked(tmp_path / "out", music.stdout, music.stderr)


def test_the_key_comes_from_the_owner_file_and_never_leaks_on_error(tmp_path):
    home = tmp_path / "home"
    write(home / ".config" / "keel" / "elevenlabs.env", f"# owner\nOTHER=1\nELEVENLABS_API_KEY='{FAKE_KEY}'\n")
    bad = Stub(fail=True)
    try:
        sb = write(tmp_path / "sb.json", LANDSCAPE)
        env = {"HOME": str(home), "ELEVENLABS_BASE_URL": bad.url}
        r = node("audio.mjs", "narration", "--storyboard", sb, "--out", tmp_path / "out", cwd=tmp_path, env=env)
        assert r.returncode == 1
        assert bad.calls and bad.calls[0][1]["xi-api-key"] == FAKE_KEY
        assert "401" in r.stderr and "***" in r.stderr
        assert not leaked(tmp_path / "out", r.stdout, r.stderr) if (tmp_path / "out").exists() else FAKE_KEY not in r.stderr + r.stdout
    finally:
        bad.close()


def test_doctor_reports_the_key_as_a_boolean_only(tmp_path):
    home = tmp_path / "home"
    r = node("doctor.mjs", "--json", cwd=tmp_path, env={"HOME": str(home), "ELEVENLABS_API_KEY": FAKE_KEY})
    report = json.loads(r.stdout)
    assert report["elevenlabsKey"] is True and FAKE_KEY not in r.stdout + r.stderr
    assert str(len(FAKE_KEY)) not in json.dumps(report["elevenlabs"] if "elevenlabs" in report else {})
    r = node("doctor.mjs", "--json", cwd=tmp_path, env={"HOME": str(home)})
    assert json.loads(r.stdout)["elevenlabsKey"] is False
    r = node("doctor.mjs", cwd=tmp_path, env={"HOME": str(home), "ELEVENLABS_API_KEY": FAKE_KEY})
    assert FAKE_KEY not in r.stdout + r.stderr and "ElevenLabs key" in r.stdout


def test_capture_refuses_a_host_that_is_not_local_nor_listed(tmp_path):
    probe = tmp_path / "probe.mjs"
    probe.write_text(
        f"import {{ assertCaptureHost }} from {json.dumps((SCRIPTS / 'lib' / 'config.mjs').as_uri())};\n"
        "const out = [];\n"
        "for (const [url, hosts] of [['http://127.0.0.1:3000', []], ['http://app.localhost', []],\n"
        "    ['https://app.acme.example', []], ['https://staging.acme.example', ['staging.acme.example']]]) {\n"
        "  try { assertCaptureHost(url, { captureHosts: hosts }); out.push('ok'); } catch (e) { out.push(e.message); }\n"
        "}\n"
        "console.log(JSON.stringify(out));\n")
    r = subprocess.run(["node", str(probe)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    local, sub, prod, staging = json.loads(r.stdout)
    assert (local, sub, staging) == ("ok", "ok", "ok")
    assert "never production" in prod
