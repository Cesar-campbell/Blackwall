<?php
declare(strict_types=1);

namespace Blackwall;

/** Identidad del llamador, tomada SOLO de un access token validado (nunca de lo que diga la interfaz). */
final class Principal
{
    /** @param list<string> $roles @param list<string> $scopes */
    public function __construct(
        public readonly string $sub,
        public readonly string $usuario,
        public readonly array $roles,
        public readonly array $scopes,
        public readonly string $sid = '',
    ) {
    }

    public function tiene(string $scope): bool
    {
        return in_array($scope, $this->scopes, true);
    }
}

/**
 * API protegida. Cada petición: 1) valida el access token (firma JWKS, iss, aud, exp);
 * 2) comprueba el scope exigido por ese endpoint (denegar por defecto); 3) aplica control por propiedad.
 */
final class Api
{
    private const SEV = ['baja', 'media', 'alta', 'critica'];
    private const EST = ['abierto', 'en_analisis', 'resuelto'];
    private Principal $p;
    private string $metodo;
    private string $ruta;
    private array $cuerpo = [];

    public static function atender(string $metodo, string $ruta): never
    {
        (new self())->ejecutar($metodo, $ruta);
    }

    private function ejecutar(string $metodo, string $ruta): never
    {
        $this->metodo = $metodo;
        $this->ruta = $ruta;
        try {
            $this->p = $this->autenticar();
            if (in_array($metodo, ['POST', 'PUT'], true)) {
                $raw = file_get_contents('php://input', false, null, 0, 65536) ?: '';
                $j = $raw === '' ? [] : json_decode($raw, true);
                if (!is_array($j)) {
                    $this->responder(400, ['error' => 'bad_request', 'detalle' => 'El cuerpo debe ser JSON válido.']);
                }
                $this->cuerpo = $j;
            }
            Db::pdo()->prepare('UPDATE casos SET propietario_sub=? WHERE propietario=? AND propietario_sub IS NULL')
                ->execute([$this->p->sub, $this->p->usuario]);
            $this->enrutar();
        } catch (ErrorNegocio $e) {
            $this->responder($e->http, ['error' => $e->http === 404 ? 'not_found' : 'bad_request', 'detalle' => $e->getMessage()]);
        } catch (\Throwable $e) {
            error_log('API: ' . $e);
            $this->responder(500, ['error' => 'server_error', 'detalle' => 'Error interno del servidor.']);
        }
    }

    private function responder(int $st, mixed $cuerpo): never
    {
        http_response_code($st);
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode($cuerpo, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT);
        exit;
    }

    private function autenticar(): Principal
    {
        $h = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
        if (!preg_match('/^Bearer\s+([A-Za-z0-9\-_\.]+)$/', $h, $m)) {
            Db::auditar('?', null, "{$this->metodo} {$this->ruta}", 'DENY', '401 token ausente');
            header('WWW-Authenticate: Bearer realm="blackwall"');
            $this->responder(401, ['error' => 'unauthorized', 'detalle' => 'Falta el token de acceso.']);
        }
        try {
            $c = Tokens::verificar($m[1], 'Bearer');
        } catch (TokenInvalido $e) {
            Db::auditar('?', null, "{$this->metodo} {$this->ruta}", 'DENY', '401 ' . $e->getMessage());
            header('WWW-Authenticate: Bearer realm="blackwall", error="invalid_token"');
            $this->responder(401, ['error' => 'unauthorized', 'detalle' => $e->getMessage()]);
        }
        $roles = array_values(array_filter((array) ($c['roles'] ?? []), fn($r) => is_string($r) && str_starts_with($r, 'ROL_')));
        $scopes = array_values(array_filter(explode(' ', (string) ($c['scope'] ?? ''))));
        $p = new Principal((string) $c['sub'], (string) ($c['preferred_username'] ?? '?'), $roles, $scopes, (string) ($c['sid'] ?? ''));
        if ($p->sid !== '') {
            // Las consultas automáticas de la interfaz (X-Auto: 1) no cuentan como actividad del usuario
            $motivo = Sesiones::evaluar($p->sid, $p->usuario, $p->sub, ($_SERVER['HTTP_X_AUTO'] ?? '') !== '1', $p->roles[0] ?? '');
            if ($motivo !== null) {
                Db::auditar($p->usuario, $p->sub, "{$this->metodo} {$this->ruta}", 'DENY', "401 sesión cerrada ($motivo)");
                header('WWW-Authenticate: Bearer realm="blackwall", error="invalid_token"');
                $this->responder(401, ['error' => 'unauthorized', 'motivo' => $motivo, 'detalle' => match ($motivo) {
                    'inactividad' => 'Tu sesión se cerró por inactividad.',
                    'ciclos' => 'Alcanzaste el tiempo máximo de sesión.',
                    default => 'La sesión ya fue cerrada.',
                }]);
            }
        }
        return $p;
    }

