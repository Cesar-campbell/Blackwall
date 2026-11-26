/* Capturas de la consola de administración de Keycloak para la guía técnica.
 * Uso: NODE_PATH=<carpeta con puppeteer-core> node pruebas/kc_consola.cjs <carpeta_salida>
 */
const puppeteer = require('puppeteer-core');
const fs = require('fs');
const os = require('os');
const path = require('path');

const BW = process.env.BW_HOME || path.join(os.homedir(), '.local/share/blackwall');
const ENV = Object.fromEntries(
  fs.readFileSync(path.join(BW, 'blackwall.env'), 'utf8').split('\n').filter(l => l.includes('=')).map(l => [l.split('=')[0], l.slice(l.indexOf('=') + 1)])
);
const OUT = process.argv[2];
const KC = 'https://acceso.localhost:8443';
const R = 'proyecto-accesos';
const esperar = ms => new Promise(r => setTimeout(r, ms));

const paginas = [
  ['kc-realm', `/admin/master/console/#/${R}/realm-settings`],
  ['kc-tokens', `/admin/master/console/#/${R}/realm-settings/tokens`],
  ['kc-seguridad', `/admin/master/console/#/${R}/realm-settings/security-defenses`],
  ['kc-clientes', `/admin/master/console/#/${R}/clients`],
  ['kc-scopes', `/admin/master/console/#/${R}/client-scopes`],
  ['kc-roles', `/admin/master/console/#/${R}/roles`],
  ['kc-grupos', `/admin/master/console/#/${R}/groups`],
  ['kc-federacion', `/admin/master/console/#/${R}/user-federation`],
  ['kc-flujos', `/admin/master/console/#/${R}/authentication`],
  ['kc-politicas', `/admin/master/console/#/${R}/authentication/policies`],
  ['kc-eventos', `/admin/master/console/#/${R}/events`],
  ['kc-usuarios', `/admin/master/console/#/${R}/users`],
];

(async () => {
  const b = await puppeteer.launch({
    executablePath: '/usr/bin/chromium-browser', headless: 'new',
    args: ['--no-sandbox', '--ignore-certificate-errors'], defaultViewport: { width: 1400, height: 900 },
  });
  const p = await b.newPage();
  await p.goto(KC + '/admin/master/console/', { waitUntil: 'load', timeout: 60000 });
  await p.waitForSelector('#username', { timeout: 30000 });
  await p.type('#username', ENV.KC_ADMIN_USER);
  await p.type('#password', ENV.KC_ADMIN_PASSWORD);
  await Promise.all([p.waitForNavigation({ waitUntil: 'load', timeout: 60000 }), p.click('#kc-login')]);
  await esperar(4000);
  for (const [n, ruta] of paginas) {
    try {
      await p.goto(KC + ruta, { waitUntil: 'load', timeout: 60000 });
      await p.reload({ waitUntil: 'load', timeout: 60000 });   // la consola es una SPA: se recarga para que tome el realm de la ruta
      await esperar(4500);
      await p.screenshot({ path: path.join(OUT, n + '.png') });
      console.log('ok', n);
    } catch (e) { console.log('FALLO', n, e.message.slice(0, 80)); }
  }
  await b.close();
})();
