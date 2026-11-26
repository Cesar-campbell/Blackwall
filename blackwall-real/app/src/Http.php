<?php
declare(strict_types=1);

namespace Blackwall;

/** Cliente HTTP mínimo con cURL. Siempre verifica el certificado contra la CA del laboratorio. */
final class Http
{
    /** @return array{0:int,1:string} [código, cuerpo] */
    public static function pedir(string $metodo, string $url, array|string|null $cuerpo = null, array $cabeceras = []): array
    {
        $ch = curl_init($url);
        // cURL resuelve *.localhost a 127.0.0.1 sin consultar el DNS de Docker: se mapea el nombre público
        // del IdP (que debe coincidir con el issuer y el certificado) a su contenedor.
        $host = (string) parse_url($url, PHP_URL_HOST);
        $puerto = (int) (parse_url($url, PHP_URL_PORT) ?: 443);
        foreach (explode(',', (string) getenv('RESOLVE_MAP')) as $par) {
            [$nombre, $destino] = array_pad(explode('=', trim($par), 2), 2, '');
            if ($nombre !== '' && $nombre === $host && ($ip = gethostbyname($destino)) !== $destino) {
                curl_setopt($ch, CURLOPT_RESOLVE, ["$host:$puerto:$ip"]);
            }
        }
        curl_setopt_array($ch, [
            CURLOPT_CUSTOMREQUEST => $metodo,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => 10,
            CURLOPT_CONNECTTIMEOUT => 5,
            CURLOPT_CAINFO => Config::get('CA_BUNDLE'),
            CURLOPT_SSL_VERIFYPEER => true,
            CURLOPT_SSL_VERIFYHOST => 2,
            CURLOPT_FOLLOWLOCATION => false,
            CURLOPT_HTTPHEADER => $cabeceras,
        ]);
        if ($cuerpo !== null) {
            curl_setopt($ch, CURLOPT_POSTFIELDS, is_array($cuerpo) ? http_build_query($cuerpo) : $cuerpo);
        }
        $r = curl_exec($ch);
        if ($r === false) {
            $e = curl_error($ch);
            curl_close($ch);
            throw new \RuntimeException("Error de red hacia $url: $e");
        }
        $codigo = (int) curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
        curl_close($ch);
        return [$codigo, (string) $r];
    }

    public static function json(string $metodo, string $url, array|string|null $cuerpo = null, array $cabeceras = []): array
    {
        [$st, $r] = self::pedir($metodo, $url, $cuerpo, $cabeceras);
        return [$st, json_decode($r, true) ?? []];
    }
}