    // ------------------------------------------------------------------ utilidades de respuesta / permisos
    private function denegar(string $porque): never
    {
        Db::auditar($this->p->usuario, $this->p->sub, "{$this->metodo} {$this->ruta}", 'DENY', "403 $porque");
        $this->responder(403, ['error' => 'forbidden', 'detalle' => $porque]);
    }

    private function exigir(string ...$alguno): void
    {
        foreach ($alguno as $s) {
            if ($this->p->tiene($s)) {
                return;
            }
        }
        $this->denegar('requiere ' . implode(' o ', $alguno));
    }

    private function ok(mixed $cuerpo, int $st = 200, bool $auditar = false): never
    {
        if ($auditar) {
            Db::auditar($this->p->usuario, $this->p->sub, "{$this->metodo} {$this->ruta}", 'ALLOW', (string) $st);
        }
        $this->responder($st, $cuerpo);
    }

    private function noEncontrado(): never
    {
        $this->responder(404, ['error' => 'not_found', 'detalle' => 'No encontrado']);
    }

    private function malo(string $d): never
    {
        $this->responder(400, ['error' => 'bad_request', 'detalle' => $d]);
    }

    // ------------------------------------------------------------------ enrutador (todo lo no listado = 404)
    private function enrutar(): void
    {
        $m = $this->metodo;
        $r = $this->ruta;
        $n = null;
        if ($r === '/api/yo' && $m === 'GET') {
            $this->ok(['sub' => $this->p->sub, 'usuario' => $this->p->usuario, 'roles' => $this->p->roles, 'scopes' => $this->p->scopes]);
        }
        if ($r === '/api/casos') {
            $m === 'GET' && $this->listarCasos();
            $m === 'POST' && $this->crearCaso();
        }
        if (preg_match('#^/api/casos/([A-Za-z0-9-]+)$#', $r, $x)) {
            $m === 'GET' && $this->verCaso($x[1]);
            $m === 'PUT' && $this->editarCaso($x[1]);
            $m === 'DELETE' && $this->borrarCaso($x[1]);
        }
        if (preg_match('#^/api/casos/([A-Za-z0-9-]+)/comentarios(?:/(\d+))?$#', $r, $x)) {
            $m === 'POST' && !isset($x[2]) && $this->comentar($x[1]);
            $m === 'PUT' && isset($x[2]) && $this->editarComentario($x[1], (int) $x[2]);
            $m === 'DELETE' && isset($x[2]) && $this->borrarComentario($x[1], (int) $x[2]);
        }
        if ($r === '/api/estadisticas' && $m === 'GET') {
            $this->estadisticas();
        }
        if ($r === '/api/usuarios') {
            $m === 'GET' && $this->listarUsuarios();
            $m === 'POST' && $this->crearUsuario();
        }
        if (preg_match('#^/api/usuarios/([a-z0-9.\-]+)(/desbloquear)?$#', $r, $x)) {
            isset($x[2]) && $m === 'POST' && $this->desbloquearUsuario($x[1]);
            !isset($x[2]) && $m === 'PUT' && $this->editarUsuario($x[1]);
            !isset($x[2]) && $m === 'DELETE' && $this->borrarUsuario($x[1]);
        }
        if ($r === '/api/auditoria' && $m === 'GET') {
            $this->auditoria();
        }
        if ($r === '/api/config') {
            $m === 'GET' && $this->verConfig();
            $m === 'PUT' && $this->guardarConfig();
        }
        $this->noEncontrado();
    }

