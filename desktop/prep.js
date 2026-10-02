// Copies ffmpeg/ffprobe for this OS/arch into resources/bin (yt-dlp, deno and the server are added by CI).
const fs = require('fs')
const path = require('path')
const exe = process.platform === 'win32' ? '.exe' : ''
const bin = path.join(__dirname, 'resources', 'bin')
fs.mkdirSync(bin, { recursive: true })
fs.copyFileSync(require('ffmpeg-static'), path.join(bin, 'ffmpeg' + exe))
fs.copyFileSync(require('ffprobe-static').path, path.join(bin, 'ffprobe' + exe))
