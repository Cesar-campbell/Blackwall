<?php
declare(strict_types=1);

/** Controlador frontal: /api/* (API protegida por token), /auth/* y /callback (OIDC) y la página. */

require __DIR__ . '/../vendor/autoload.php';

use Blackwall\Config;
use Blackwall\Db;
use Blackwall\Oidc;
use Blackwall\Sesion;
use Blackwall\Sesiones;
use Blackwall\TokenInvalido;
use Blackwall\Tokens;

$metodo = $_SERVER['REQUEST_METHOD'];
$ruta = rtrim((string) parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH), '/') ?: '/';

if (str_starts_with($ruta, '/api/') || $ruta === '/api') {
    \Blackwall\Api::atender($metodo, $ruta);   // nunca usa cookies: solo Authorization: Bearer
}

function json_salida(int $st, array $d): never
{
    http_response_code($st);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($d, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT);
    exit;
}

/** Guarda en la sesión del servidor los tokens y los datos del usuario ya validados. */
function establecer(array $t, array $access, ?array $id): void
{
    $_SESSION['tok'] = ['access' => $t['access_token'], 'refresh' => $t['refresh_token'] ?? '', 'id' => $t['id_token'] ?? ($_SESSION['tok']['id'] ?? ''),
        'exp' => (int) $access['exp']];
    $_SESSION['u'] = [
        'sub' => $access['sub'], 'usuario' => $access['preferred_username'] ?? '?',
        'nombre' => $id['name'] ?? ($_SESSION['u']['nombre'] ?? ($access['preferred_username'] ?? '?')),
        'roles' => array_values(array_filter((array) ($access['roles'] ?? []), fn($r) => str_starts_with((string) $r, 'ROL_'))),
        'grupos' => array_values((array) ($access['groups'] ?? [])),
        'scopes' => array_values(array_filter(explode(' ', (string) ($access['scope'] ?? '')), fn($s) => str_contains($s, ':'))),
    ];
}

/** Cierra la sesión por una regla del servidor (inactividad o ciclos): revoca en Keycloak, anula la sesión y avisa al navegador. */
function cerrar_sesion(string $motivo): never
{
    $u = $_SESSION['u'] ?? ['usuario' => '?', 'sub' => null];
    if (!empty($_SESSION['tok']['refresh'])) {
        try {
            Oidc::revocar($_SESSION['tok']['refresh']);
        } catch (\Throwable) {
        }
    }
    if (!empty($_SESSION['sid'])) {
        Sesiones::cerrar($_SESSION['sid'], $motivo, $u['usuario'], $u['sub']);
    }
    Sesion::destruir();
    json_salida(401, ['error' => 'unauthorized', 'motivo' => $motivo, 'detalle' => $motivo === 'inactividad' ? 'Tu sesión se cerró por inactividad.' : 'Alcanzaste el tiempo máximo de sesión.']);
}

Sesion::iniciar();

