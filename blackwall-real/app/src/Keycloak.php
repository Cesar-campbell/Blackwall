<?php
declare(strict_types=1);

namespace Blackwall;

/**
 * API de administración de Keycloak con la cuenta de servicio cli-blackwall-sync-dev
 * (client credentials, solo los roles necesarios). Se usa para: eventos de auditoría, estado de MFA/bloqueo
 * y parámetros de seguridad del realm.
 */
final class Keycloak
{
    private static function token(): string
    {
        $archivo = Config::datos() . '/svc-token.json';
        if (is_file($archivo)) {
            $t = json_decode((string) file_get_contents($archivo), true);
            if (is_array($t) && ($t['exp'] ?? 0) > time() + 15) {
                return $t['token'];
            }
        }
        [$st, $r] = Http::json('POST', Config::get('KC_URL') . '/realms/' . Config::get('KC_REALM') . '/protocol/openid-connect/token', [
            'grant_type' => 'client_credentials',
            'client_id' => Config::get('SYNC_CLIENT_ID'),
            'client_secret' => Config::get('SYNC_CLIENT_SECRET'),
        ]);
        if ($st !== 200) {
            throw new \RuntimeException('No se pudo autenticar la cuenta de servicio en Keycloak');
        }
        file_put_contents($archivo, json_encode(['token' => $r['access_token'], 'exp' => time() + (int) $r['expires_in']]), LOCK_EX);
        chmod($archivo, 0600);
        return $r['access_token'];
    }

    public static function admin(string $metodo, string $ruta, ?array $cuerpo = null): array
    {
        $url = Config::get('KC_URL') . '/admin/realms/' . Config::get('KC_REALM') . $ruta;
        return Http::json($metodo, $url, $cuerpo !== null ? json_encode($cuerpo) : null, [
            'Authorization: Bearer ' . self::token(), 'Content-Type: application/json',
        ]);
    }

    /** Id interno de Keycloak de un usuario (la búsqueda importa al usuario desde el directorio si aún no estaba). */
    public static function idDe(string $username): ?string
    {
        [$st, $l] = self::admin('GET', '/users?exact=true&username=' . rawurlencode($username));
        return ($st === 200 && !empty($l[0]['id'])) ? $l[0]['id'] : null;
    }

    /**
     * Id, estado de MFA y de bloqueo de un usuario, con caché corta (30 s): la pantalla de Usuarios preguntaba 3 veces
     * por persona a Keycloak en cada visita. La caché se borra cuando el administrador cambia algo.
     */
    public static function estadoUsuario(string $username): array
    {
        $archivo = Config::datos() . '/estado-usuarios.json';
        $cache = is_file($archivo) ? (json_decode((string) file_get_contents($archivo), true) ?: []) : [];
        $e = $cache[$username] ?? null;
        if ($e !== null && time() - $e['t'] < 30) {
            return $e;
        }
        $id = self::idDe($username);
        $e = ['id' => $id, 'mfa' => $id ? self::tieneOtp($id) : false, 'bloqueado' => $id ? self::bloqueado($id) : false, 't' => time()];
        $cache[$username] = $e;
        file_put_contents($archivo, json_encode($cache), LOCK_EX);
        return $e;
    }

    public static function olvidarEstados(): void
    {
        @unlink(Config::datos() . '/estado-usuarios.json');
    }

    public static function tieneOtp(string $id): bool
    {
        [$st, $c] = self::admin('GET', "/users/$id/credentials");
        foreach ($st === 200 ? $c : [] as $x) {
            if (($x['type'] ?? '') === 'otp') {
                return true;
            }
        }
        return false;
    }

    public static function bloqueado(string $id): bool
    {
        [$st, $r] = self::admin('GET', "/attack-detection/brute-force/users/$id");
        return $st === 200 && !empty($r['disabled']);
    }

    public static function desbloquear(string $id): void
    {
        self::admin('DELETE', "/attack-detection/brute-force/users/$id");
    }

    public static function borrarUsuario(string $id): void
    {
        self::admin('DELETE', "/users/$id");
    }

    /** Eventos del realm (inicios de sesión, fallos, bloqueos) traducidos al formato de la auditoría. */
    public static function eventos(int $max = 150): array
    {
        [$st, $ev] = self::admin('GET', '/events?max=' . $max);
        $salida = [];
        foreach ($st === 200 ? $ev : [] as $e) {
            $tipo = $e['type'] ?? '';
            $error = $e['error'] ?? '';
            $usuario = $e['details']['username'] ?? ($e['userId'] ?? '?');
            [$evento, $res] = match (true) {
                $tipo === 'LOGIN' => ['LOGIN', 'ALLOW'],
                $tipo === 'LOGIN_ERROR' && str_contains($error, 'temporarily_disabled') => ['LOCKOUT', 'DENY'],
                $tipo === 'LOGIN_ERROR' => ['LOGIN', 'DENY'],
                $tipo === 'USER_DISABLED_BY_TEMPORARY_LOCKOUT' => ['LOCKOUT', 'DENY'],
                $tipo === 'LOGOUT' => ['LOGOUT', 'ALLOW'],
                $tipo === 'REFRESH_TOKEN_ERROR' || $tipo === 'CODE_TO_TOKEN_ERROR' => [$tipo, 'DENY'],
                $tipo === 'UPDATE_PASSWORD' => ['PWD_CHANGE', 'ALLOW'],
                $tipo === 'UPDATE_PASSWORD_ERROR' => ['PWD_CHANGE', 'DENY'],
                $tipo === 'UPDATE_TOTP' => ['TOTP_ENROLL', 'ALLOW'],
                default => [$tipo, str_ends_with($tipo, 'ERROR') ? 'DENY' : 'ALLOW'],
            };
            if (in_array($tipo, ['REFRESH_TOKEN', 'CODE_TO_TOKEN'], true)) {
                continue;
            }
            $salida[] = [
                't' => gmdate('c', intdiv((int) $e['time'], 1000)), 'u' => $usuario, 'ev' => $evento, 'res' => $res,
                'det' => ($error !== '' ? $error : $tipo) . ' · IP ' . ($e['ipAddress'] ?? '?'), 'src' => 'keycloak',
            ];
        }
        return $salida;
    }

    public static function realm(): array
    {
        return self::admin('GET', '')[1];
    }

    public static function actualizarRealm(array $cambios): bool
    {
        // Solo los campos que cambian: reenviar todo el realm rompe los objetos vacíos ({} pasaría a [])
        [$st] = self::admin('PUT', '', $cambios);
        return $st === 204;
    }
}
