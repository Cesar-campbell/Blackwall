<?php
declare(strict_types=1);

namespace Blackwall;

/** Error con código HTTP para devolver mensajes claros desde la API. */
final class ErrorNegocio extends \RuntimeException
{
    public function __construct(string $m, public readonly int $http = 400)
    {
        parent::__construct($m);
    }
}

/**
 * Directorio (OpenLDAP por LDAPS) como fuente única de usuarios y grupos.
 * La app se conecta con la cuenta de servicio svc-blackwall-sync (permisos limitados por ACL en el directorio).
 */
final class Ldap
{
    /** Grupo del directorio → rol de la aplicación (mismo mapeo que configura Keycloak). */
    public const GRUPOS = [
        'GRP_TI_ADMIN' => 'ROL_ADMIN',
        'GRP_SOC_ANALISTA' => 'ROL_ANALISTA',
        'GRP_CUM_AUDITOR' => 'ROL_AUDITOR',
        'GRP_USR_USUARIO' => 'ROL_USUARIO',
        'GRP_PUB_INVITADO' => 'ROL_INVITADO',
    ];

    private static function conectar()
    {
        ldap_set_option(null, LDAP_OPT_X_TLS_CACERTFILE, Config::get('CA_BUNDLE'));
        ldap_set_option(null, LDAP_OPT_X_TLS_REQUIRE_CERT, LDAP_OPT_X_TLS_DEMAND);
        $ds = ldap_connect(Config::get('LDAP_URL'));
        ldap_set_option($ds, LDAP_OPT_PROTOCOL_VERSION, 3);
        ldap_set_option($ds, LDAP_OPT_NETWORK_TIMEOUT, 5);
        if (!@ldap_bind($ds, Config::get('LDAP_BIND_DN'), Config::get('LDAP_BIND_PASSWORD'))) {
            throw new \RuntimeException('No se pudo conectar al directorio: ' . ldap_error($ds));
        }
        return $ds;
    }

    private static function base(): string
    {
        return Config::get('LDAP_BASE');
    }

    private static function dnGrupo(string $grupo): string
    {
        return 'cn=' . $grupo . ',ou=' . self::area($grupo) . ',' . self::base();
    }

    public static function area(string $grupo): string
    {
        return strtolower(explode('_', $grupo)[1] ?? 'usr');
    }

    /** @return list<array<string,mixed>> */
    public static function listar(): array
    {
        $ds = self::conectar();
        $miembros = [];
        $g = ldap_search($ds, self::base(), '(objectClass=groupOfNames)', ['cn', 'member']);
        foreach (ldap_get_entries($ds, $g) as $e) {
            if (!is_array($e) || !isset($e['cn'][0])) {
                continue;
            }
            for ($i = 0; $i < ($e['member']['count'] ?? 0); $i++) {
                $miembros[strtolower($e['member'][$i])] = $e['cn'][0];
            }
        }
        $r = ldap_search($ds, self::base(), '(|(objectClass=inetOrgPerson)(objectClass=simpleSecurityObject))',
            ['uid', 'cn', 'objectClass', 'pwdAccountLockedTime']);
        $lista = [];
        foreach (ldap_get_entries($ds, $r) as $e) {
            if (!is_array($e) || !isset($e['uid'][0])) {
                continue;
            }
            $clases = [];
            for ($i = 0; $i < ($e['objectclass']['count'] ?? 0); $i++) {
                $clases[] = strtolower($e['objectclass'][$i]);
            }
            $svc = !in_array('inetorgperson', $clases, true);   // la cuenta de servicio no es una persona
            $grupo = $miembros[strtolower($e['dn'])] ?? null;
            $lista[] = [
                'id' => $e['uid'][0],
                'n' => $svc ? 'Cuenta de servicio (sincronización)' : ($e['cn'][0] ?? $e['uid'][0]),
                'g' => $grupo,
                'r' => $grupo ? (self::GRUPOS[$grupo] ?? null) : null,
                'svc' => $svc,
                'ldap_bloq' => isset($e['pwdaccountlockedtime'][0]),
            ];
        }
        usort($lista, fn($a, $b) => [$a['svc'], $a['id']] <=> [$b['svc'], $b['id']]);
        return $lista;
    }

    private static function dnDe($ds, string $uid): ?string
    {
        $r = ldap_search($ds, self::base(), '(&(objectClass=inetOrgPerson)(uid=' . ldap_escape($uid, '', LDAP_ESCAPE_FILTER) . '))', ['uid']);
        $e = ldap_get_entries($ds, $r);
        return ($e['count'] ?? 0) > 0 ? $e[0]['dn'] : null;
    }

