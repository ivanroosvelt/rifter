import json
import os
import re
import subprocess
import threading
import time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs


# ponytail: age = mtime, touched on every serve/save; hourly sweep, no index/DB
TTL = {'data': 30 * 86400, 'data/pv': 86400}  # seconds unused before deletion


def touch(path):
    try:
        os.utime(path)
    except OSError:
        pass


def sweep():
    while True:
        now = time.time()
        for d, ttl in TTL.items():
            for e in os.scandir(d):
                if e.name.endswith('.mp3') and e.is_file() and now - e.stat().st_mtime > ttl:
                    os.remove(e.path)
                    if d == 'data' and os.path.exists(j := e.path[:-4] + '.json'):
                        os.remove(j)  # checkpoints die with their song
        time.sleep(3600)


class Handler(SimpleHTTPRequestHandler):
    # Serves index.html and data/<id>.mp3 from cwd; /api/load downloads the audio with yt-dlp.
    def do_GET(self):
        url = urlparse(self.path)
        args = parse_qs(url.query)
        if url.path == '/api/preview':
            return self.preview(args.get('id', [''])[0], args.get('start', ['0'])[0])
        if re.fullmatch(r'/data/(pv/)?[\w-]+\.mp3', url.path):
            touch(url.path[1:])
        if url.path not in ('/api/load', '/api/search'):
            return super().do_GET()
        q = args.get('q', [''])[0].strip()
        if not q:
            return self.reply(400, {'error': 'Falta la canción'})
        if url.path == '/api/search':
            p = subprocess.run(['yt-dlp', '--flat-playlist', '--print',
                                '%(id)s\t%(title)s\t%(duration_string)s\t%(channel)s', '--', f'ytsearch10:{q}'],
                               capture_output=True, text=True, timeout=60)
            keys = ('id', 'title', 'duration', 'channel')
            return self.reply(200, [dict(zip(keys, l.split('\t'))) for l in p.stdout.splitlines()])
        target = q if re.match(r'https?://', q) else f'ytsearch1:{q}'
        cmd = ['yt-dlp', '--no-playlist', '-x', '--audio-format', 'mp3',
               '-o', 'data/%(id)s.%(ext)s', '--no-simulate',
               '--print', 'after_move:%(id)s\t%(title)s', '--', target]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        except subprocess.TimeoutExpired:
            return self.reply(504, {'error': 'yt-dlp tardó demasiado'})
        lines = p.stdout.strip().splitlines()
        if p.returncode or not lines:
            return self.reply(502, {'error': (p.stderr.strip().splitlines() or ['yt-dlp falló'])[-1]})
        vid, title = lines[-1].split('\t', 1)
        self.reply(200, {'id': vid, 'title': title})

    def preview(self, vid, start):
        # 15 s mp3 clip, cached in data/pv/, then redirect to the static file
        if not re.fullmatch(r'[\w-]{11}', vid) or not start.isdigit():
            return self.reply(400, {'error': 'Petición inválida'})
        if not os.path.exists(f'data/pv/{vid}.mp3'):
            try:
                subprocess.run(['yt-dlp', '-f', 'bestaudio', '--download-sections', f'*{start}-{int(start) + 15}',
                                '-x', '--audio-format', 'mp3', '-o', 'data/pv/%(id)s.%(ext)s',
                                '--', f'https://youtu.be/{vid}'], capture_output=True, timeout=60)
            except subprocess.TimeoutExpired:
                pass
            if not os.path.exists(f'data/pv/{vid}.mp3'):
                return self.reply(502, {'error': 'No se pudo generar la vista previa'})
        self.send_response(302)
        self.send_header('Location', f'/data/pv/{vid}.mp3')
        self.end_headers()

    def do_PUT(self):
        # Saves the checkpoints of a song as data/<id>.json
        m = re.fullmatch(r'/data/([\w-]{1,64})\.json', self.path)
        size = int(self.headers.get('Content-Length', 0))
        if not m or size > 1_000_000:
            return self.reply(400, {'error': 'Petición inválida'})
        body = self.rfile.read(size)
        try:
            json.loads(body)
        except ValueError:
            return self.reply(400, {'error': 'JSON inválido'})
        with open(f'data/{m[1]}.json', 'wb') as f:
            f.write(body)
        touch(f'data/{m[1]}.mp3')
        self.reply(200, {})

    def reply(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == '__main__':
    os.makedirs('data/pv', exist_ok=True)
    threading.Thread(target=sweep, daemon=True).start()
    ThreadingHTTPServer((os.environ.get('HOST', '0.0.0.0'), int(os.environ.get('PORT', 8000))), Handler).serve_forever()
