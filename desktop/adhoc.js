// Ad-hoc codesign on macOS: arm64 refuses unsigned apps as "damaged"; this downgrades it to the right-click > Open prompt.
const { execFileSync } = require('child_process')
exports.default = ctx => {
  if (ctx.electronPlatformName !== 'darwin') return
  const app = `${ctx.appOutDir}/${ctx.packager.appInfo.productFilename}.app`
  execFileSync('codesign', ['--force', '--deep', '-s', '-', app], { stdio: 'inherit' })
}