    // ------------------------------------------------------------------ casos
    private function filaCaso(array $f): array
    {
        return ['id' => Db::idCaso((int) $f['n']), 'titulo' => $f['titulo'], 'descripcion' => $f['descripcion'],
            'severidad' => $f['severidad'], 'estado' => $f['estado'], 'propietario' => $f['propietario'], 'creado' => $f['creado']];
    }

    private function buscarCaso(string $id): ?array
    {
        $n = Db::numCaso($id);
        if ($n === null) {
            return null;
        }
        $q = Db::pdo()->prepare('SELECT * FROM casos WHERE n=?');
        $q->execute([$n]);
        return $q->fetch() ?: null;
    }

    private function esMio(array $caso): bool
    {
        return $caso['propietario_sub'] !== null && hash_equals((string) $caso['propietario_sub'], $this->p->sub);
    }

    private function listarCasos(): void
    {
        if ($this->p->tiene('casos:leer')) {
            $f = Db::pdo()->query('SELECT * FROM casos ORDER BY n')->fetchAll();
        } elseif ($this->p->tiene('casos:leer_propios')) {
            $q = Db::pdo()->prepare('SELECT * FROM casos WHERE propietario_sub=? ORDER BY n');
            $q->execute([$this->p->sub]);
            $f = $q->fetchAll();
        } else {
            $this->denegar('requiere casos:leer');
        }
        $this->ok(array_map([$this, 'filaCaso'], $f));
    }

    private function crearCaso(): void
    {
        $this->exigir('casos:escribir', 'casos:crear');
        $t = trim((string) ($this->cuerpo['titulo'] ?? ''));
        if ($t === '' || mb_strlen($t) > 120) {
            $this->malo('El título es obligatorio (máx. 120 caracteres).');
        }
        $d = (string) ($this->cuerpo['descripcion'] ?? '');
        if (mb_strlen($d) > 2000) {
            $this->malo('La descripción es demasiado larga (máx. 2000 caracteres).');
        }
        $sev = in_array($this->cuerpo['severidad'] ?? '', self::SEV, true) ? $this->cuerpo['severidad'] : 'media';
        $ahora = gmdate('c');
        $pdo = Db::pdo();
        $pdo->prepare('INSERT INTO casos(titulo,descripcion,severidad,estado,propietario,propietario_sub,creado,actualizado) VALUES(?,?,?,?,?,?,?,?)')
            ->execute([$t, $d, $sev, 'abierto', $this->p->usuario, $this->p->sub, $ahora, $ahora]);
        $q = $pdo->prepare('SELECT * FROM casos WHERE n=?');
        $q->execute([$pdo->lastInsertId()]);
        $this->ok($this->filaCaso($q->fetch()), 201, true);
    }

    private function verCaso(string $id): void
    {
        $c = $this->buscarCaso($id);
        if ($this->p->tiene('casos:leer')) {
            $c ?? $this->noEncontrado();
        } elseif ($this->p->tiene('casos:leer_propios')) {
            // Control por propiedad: un caso ajeno es indistinguible de uno inexistente (no revela su contenido)
            ($c !== null && $this->esMio($c)) || $this->noEncontrado();
        } else {
            $this->denegar('requiere casos:leer');
        }
        $q = Db::pdo()->prepare('SELECT id,autor AS autor,texto FROM comentarios WHERE caso_n=? ORDER BY id');
        $q->execute([$c['n']]);
        $this->ok($this->filaCaso($c) + ['comentarios' => $q->fetchAll()]);
    }

