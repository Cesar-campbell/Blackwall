<?php
declare(strict_types=1);

namespace Blackwall;

/** Sesión del navegador (cookie de sesión), separada de los tokens, que se guardan solo en el servidor. */
final class Sesion
{
    public static function iniciar(): void
    {
        session_name('__Host-bw');                 // prefijo __Host-: solo HTTPS, sin Domain, Path=/
        session_set_cookie_params([
            'lifetime' => 0, 'path' => '/', 'secure' => true, 'httponly' => true, 'samesite' => 'Lax',
        ]);
        ini_set('session.use_strict_mode', '1');
        ini_set('session.use_only_cookies', '1');
        session_start();
    }

    /** Registra un paso del flujo de autenticación para mostrarlo en "qué pasa por detrás". */
    public static function paso(string $msg, string $tipo = ''): void
    {
        $_SESSION['flujo'][] = ['msg' => $msg, 'k' => $tipo];
        $_SESSION['flujo'] = array_slice($_SESSION['flujo'], -30);
    }

    public static function destruir(): void
    {
        $_SESSION = [];
        if (ini_get('session.use_cookies')) {
            setcookie(session_name(), '', ['expires' => time() - 3600, 'path' => '/', 'secure' => true, 'httponly' => true, 'samesite' => 'Lax']);
        }
        session_destroy();
    }
}
