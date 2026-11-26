<?php
declare(strict_types=1);

namespace Blackwall;

/** OpenID Connect: Authorization Code + PKCE (S256) contra Keycloak. Sin Implicit ni ROPC. */
final class Oidc
{
    public static function b64u(string $b): string
    {
        return rtrim(strtr(base64_encode($b), '+/', '-_'), '=');
    }

    /**
     * Con una dirección pública, las llamadas del servidor a Keycloak (token, claves, cierre de sesión) se hacen por la red
     * interna de Docker en vez de salir a internet y volver. Solo se reescribe el prefijo; el navegador sigue usando la pública.
     */
    public static function interno(string $url): string
    {
        $base = getenv('OIDC_INTERNAL_ISSUER');
        $emisor = Config::get('OIDC_ISSUER');
        return ($base !== false && $base !== '' && str_starts_with($url, $emisor)) ? $base . substr($url, strlen($emisor)) : $url;
    }

    /** Documento de descubrimiento (con caché de una hora). */
    public static function descubrir(): array
    {
        $archivo = Config::datos() . '/discovery.json';
        if (is_file($archivo) && time() - filemtime($archivo) < 3600) {
            $d = json_decode((string) file_get_contents($archivo), true);
            if (is_array($d)) {
                return $d;
            }
        }
        [$st, $d] = Http::json('GET', self::interno(Config::get('OIDC_ISSUER')) . '/.well-known/openid-configuration');
        if ($st !== 200 || ($d['issuer'] ?? '') !== Config::get('OIDC_ISSUER')) {
            throw new \RuntimeException('Descubrimiento OIDC inválido');
        }
        file_put_contents($archivo, json_encode($d), LOCK_EX);
        return $d;
    }

    public static function redirectUri(): string
    {
        return Config::get('APP_URL') . '/callback';
    }

    /** Paso 1: redirige al usuario a Keycloak con code_challenge, state y nonce. */
    public static function urlLogin(?string $accion = null): string
    {
        $verifier = self::b64u(random_bytes(48));
        $state = self::b64u(random_bytes(16));
        $nonce = self::b64u(random_bytes(16));
        $_SESSION['oidc'] = ['verifier' => $verifier, 'state' => $state, 'nonce' => $nonce, 't' => time()];
        $q = [
            'client_id' => Config::get('OIDC_CLIENT_ID'),
            'redirect_uri' => self::redirectUri(),
            'response_type' => 'code',
            'scope' => 'openid profile',
            'state' => $state,
            'nonce' => $nonce,
            'code_challenge' => self::b64u(hash('sha256', $verifier, true)),
            'code_challenge_method' => 'S256',
        ];
        if ($accion !== null) {
            $q['kc_action'] = $accion;   // p. ej. UPDATE_PASSWORD
        }
        Sesion::paso('App → Keycloak: GET /auth?response_type=code&code_challenge=' . substr($q['code_challenge'], 0, 12)
            . '…&code_challenge_method=S256&state=' . substr($state, 0, 6) . '…&nonce=' . substr($nonce, 0, 6) . '…', 'ok');
        return self::descubrir()['authorization_endpoint'] . '?' . http_build_query($q);
    }

    /** Paso 2: intercambia el código por tokens enviando el code_verifier. */
    public static function intercambiar(string $code): array
    {
        $o = $_SESSION['oidc'] ?? null;
        unset($_SESSION['oidc']);
        [$st, $t] = Http::json('POST', self::interno(self::descubrir()['token_endpoint']), [
            'grant_type' => 'authorization_code',
            'code' => $code,
            'redirect_uri' => self::redirectUri(),
            'client_id' => Config::get('OIDC_CLIENT_ID'),
            'client_secret' => Config::get('OIDC_CLIENT_SECRET'),
            'code_verifier' => $o['verifier'] ?? '',
        ]);
        if ($st !== 200) {
            throw new \RuntimeException('Keycloak rechazó el intercambio del código: ' . ($t['error_description'] ?? $t['error'] ?? $st));
        }
        return $t;
    }

    /** Refresh token con rotación: el refresh viejo queda inválido y se devuelve uno nuevo. */
    public static function renovar(string $refresh): ?array
    {
        [$st, $t] = Http::json('POST', self::interno(self::descubrir()['token_endpoint']), [
            'grant_type' => 'refresh_token',
            'refresh_token' => $refresh,
            'client_id' => Config::get('OIDC_CLIENT_ID'),
            'client_secret' => Config::get('OIDC_CLIENT_SECRET'),
        ]);
        return $st === 200 ? $t : null;
    }

    /** Revoca la sesión en el IdP (back-channel): el refresh token deja de servir. */
    public static function revocar(string $refresh): bool
    {
        [$st] = Http::pedir('POST', self::interno(self::descubrir()['end_session_endpoint']), [
            'client_id' => Config::get('OIDC_CLIENT_ID'),
            'client_secret' => Config::get('OIDC_CLIENT_SECRET'),
            'refresh_token' => $refresh,
        ]);
        return $st === 204 || $st === 200;
    }

    public static function urlCierreSesion(string $idToken): string
    {
        return self::descubrir()['end_session_endpoint'] . '?' . http_build_query([
            'id_token_hint' => $idToken,
            'post_logout_redirect_uri' => Config::get('APP_URL') . '/',
            'client_id' => Config::get('OIDC_CLIENT_ID'),
        ]);
    }
}
