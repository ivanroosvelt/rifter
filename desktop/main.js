// Electron shell: runs the bundled Python server on a free port and shows it in a window.
const { app, BrowserWindow } = require('electron')
const { spawn } = require('child_process')
const net = require('net')
const fs = require('fs')
const path = require('path')

const exe = process.platform === 'win32' ? '.exe' : ''
const res = app.isPackaged ? process.resourcesPath : path.join(__dirname, 'resources')
let server

app.whenReady().then(async () => {
  const port = await new Promise(r => {
    const s = net.createServer().listen(0, '127.0.0.1', () => { const p = s.address().port; s.close(() => r(p)) })
  })
  const home = path.join(app.getPath('userData'), 'rifter') // server serves index.html and data/ from its cwd
  fs.mkdirSync(home, { recursive: true })
  fs.copyFileSync(path.join(res, 'index.html'), path.join(home, 'index.html'))
  server = spawn(path.join(res, 'rifter-server' + exe), [], {
    cwd: home,
    env: { ...process.env, HOST: '127.0.0.1', PORT: String(port), PATH: path.join(res, 'bin') + path.delimiter + process.env.PATH },
    stdio: 'inherit',
  })
  const win = new BrowserWindow({ width: 1280, height: 800 })
  const url = `http://127.0.0.1:${port}`
  // ponytail: retry until the server is up, no readiness protocol
  win.webContents.on('did-fail-load', () => setTimeout(() => win.loadURL(url), 200))
  win.loadURL(url)
})

app.on('window-all-closed', () => app.quit())
app.on('quit', () => server && server.kill())