    private function editarCaso(string $id): void
    {
        $c = $this->buscarCaso($id);
        $b = $this->cuerpo;
        if ($this->p->tiene('casos:escribir')) {
            $c ?? $this->noEncontrado();
            $est = in_array($b['estado'] ?? '', self::EST, true) ? $b['estado'] : $c['estado'];
            $sev = in_array($b['severidad'] ?? '', self::SEV, true) ? $b['severidad'] : $c['severidad'];
            Db::pdo()->prepare('UPDATE casos SET estado=?, severidad=?, actualizado=? WHERE n=?')->execute([$est, $sev, gmdate('c'), $c['n']]);
        } elseif ($this->p->tiene('casos:escribir_propios')) {
            // "U limitado": solo su caso, solo abierto y solo título/descripción
            ($c !== null && $this->esMio($c)) || $this->noEncontrado();
            if ($c['estado'] !== 'abierto') {
                $this->denegar('solo puedes editar casos abiertos');
            }
            if (isset($b['estado']) || isset($b['severidad'])) {
                $this->denegar('no puedes cambiar estado ni severidad');
            }
            $t = trim((string) ($b['titulo'] ?? ''));
            $d = (string) ($b['descripcion'] ?? '');
            if ($t === '' || mb_strlen($t) > 120 || mb_strlen($d) > 2000) {
                $this->malo('Título obligatorio (máx. 120) y descripción de máx. 2000 caracteres.');
            }
            Db::pdo()->prepare('UPDATE casos SET titulo=?, descripcion=?, actualizado=? WHERE n=?')->execute([$t, $d, gmdate('c'), $c['n']]);
        } else {
            $this->denegar('requiere casos:escribir');
        }
        $this->ok($this->filaCaso($this->buscarCaso($id)), 200, true);
    }

    private function borrarCaso(string $id): void
    {
        $this->exigir('casos:borrar');
        $c = $this->buscarCaso($id) ?? $this->noEncontrado();
        Db::pdo()->prepare('DELETE FROM casos WHERE n=?')->execute([$c['n']]);
        $this->ok(['ok' => true], 200, true);
    }

    // ------------------------------------------------------------------ comentarios
    private function comentar(string $id): void
    {
        $c = $this->buscarCaso($id);
        if ($this->p->tiene('comentarios:escribir')) {
            $c ?? $this->noEncontrado();
        } elseif ($this->p->tiene('comentarios:escribir_propios')) {
            ($c !== null && $this->esMio($c)) || $this->noEncontrado();
        } else {
            $this->denegar('requiere comentarios:escribir');
        }
        $x = trim((string) ($this->cuerpo['texto'] ?? ''));
        if ($x === '' || mb_strlen($x) > 1000) {
            $this->malo('El comentario es obligatorio (máx. 1000 caracteres).');
        }
        Db::pdo()->prepare('INSERT INTO comentarios(caso_n,autor,autor_sub,texto,creado) VALUES(?,?,?,?,?)')
            ->execute([$c['n'], $this->p->usuario, $this->p->sub, $x, gmdate('c')]);
        $this->ok(['ok' => true], 201, true);
    }

    private function editarComentario(string $id, int $cid): void
    {
        $this->exigir('comentarios:escribir');
        $c = $this->buscarCaso($id) ?? $this->noEncontrado();
        $x = trim((string) ($this->cuerpo['texto'] ?? ''));
        if ($x === '' || mb_strlen($x) > 1000) {
            $this->malo('El comentario es obligatorio (máx. 1000 caracteres).');
        }
        $q = Db::pdo()->prepare('UPDATE comentarios SET texto=? WHERE id=? AND caso_n=?');
        $q->execute([$x, $cid, $c['n']]);
        $q->rowCount() > 0 || $this->noEncontrado();
        $this->ok(['ok' => true], 200, true);
    }

    private function borrarComentario(string $id, int $cid): void
    {
        $this->exigir('comentarios:borrar');
        $c = $this->buscarCaso($id) ?? $this->noEncontrado();
        $q = Db::pdo()->prepare('DELETE FROM comentarios WHERE id=? AND caso_n=?');
        $q->execute([$cid, $c['n']]);
        $q->rowCount() > 0 || $this->noEncontrado();
        $this->ok(['ok' => true], 200, true);
    }