switch ($ruta) {
    case '/':
        // Sin sesión se va directo al acceso (como cualquier aplicación); la pantalla de aviso solo se ve si algo falló
        if (empty($_SESSION['u']) && !isset($_GET['e'])) {
            $_SESSION['flujo'] = [];
            header('Location: ' . Oidc::urlLogin());
            break;
        }
        header('Content-Type: text/html; charset=utf-8');
        readfile(__DIR__ . '/vista.html');
        break;

    case '/auth/login':
        $_SESSION['flujo'] = [];
        header('Location: ' . Oidc::urlLogin());
        break;

    case '/auth/cambiar-clave':   // el cambio de contraseña lo hace Keycloak (acción requerida UPDATE_PASSWORD)
        isset($_SESSION['u']) || json_salida(401, ['error' => 'unauthorized']);
        header('Location: ' . Oidc::urlLogin('UPDATE_PASSWORD'));
        break;

    case '/callback':
        $o = $_SESSION['oidc'] ?? null;
        $fallo = function (string $codigo, string $detalle) use (&$o): never {
            Db::auditar('?', null, 'LOGIN', 'DENY', $detalle);
            Sesion::paso("App: $detalle", 'no');
            unset($_SESSION['oidc']);
            header('Location: /?e=' . $codigo);
            exit;
        };
        if (isset($_GET['error'])) {
            $fallo('idp', 'el proveedor de identidad devolvió un error (' . preg_replace('/[^a-z_]/', '', (string) $_GET['error']) . ')');
        }
        if (!$o || time() - $o['t'] > 600) {
            $fallo('sesion', 'no hay un inicio de sesión en curso');
        }
        // state: protección CSRF del flujo de autorización
        if (!isset($_GET['state']) || !hash_equals($o['state'], (string) $_GET['state'])) {
            $fallo('state', 'el state recibido no coincide');
        }
        Sesion::paso('App: el state recibido coincide con el enviado ✓ (anti-CSRF)', 'ok');
        if (empty($_GET['code'])) {
            $fallo('code', 'falta el código de autorización');
        }
        try {
            $t = Oidc::intercambiar((string) $_GET['code']);
            Sesion::paso('App → Keycloak: POST /token (code + code_verifier). SHA256(verifier) == challenge ✓', 'ok');
            $id = Tokens::verificar($t['id_token'], 'ID', $o['nonce']);
            Sesion::paso('App valida el ID token: firma RS256 (JWKS) ✓ iss ✓ aud ✓ exp ✓ nonce ✓', 'ok');
            $access = Tokens::verificar($t['access_token'], 'Bearer');
            Sesion::paso('App valida el access token (vida ' . ($access['exp'] - $access['iat']) . ' s) y crea su propia sesión', 'ok');
        } catch (TokenInvalido $e) {
            $fallo('token', 'token rechazado: ' . $e->getMessage());
        } catch (\Throwable $e) {
            error_log('callback: ' . $e->getMessage());
            $fallo('idp', 'no se pudo completar el intercambio con el proveedor de identidad');
        }
        $flujo = $_SESSION['flujo'] ?? [];
        session_regenerate_id(true);    // evita fijación de sesión
        $_SESSION = ['flujo' => $flujo, 'csrf' => bin2hex(random_bytes(24))];
        establecer($t, $access, $id);
        $_SESSION['sid'] = (string) ($access['sid'] ?? bin2hex(random_bytes(8)));
        Sesiones::registrar($_SESSION['sid'], (string) ($access['preferred_username'] ?? '?'), (string) ($_SESSION['u']['roles'][0] ?? ''));
        Db::auditar($access['preferred_username'] ?? '?', $access['sub'], 'LOGIN', 'ALLOW', implode(',', $_SESSION['u']['roles']));
        header('Location: /');
        break;

    case '/auth/sesion':
        if (empty($_SESSION['u'])) {
            json_salida(401, ['error' => 'unauthorized', 'detalle' => 'No hay sesión.']);
        }
        $sid = (string) ($_SESSION['sid'] ?? '');
        if ($sid !== '' && ($m = Sesiones::evaluar($sid, $_SESSION['u']['usuario'], $_SESSION['u']['sub'], false)) !== null) {
            cerrar_sesion($m);
        }
        $forzar = isset($_GET['renovar']);
        if ($forzar || $_SESSION['tok']['exp'] - time() < 30) {
            if ($sid !== '' && ($m = Sesiones::renovar($sid, $_SESSION['u']['usuario'], $_SESSION['u']['sub'])) !== null) {
                cerrar_sesion($m);   // se agotaron los ciclos (o hubo inactividad): hay que iniciar sesión de nuevo
            }
            $n = Oidc::renovar($_SESSION['tok']['refresh']);
            try {
                $access = $n ? Tokens::verificar($n['access_token'], 'Bearer') : null;
            } catch (TokenInvalido) {
                $access = null;
            }
            if (!$access) {   // refresh vencido, revocado o reutilizado: se cierra la sesión local
                Db::auditar($_SESSION['u']['usuario'], $_SESSION['u']['sub'], 'REFRESH', 'DENY', 'refresh token inválido o revocado');
                Sesion::destruir();
                json_salida(401, ['error' => 'unauthorized', 'detalle' => 'Tu sesión expiró.']);
            }
            establecer($n, $access, null);
            Db::auditar($_SESSION['u']['usuario'], $_SESSION['u']['sub'], 'REFRESH', 'ALLOW', 'refresh token rotado');
            Sesion::paso('App → Keycloak: refresh_token (rotación): el anterior queda invalidado ✓', 'ok');
        }
        json_salida(200, [
            'usuario' => $_SESSION['u']['usuario'], 'nombre' => $_SESSION['u']['nombre'], 'roles' => $_SESSION['u']['roles'],
            'grupos' => $_SESSION['u']['grupos'], 'scopes' => $_SESSION['u']['scopes'],
            'access_token' => $_SESSION['tok']['access'], 'exp' => $_SESSION['tok']['exp'], 'csrf' => $_SESSION['csrf'],
        ]);

    case '/auth/actividad':   // el navegador avisa que hubo actividad real (clics, teclas); también devuelve los tiempos
        if ($metodo !== 'POST') {
            json_salida(405, ['error' => 'method_not_allowed']);
        }
        if (empty($_SESSION['u']) || !hash_equals($_SESSION['csrf'] ?? '', $_SERVER['HTTP_X_CSRF_TOKEN'] ?? '')) {
            json_salida(401, ['error' => 'unauthorized']);
        }
        if (($m = Sesiones::evaluar((string) $_SESSION['sid'], $_SESSION['u']['usuario'], $_SESSION['u']['sub'], true)) !== null) {
            cerrar_sesion($m);
        }
        json_salida(200, Sesiones::estado((string) $_SESSION['sid']));

    case '/auth/estado':      // consulta de tiempos; NO cuenta como actividad
        if (empty($_SESSION['u'])) {
            json_salida(401, ['error' => 'unauthorized']);
        }
        if (($m = Sesiones::evaluar((string) $_SESSION['sid'], $_SESSION['u']['usuario'], $_SESSION['u']['sub'], false)) !== null) {
            cerrar_sesion($m);
        }
        json_salida(200, Sesiones::estado((string) $_SESSION['sid']));

    case '/auth/logout':
        if ($metodo !== 'POST') {
            json_salida(405, ['error' => 'method_not_allowed']);
        }
        if (empty($_SESSION['u']) || !hash_equals($_SESSION['csrf'] ?? '', $_SERVER['HTTP_X_CSRF_TOKEN'] ?? '')) {
            json_salida(403, ['error' => 'forbidden', 'detalle' => 'Token CSRF inválido.']);
        }
        Sesiones::cerrar((string) ($_SESSION['sid'] ?? ''), 'logout');
        $revocado = Oidc::revocar($_SESSION['tok']['refresh']);   // revoca la sesión en el IdP
        Db::auditar($_SESSION['u']['usuario'], $_SESSION['u']['sub'], 'LOGOUT', 'ALLOW', $revocado ? 'sesión revocada en Keycloak y en la app' : 'sesión local cerrada (el IdP no confirmó)');
        $destino = Oidc::urlCierreSesion($_SESSION['tok']['id']);
        Sesion::destruir();
        json_salida(200, ['redirect' => $destino]);

    default:
        http_response_code(404);
        header('Content-Type: text/plain; charset=utf-8');
        echo 'No encontrado';
}