    private static function grupoActual($ds, string $dn): ?string
    {
        $r = ldap_search($ds, self::base(), '(&(objectClass=groupOfNames)(member=' . ldap_escape($dn, '', LDAP_ESCAPE_FILTER) . '))', ['cn']);
        $e = ldap_get_entries($ds, $r);
        return ($e['count'] ?? 0) > 0 ? $e[0]['cn'][0] : null;
    }

    private static function partir(string $nombre): array
    {
        $partes = preg_split('/\s+/', trim($nombre), 2);
        return [$partes[0], $partes[1] ?? $partes[0]];
    }

    public static function crear(string $uid, string $nombre, string $grupo, string $clave): void
    {
        if (!isset(self::GRUPOS[$grupo])) {
            throw new ErrorNegocio('Grupo no válido.');
        }
        $ds = self::conectar();
        if (self::dnDe($ds, $uid) !== null) {
            throw new ErrorNegocio('Ese usuario ya existe. Si hay homónimos, agrega un número (perez.juan2).');
        }
        [$nom, $ape] = self::partir($nombre);
        $dn = 'uid=' . ldap_escape($uid, '', LDAP_ESCAPE_DN) . ',ou=' . self::area($grupo) . ',' . self::base();
        $ok = @ldap_add($ds, $dn, [
            'objectClass' => ['inetOrgPerson'], 'uid' => $uid, 'cn' => trim($nombre), 'givenName' => $nom, 'sn' => $ape,
            'mail' => $uid . '@blackwall.utp', 'userPassword' => $clave,
        ]);
        if (!$ok) {
            // La política de contraseñas vive en el directorio (ppolicy): longitud mínima 12, historial, etc.
            throw new ErrorNegocio(ldap_errno($ds) === 19 ? 'La contraseña no cumple la política del directorio (mínimo 12 caracteres).' : 'No se pudo crear el usuario: ' . ldap_error($ds));
        }
        if (!@ldap_mod_add($ds, self::dnGrupo($grupo), ['member' => $dn]) && ldap_errno($ds) !== 20) {   // 20 = ya era miembro
            @ldap_delete($ds, $dn);
            throw new ErrorNegocio('No se pudo asignar el grupo: ' . ldap_error($ds), 500);
        }
    }

    public static function actualizar(string $uid, string $nombre, string $grupo): void
    {
        if (!isset(self::GRUPOS[$grupo])) {
            throw new ErrorNegocio('Grupo no válido.');
        }
        $ds = self::conectar();
        $dn = self::dnDe($ds, $uid) ?? throw new ErrorNegocio('No encontrado', 404);
        [$nom, $ape] = self::partir($nombre);
        @ldap_mod_replace($ds, $dn, ['cn' => trim($nombre), 'givenName' => $nom, 'sn' => $ape]);
        $actual = self::grupoActual($ds, $dn);
        if ($actual !== $grupo) {
            // Primero se agrega al grupo nuevo; si falla, no se toca el anterior (nunca queda sin rol por error)
            if (!@ldap_mod_add($ds, self::dnGrupo($grupo), ['member' => $dn]) && ldap_errno($ds) !== 20) {
                throw new ErrorNegocio('No se pudo cambiar de grupo: ' . ldap_error($ds), 500);
            }
            if ($actual !== null) {
                if (!@ldap_mod_del($ds, self::dnGrupo($actual), ['member' => $dn])) {
                    throw new ErrorNegocio('El usuario era el único miembro del grupo anterior; ese grupo no puede quedar vacío en el directorio.', 409);
                }
            }
        }
    }

    public static function eliminar(string $uid): void
    {
        $ds = self::conectar();
        $dn = self::dnDe($ds, $uid) ?? throw new ErrorNegocio('No encontrado', 404);
        $g = self::grupoActual($ds, $dn);
        if ($g !== null && !@ldap_mod_del($ds, self::dnGrupo($g), ['member' => $dn])) {
            throw new ErrorNegocio('No se puede eliminar al único miembro del grupo ' . $g . ' (un grupo no puede quedar vacío).', 409);
        }
        if (!@ldap_delete($ds, $dn)) {
            throw new ErrorNegocio('No se pudo eliminar: ' . ldap_error($ds), 500);
        }
    }

    /** Quita el bloqueo de la política de contraseñas (ppolicy). */
    public static function desbloquear(string $uid): void
    {
        $ds = self::conectar();
        $dn = self::dnDe($ds, $uid) ?? throw new ErrorNegocio('No encontrado', 404);
        @ldap_mod_del($ds, $dn, ['pwdAccountLockedTime' => []]);
        @ldap_mod_del($ds, $dn, ['pwdFailureTime' => []]);
    }
}
