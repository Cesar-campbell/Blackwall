<?php
declare(strict_types=1);

namespace Blackwall;

/** Configuración: todo sale de variables de entorno (los secretos nunca están en el código). */
final class Config
{
    public static function get(string $clave, ?string $porDefecto = null): string
    {
        $v = getenv($clave);
        if ($v === false || $v === '') {
            if ($porDefecto !== null) {
                return $porDefecto;
            }
            throw new \RuntimeException("Falta la variable de entorno $clave");
        }
        return $v;
    }

    public static function datos(): string
    {
        return '/var/www/datos';
    }
}
