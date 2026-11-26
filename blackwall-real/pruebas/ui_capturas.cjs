/* Prueba de interfaz en un navegador real (Chromium headless) y capturas para el informe.
 * Uso:  NODE_PATH=<carpeta con node_modules/puppeteer-core> node pruebas/ui_capturas.cjs <usuario> <prefijo> <vista1,vista2,...>
 * Vistas: login, keycloak, inicio, casos, caso, usuarios, usuario-nuevo, auditoria, config, cuenta, denegado
 * La contraseña sale de $BW_HOME/blackwall.env; el secreto TOTP (si el rol lo exige) de $BW_HOME/totp-<usuario>.secret
 */
const puppeteer = require('puppeteer-core');
const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');

const BW = process.env.BW_HOME || path.join(os.homedir(), '.local/share/blackwall');
const ENV = Object.fromEntries(fs.readFileSync(path.join(BW, 'blackwall.env'), 'utf8').split('\n').filter(l => l.includes('=')).map(l => [l.split('=')[0], l.slice(l.indexOf('=') + 1)]));
const [usuario, prefijo, lista] = process.argv.slice(2);
const vistas = (lista || 'inicio').split(',');
const SALIDA = path.join(__dirname, '..', 'evidencias', 'capturas');
fs.mkdirSync(SALIDA, { recursive: true });
const APP = 'https://app.localhost:8444';

function b32(s) { const A = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'; let bits = ''; for (const c of s.replace(/=+$/, '')) bits += A.indexOf(c).toString(2).padStart(5, '0'); const out = []; for (let i = 0; i + 8 <= bits.length; i += 8) out.push(parseInt(bits.slice(i, i + 8), 2)); return Buffer.from(out); }
function totp(secreto, paso = Math.floor(Date.now() / 30000)) {
  const buf = Buffer.alloc(8); buf.writeBigUInt64BE(BigInt(paso));
  const h = crypto.createHmac('sha1', b32(secreto)).update(buf).digest(); const o = h[h.length - 1] & 15;
  return String(((h.readUInt32BE(o) & 0x7fffffff) % 1000000)).padStart(6, '0');
}
const esperar = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const navegador = await puppeteer.launch({ executablePath: '/usr/bin/chromium-browser', headless: 'new', args: ['--no-sandbox', '--ignore-certificate-errors', '--disable-gpu'], defaultViewport: { width: 1360, height: 860, deviceScaleFactor: 1 } });
  const pag = await navegador.newPage();
  const problemas = [];
  pag.on('console', m => { if (['error', 'warning'].includes(m.type())) problemas.push(`[${m.type()}] ${m.text()}`.slice(0, 200)); });
  pag.on('pageerror', e => problemas.push('[pageerror] ' + String(e).slice(0, 200)));
  pag.on('requestfailed', r => problemas.push('[requestfailed] ' + r.url().slice(0, 100)));
  const foto = async n => { const f = path.join(SALIDA, `${prefijo}-${n}.png`); await pag.screenshot({ path: f }); console.log('captura', path.basename(f)); };

  await pag.goto(APP + '/', { waitUntil: 'load', timeout: 45000 });   // sin sesión, la app redirige al acceso
  await pag.waitForSelector('#username'); await esperar(900);
  if (vistas.includes('login') || vistas.includes('keycloak')) await foto('login');
  await pag.type('#username', usuario); await pag.type('#password', ENV.DEMO_PASSWORD);
  await Promise.all([pag.waitForNavigation({ waitUntil: 'load', timeout: 45000 }), pag.click('#kc-login')]);

  if (await pag.$('#otp')) {   // segundo factor
    const archivo = path.join(BW, `totp-${usuario}.secret`);
    const secreto = fs.readFileSync(archivo, 'utf8').trim();
    // anti-replay de Keycloak: no se reutiliza el código de la ventana en que se enroló
    if (Date.now() - fs.statSync(archivo).mtimeMs < 35000) await esperar(35000 - (Date.now() - fs.statSync(archivo).mtimeMs));
    if (vistas.includes('keycloak')) await foto('keycloak-totp');
    await pag.type('#otp', totp(secreto));
    await Promise.all([pag.waitForNavigation({ waitUntil: 'load', timeout: 45000 }), pag.click('#kc-login')]);
  }
  await pag.waitForSelector('body.in', { timeout: 10000 });
  await esperar(500);

  for (const v of vistas) {
    if (['login', 'keycloak'].includes(v)) continue;
    if (v === 'denegado') { await pag.evaluate(() => { location.hash = 'config'; }); }
    else if (v === 'caso' || v === 'usuario-nuevo') { /* modales: se abren desde su lista */ }
    else await pag.evaluate(x => { location.hash = x; }, v);
    await esperar(900);
    if (v === 'caso') { await pag.evaluate(() => { location.hash = 'casos'; }); await esperar(700); await pag.click('[data-a="ver"]'); await esperar(700); }
    if (v === 'usuario-nuevo') { await pag.evaluate(() => { location.hash = 'usuarios'; }); await esperar(900); await pag.click('[data-a="unuevo"]'); await esperar(500); }
    await foto(v);
    if (v === 'caso' || v === 'usuario-nuevo') { await pag.click('#modal [data-a="cerrar"]'); await esperar(300); }
  }
  const rol = await pag.$eval('#wRole', e => e.textContent), nombre = await pag.$eval('#wName', e => e.textContent);
  console.log(`sesión: ${nombre} · ${rol}`);
  console.log('problemas de consola/red:', problemas.length ? '\n  ' + problemas.join('\n  ') : 'ninguno');
  await navegador.close();
})().catch(e => { console.error('FALLO', e.message); process.exit(1); });
