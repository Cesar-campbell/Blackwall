<?php
declare(strict_types=1);

namespace Blackwall;

/**
 * Vida de cada sesión, controlada por el SERVIDOR (no por el navegador) y definida POR ROL:
 *  - ciclos: cada renovación del acceso es un ciclo; al agotar el máximo del rol hay que volver a iniciar sesión (con MFA);
 *  - inactividad: si pasa más tiempo sin actividad real que el límite del rol, la sesión se cierra;
 *  - cierre inmediato: una sesión cerrada deja de servir aunque su token no haya vencido (la API lo consulta en cada petición).
 */
final class Sesiones
{
    public const ROLES = ['ROL_ADMIN', 'ROL_ANALISTA', 'ROL_AUDITOR', 'ROL_USUARIO', 'ROL_INVITADO'];
    private const GENERAL = ['maxCiclos' => 12, 'inactividadSeg' => 600, 'avisoSeg' => 30];
    /** Valores iniciales por rol: quien tiene más poder, menos tiempo de inactividad. */
    private const INICIAL = [
        'ROL_ADMIN' => ['maxCiclos' => 6, 'inactividadSeg' => 300, 'avisoSeg' => 30],
        'ROL_AUDITOR' => ['maxCiclos' => 12, 'inactividadSeg' => 600, 'avisoSeg' => 30],
        'ROL_ANALISTA' => ['maxCiclos' => 12, 'inactividadSeg' => 900, 'avisoSeg' => 30],
        'ROL_USUARIO' => ['maxCiclos' => 12, 'inactividadSeg' => 1200, 'avisoSeg' => 30],
        'ROL_INVITADO' => ['maxCiclos' => 12, 'inactividadSeg' => 1800, 'avisoSeg' => 30],
    ];

    /** @return array<string,array{maxCiclos:int,inactividadSeg:int,avisoSeg:int}> política de cada rol */
    public static function todos(): array
    {
        $r = self::INICIAL;
        foreach (Db::pdo()->query('SELECT clave, valor FROM ajustes')->fetchAll() as $f) {
            [$k, $rol] = array_pad(explode('|', $f['clave'], 2), 2, '');
            if (isset($r[$rol][$k])) {
                $r[$rol][$k] = (int) $f['valor'];
            }
        }
        return $r;
    }

    /** @return array{maxCiclos:int,inactividadSeg:int,avisoSeg:int} */
    public static function ajustes(string $rol): array
    {
        return self::todos()[$rol] ?? self::GENERAL;
    }

    /** @param array<string,array<string,int>> $porRol */
    public static function guardar(array $porRol): void
    {
        $q = Db::pdo()->prepare('INSERT INTO ajustes(clave,valor) VALUES(?,?) ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor');
        foreach (self::ROLES as $rol) {
            foreach (['maxCiclos', 'inactividadSeg', 'avisoSeg'] as $k) {
                $q->execute(["$k|$rol", (string) (int) $porRol[$rol][$k]]);
            }
        }
    }

    private static function fila(string $sid): ?array
    {
        $q = Db::pdo()->prepare('SELECT * FROM sesiones WHERE sid=?');
        $q->execute([$sid]);
        return $q->fetch() ?: null;
    }

    public static function registrar(string $sid, string $usuario, string $rol): void
    {
        $ahora = time();
        Db::pdo()->prepare('INSERT OR REPLACE INTO sesiones(sid,usuario,rol,inicio,actividad,ciclos,cerrada) VALUES(?,?,?,?,?,0,NULL)')
            ->execute([$sid, $usuario, $rol, $ahora, $ahora]);
    }

    public static function cerrar(string $sid, string $motivo, string $usuario = '?', ?string $sub = null): void
    {
        $q = Db::pdo()->prepare('UPDATE sesiones SET cerrada=? WHERE sid=? AND cerrada IS NULL');
        $q->execute([$motivo, $sid]);
        if ($q->rowCount() > 0 && $motivo !== 'logout') {
            Db::auditar($usuario, $sub, 'SESION_EXPIRADA', 'DENY', $motivo === 'inactividad' ? 'cerrada por inactividad' : 'cerrada: se agotó el máximo de ciclos');
        }
    }

    /**
     * Comprueba una sesión. Devuelve el motivo del cierre ('inactividad', 'ciclos', 'logout') o null si sigue activa.
     * Si la sesión no existía (token obtenido sin pasar por la app), se registra al verla por primera vez.
     */
    public static function evaluar(string $sid, string $usuario, ?string $sub, bool $cuentaActividad, string $rol = ''): ?string
    {
        $f = self::fila($sid);
        if ($f === null) {
            self::registrar($sid, $usuario, $rol);
            return null;
        }
        if ($f['cerrada'] !== null) {
            return (string) $f['cerrada'];
        }
        if (time() - (int) $f['actividad'] > self::ajustes((string) $f['rol'])['inactividadSeg']) {
            self::cerrar($sid, 'inactividad', $usuario, $sub);
            return 'inactividad';
        }
        if ($cuentaActividad) {
            self::tocar($sid);
        }
        return null;
    }

    public static function tocar(string $sid): void
    {
        Db::pdo()->prepare('UPDATE sesiones SET actividad=? WHERE sid=? AND cerrada IS NULL')->execute([time(), $sid]);
    }

    /** Una renovación del acceso = un ciclo. Devuelve el motivo si ya no se puede renovar. */
    public static function renovar(string $sid, string $usuario, ?string $sub): ?string
    {
        $motivo = self::evaluar($sid, $usuario, $sub, false);
        if ($motivo !== null) {
            return $motivo;
        }
        $f = self::fila($sid);
        if ((int) $f['ciclos'] + 1 > self::ajustes((string) $f['rol'])['maxCiclos']) {
            self::cerrar($sid, 'ciclos', $usuario, $sub);
            return 'ciclos';
        }
        Db::pdo()->prepare('UPDATE sesiones SET ciclos=ciclos+1 WHERE sid=?')->execute([$sid]);
        return null;
    }

    /** Datos para los avisos de la interfaz. */
    public static function estado(string $sid): array
    {
        $f = self::fila($sid);
        $a = self::ajustes($f ? (string) $f['rol'] : '');
        $inactivo = $f ? time() - (int) $f['actividad'] : 0;
        return ['inactivoSeg' => $inactivo, 'limiteSeg' => $a['inactividadSeg'], 'avisoSeg' => $a['avisoSeg'],
            'restanteSeg' => max(0, $a['inactividadSeg'] - $inactivo), 'ciclos' => $f ? (int) $f['ciclos'] : 0, 'maxCiclos' => $a['maxCiclos']];
    }
}