    // ------------------------------------------------------------------ estadísticas
    private function estadisticas(): void
    {
        $contar = function (?string $sub): array {
            $w = $sub !== null ? ' WHERE propietario_sub=?' : '';
            $par = $sub !== null ? [$sub] : [];
            $pdo = Db::pdo();
            $t = $pdo->prepare("SELECT COUNT(*) FROM casos$w");
            $t->execute($par);
            $por = function (string $col, array $vals) use ($pdo, $w, $par): array {
                $q = $pdo->prepare("SELECT $col AS k, COUNT(*) AS n FROM casos$w GROUP BY $col");
                $q->execute($par);
                $m = array_column($q->fetchAll(), 'n', 'k');
                return array_map(fn($v) => [$v, (int) ($m[$v] ?? 0)], $vals);
            };
            return ['total' => (int) $t->fetchColumn(), 'estado' => $por('estado', self::EST), 'severidad' => $por('severidad', self::SEV)];
        };
        if ($this->p->tiene('estadisticas:leer')) {
            $this->ok($contar(null) + ['alcance' => 'todos los casos']);
        }
        if ($this->p->tiene('estadisticas:leer_propios')) {
            $this->ok($contar($this->p->sub) + ['alcance' => 'tus casos']);
        }
        if ($this->p->tiene('estadisticas:publicas')) {
            $pdo = Db::pdo();
            $this->ok(['publico' => true, 'total' => (int) $pdo->query('SELECT COUNT(*) FROM casos')->fetchColumn(),
                'resueltos' => (int) $pdo->query("SELECT COUNT(*) FROM casos WHERE estado='resuelto'")->fetchColumn(), 'alcance' => 'datos públicos']);
        }
        $this->denegar('requiere estadisticas:*');
    }

    // ------------------------------------------------------------------ usuarios (directorio)
    private function listarUsuarios(): void
    {
        $this->exigir('usuarios:leer', 'usuarios:admin');
        $salida = [];
        foreach (Ldap::listar() as $u) {
            $e = $u['svc'] ? ['mfa' => false, 'bloqueado' => false] : Keycloak::estadoUsuario($u['id']);
            $salida[] = [
                'id' => $u['id'], 'nombre' => $u['n'], 'grupo' => $u['g'], 'rol' => $u['r'], 'servicio' => $u['svc'],
                'mfa' => $e['mfa'], 'bloqueado' => $u['ldap_bloq'] || $e['bloqueado'],
            ];
        }
        $this->ok($salida);
    }

    private function validarClave(string $clave): void
    {
        if (mb_strlen($clave) < 12) {
            $this->malo('La contraseña debe tener al menos 12 caracteres.');
        }
    }

    private function crearUsuario(): void
    {
        $this->exigir('usuarios:admin');
        $b = $this->cuerpo;
        $id = (string) ($b['id'] ?? '');
        if (!preg_match('/^[a-z]+\.[a-z]+\d*$/', $id) || strlen($id) > 40) {
            $this->malo('Usuario con formato apellido.nombre (minúsculas, sin acentos ni espacios).');
        }
        $nombre = trim((string) ($b['nombre'] ?? ''));
        if ($nombre === '' || mb_strlen($nombre) > 80) {
            $this->malo('El nombre es obligatorio (máx. 80 caracteres).');
        }
        $this->validarClave((string) ($b['clave'] ?? ''));
        Keycloak::olvidarEstados();
        Ldap::crear($id, $nombre, (string) ($b['grupo'] ?? ''), (string) $b['clave']);
        $this->ok(['ok' => true], 201, true);
    }

    private function editarUsuario(string $id): void
    {
        $this->exigir('usuarios:admin');
        if ($id === $this->p->usuario) {
            $this->malo('No puedes modificar tu propia cuenta.');
        }
        $nombre = trim((string) ($this->cuerpo['nombre'] ?? ''));
        if ($nombre === '' || mb_strlen($nombre) > 80) {
            $this->malo('El nombre es obligatorio (máx. 80 caracteres).');
        }
        Keycloak::olvidarEstados();
        Ldap::actualizar($id, $nombre, (string) ($this->cuerpo['grupo'] ?? ''));
        $this->ok(['ok' => true], 200, true);
    }

    private function borrarUsuario(string $id): void
    {
        $this->exigir('usuarios:admin');
        if ($id === $this->p->usuario) {
            $this->malo('No puedes eliminar tu propia cuenta.');
        }
        if (str_starts_with($id, 'svc-')) {
            $this->malo('La cuenta de servicio no se elimina desde aquí.');
        }
        Keycloak::olvidarEstados();
        $kc = Keycloak::idDe($id);
        Ldap::eliminar($id);
        if ($kc) {
            Keycloak::borrarUsuario($kc);   // limpia la copia importada en Keycloak
        }
        $this->ok(['ok' => true], 200, true);
    }

