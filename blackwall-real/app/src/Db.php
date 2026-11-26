<?php
declare(strict_types=1);

namespace Blackwall;

/** SQLite: casos, comentarios y auditoría. Todas las consultas son preparadas (sin concatenar entradas). */
final class Db
{
    private static ?\PDO $pdo = null;

    public static function pdo(): \PDO
    {
        if (self::$pdo === null) {
            $nuevo = !is_file(Config::datos() . '/blackwall.db');
            $p = new \PDO('sqlite:' . Config::datos() . '/blackwall.db', null, null, [
                \PDO::ATTR_ERRMODE => \PDO::ERRMODE_EXCEPTION,
                \PDO::ATTR_DEFAULT_FETCH_MODE => \PDO::FETCH_ASSOC,
            ]);
            $p->exec('PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON; PRAGMA busy_timeout=3000');
            $p->exec("CREATE TABLE IF NOT EXISTS casos(
                n INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT NOT NULL, descripcion TEXT NOT NULL DEFAULT '',
                severidad TEXT NOT NULL, estado TEXT NOT NULL DEFAULT 'abierto',
                propietario TEXT NOT NULL, propietario_sub TEXT, creado TEXT NOT NULL, actualizado TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS comentarios(
                id INTEGER PRIMARY KEY AUTOINCREMENT, caso_n INTEGER NOT NULL REFERENCES casos(n) ON DELETE CASCADE,
                autor TEXT NOT NULL, autor_sub TEXT, texto TEXT NOT NULL, creado TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS auditoria(
                id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, usuario TEXT NOT NULL, sub TEXT,
                evento TEXT NOT NULL, resultado TEXT NOT NULL, detalle TEXT NOT NULL DEFAULT '', ip TEXT);");
            if ($nuevo) {
                self::sembrar($p);
            }
            self::$pdo = $p;
        }
        return self::$pdo;
    }

    /** Casos de ejemplo. El dueño se identifica por usuario; el `sub` se completa en su primer acceso. */
    private static function sembrar(\PDO $p): void
    {
        $ahora = gmdate('c');
        $q = $p->prepare('INSERT INTO casos(titulo,descripcion,severidad,estado,propietario,creado,actualizado) VALUES(?,?,?,?,?,?,?)');
        foreach ([
            ['Correo de phishing a docentes', 'Varios docentes recibieron un enlace falso de "actualizar contraseña".', 'alta', 'abierto', 'ejemplo.usuario'],
            ['Laptop extraviada en laboratorio', 'Equipo del lab 2 no aparece desde el viernes.', 'media', 'en_analisis', 'ejemplo.usuario2'],
            ['Acceso no autorizado al servidor de notas', 'Inicios de sesión desde una IP externa a las 3:12 a. m.', 'critica', 'en_analisis', 'cruz.irvin'],
            ['Malware detectado en sala 3', 'El antivirus aisló un ejecutable sospechoso.', 'alta', 'resuelto', 'ejemplo.usuario'],
            ['Fuerza bruta contra el portal', 'Más de 400 intentos fallidos en 10 minutos.', 'media', 'abierto', 'ejemplo.usuario2'],
            ['USB sospechosa encontrada', 'Hallada en el pasillo del edificio 1.', 'baja', 'resuelto', 'ejemplo.usuario'],
        ] as $c) {
            $q->execute([...$c, $ahora, $ahora]);
        }
        $p->prepare('INSERT INTO comentarios(caso_n,autor,texto,creado) VALUES(1,?,?,?)')->execute(['cruz.irvin', 'Se bloqueó el dominio del enlace.', $ahora]);
        $p->prepare('INSERT INTO comentarios(caso_n,autor,texto,creado) VALUES(3,?,?,?)')->execute(['cruz.irvin', 'Se rotaron las credenciales del servicio.', $ahora]);
    }

    public static function idCaso(int $n): string
    {
        return 'INC-' . str_pad((string) $n, 3, '0', STR_PAD_LEFT);
    }

    /** Convierte "INC-007" en 7 (o null si el formato no es válido). */
    public static function numCaso(string $id): ?int
    {
        return preg_match('/^INC-(\d{1,9})$/', $id, $m) ? (int) $m[1] : null;
    }

    /** IP del visitante: detrás del proxy de la dirección pública se toma de la cabecera que él pone (solo si CONFIANZA_PROXY=1). */
    public static function ip(): ?string
    {
        if (getenv('CONFIANZA_PROXY') === '1') {
            foreach (['HTTP_CF_CONNECTING_IP', 'HTTP_X_FORWARDED_FOR'] as $h) {
                if (!empty($_SERVER[$h])) {
                    $ip = trim(explode(',', (string) $_SERVER[$h])[0]);
                    if (filter_var($ip, FILTER_VALIDATE_IP)) {
                        return $ip;
                    }
                }
            }
        }
        return $_SERVER['REMOTE_ADDR'] ?? null;
    }

    public static function auditar(string $usuario, ?string $sub, string $evento, string $resultado, string $detalle = ''): void
    {
        try {
            self::pdo()->prepare('INSERT INTO auditoria(ts,usuario,sub,evento,resultado,detalle,ip) VALUES(?,?,?,?,?,?,?)')
                ->execute([gmdate('c'), $usuario, $sub, $evento, $resultado, mb_substr($detalle, 0, 300), self::ip()]);
        } catch (\Throwable $e) {
            error_log('auditoria: ' . $e->getMessage());
        }
    }
}
