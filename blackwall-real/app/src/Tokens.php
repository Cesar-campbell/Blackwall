<?php
declare(strict_types=1);

namespace Blackwall;

use Firebase\JWT\JWK;
use Firebase\JWT\JWT;

final class TokenInvalido extends \RuntimeException
{
}

/**
 * Validación de tokens emitidos por Keycloak (guía 7.1 y 7.2):
 * firma RS256 con las claves públicas del IdP (JWKS), iss, aud, exp (y nonce para el ID token).
 */
final class Tokens
{
    private const TTL_JWKS = 600;

    /** Claves públicas del IdP, con caché en disco y recarga cuando aparece un kid desconocido. */
    private static function claves(bool $forzar = false): array
    {
        $archivo = Config::datos() . '/jwks.json';
        if (!$forzar && is_file($archivo) && time() - filemtime($archivo) < self::TTL_JWKS) {
            $j = json_decode((string) file_get_contents($archivo), true);
            if (is_array($j) && isset($j['keys'])) {
                return $j;
            }
        }
        $uri = Oidc::interno(Oidc::descubrir()['jwks_uri']);
        [$st, $j] = Http::json('GET', $uri);
        if ($st !== 200 || !isset($j['keys'])) {
            throw new \RuntimeException('No se pudo obtener el JWKS del proveedor de identidad');
        }
        file_put_contents($archivo, json_encode($j), LOCK_EX);
        return $j;
    }

    /**
     * @param string $tipo 'Bearer' (access token) o 'ID' (ID token)
     * @return array<string,mixed> claims validados
     */
    public static function verificar(string $jwt, string $tipo, ?string $nonce = null): array
    {
        $partes = explode('.', $jwt);
        if (count($partes) !== 3) {
            throw new TokenInvalido('token malformado');
        }
        $cabecera = json_decode((string) base64_decode(strtr($partes[0], '-_', '+/')), true);
        if (!is_array($cabecera) || ($cabecera['alg'] ?? '') !== 'RS256' || empty($cabecera['kid'])) {
            throw new TokenInvalido('algoritmo no permitido');   // rechaza "none", HS256, etc.
        }

        JWT::$leeway = 5;
        try {
            $claims = (array) JWT::decode($jwt, JWK::parseKeySet(self::claves(), 'RS256'));
        } catch (\UnexpectedValueException $e) {
            // kid desconocido: puede haber rotación de claves, se reintenta una vez con JWKS fresco
            if (!str_contains($e->getMessage(), '"kid"')) {
                throw new TokenInvalido(self::motivo($e));
            }
            try {
                $claims = (array) JWT::decode($jwt, JWK::parseKeySet(self::claves(true), 'RS256'));
            } catch (\Throwable $e2) {
                throw new TokenInvalido(self::motivo($e2));
            }
        } catch (\Throwable $e) {
            throw new TokenInvalido(self::motivo($e));
        }

        if (($claims['iss'] ?? '') !== Config::get('OIDC_ISSUER')) {
            throw new TokenInvalido('iss incorrecto');
        }
        $aud = (array) ($claims['aud'] ?? []);
        if (!in_array(Config::get('OIDC_CLIENT_ID'), $aud, true)) {
            throw new TokenInvalido('aud incorrecto');
        }
        if (($claims['typ'] ?? '') !== $tipo) {
            throw new TokenInvalido("se esperaba un token de tipo $tipo");
        }
        if ($nonce !== null && !hash_equals($nonce, (string) ($claims['nonce'] ?? ''))) {
            throw new TokenInvalido('nonce no coincide');
        }
        return $claims;
    }

    private static function motivo(\Throwable $e): string
    {
        $m = $e->getMessage();
        return match (true) {
            str_contains($m, 'Expired') => 'token expirado',
            str_contains($m, 'Signature verification failed') => 'firma inválida',
            str_contains($m, 'before') => 'token aún no válido',
            default => 'token inválido',
        };
    }
}