    private function desbloquearUsuario(string $id): void
    {
        $this->exigir('usuarios:admin');
        Keycloak::olvidarEstados();
        Ldap::desbloquear($id);
        if ($kc = Keycloak::idDe($id)) {
            Keycloak::desbloquear($kc);
        }
        $this->ok(['ok' => true], 200, true);
    }

    // ------------------------------------------------------------------ auditoría y configuración
    private function auditoria(): void
    {
        $this->exigir('auditoria:leer');
        $f = Db::pdo()->query('SELECT ts AS t, usuario AS u, evento AS ev, resultado AS res, detalle AS det FROM auditoria ORDER BY id DESC LIMIT 200')->fetchAll();
        $f = array_map(fn($x) => $x + ['src' => 'app'], $f);
        $todo = array_merge($f, Keycloak::eventos());
        usort($todo, fn($a, $b) => strcmp($b['t'], $a['t']));
        $this->ok(array_slice($todo, 0, 300));
    }

    private function verConfig(): void
    {
        $this->exigir('config:admin');
        $r = Keycloak::realm();
        $this->ok(['cicloMin' => intdiv((int) $r['accessTokenLifespan'], 60), 'maxIntentos' => (int) $r['failureFactor'],
            'bloqueoSeg' => (int) $r['waitIncrementSeconds'], 'roles' => Sesiones::todos()]);
    }

    private function guardarConfig(): void
    {
        $this->exigir('config:admin');
        $b = $this->cuerpo;
        $c = (int) ($b['cicloMin'] ?? 0);
        $i = (int) ($b['maxIntentos'] ?? 0);
        $s = (int) ($b['bloqueoSeg'] ?? 0);
        if ($c < 5 || $c > 15) {
            $this->malo('La duración de cada ciclo debe estar entre 5 y 15 minutos.');
        }
        if ($i < 3 || $i > 10) {
            $this->malo('Los intentos fallidos permitidos deben estar entre 3 y 10.');
        }
        if ($s < 10 || $s > 3600) {
            $this->malo('El bloqueo debe durar entre 10 y 3600 segundos.');
        }
        $porRol = [];
        $mayor = 1;
        foreach (Sesiones::ROLES as $rol) {
            $x = $b['roles'][$rol] ?? null;
            if (!is_array($x)) {
                $this->malo("Falta la configuración del rol $rol.");
            }
            $n = (int) ($x['maxCiclos'] ?? 0);
            $in = (int) ($x['inactividadSeg'] ?? 0);
            $av = (int) ($x['avisoSeg'] ?? 0);
            if ($n < 1 || $n > 48) {
                $this->malo("$rol: la cantidad máxima de ciclos debe estar entre 1 y 48.");
            }
            if ($in < 30 || $in > 1800) {
                $this->malo("$rol: la inactividad máxima debe estar entre 30 segundos y 30 minutos.");
            }
            if ($av < 10 || $av > 120 || $av >= $in) {
                $this->malo("$rol: el aviso previo debe estar entre 10 y 120 segundos y ser menor que la inactividad.");
            }
            $porRol[$rol] = ['maxCiclos' => $n, 'inactividadSeg' => $in, 'avisoSeg' => $av];
            $mayor = max($mayor, $n);
        }
        // Keycloak: el acceso se renueva cada ciclo; su sesión absoluta deja un ciclo de margen sobre el rol más largo
        $maxSesion = ($mayor + 1) * $c * 60;
        if (!Keycloak::actualizarRealm(['accessTokenLifespan' => $c * 60, 'failureFactor' => $i, 'waitIncrementSeconds' => $s,
            'ssoSessionMaxLifespan' => $maxSesion, 'ssoSessionIdleTimeout' => min(max(1800, 2 * $c * 60), $maxSesion)])) {
            $this->responder(502, ['error' => 'idp_error', 'detalle' => 'No se pudo aplicar el cambio.']);
        }
        Sesiones::guardar($porRol);
        $this->ok(['cicloMin' => $c, 'maxIntentos' => $i, 'bloqueoSeg' => $s, 'roles' => $porRol], 200, true);
    }
}
