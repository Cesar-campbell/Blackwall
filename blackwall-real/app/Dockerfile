# --- dependencias PHP (solo firebase/php-jwt: validación de firma RS256 con JWKS)
FROM composer:2 AS vendor
WORKDIR /app
COPY composer.json ./
RUN composer install --no-dev --prefer-dist --no-progress --no-interaction

# --- imagen final: Apache + PHP con TLS
FROM php:8.3-apache
RUN apt-get update \
 && apt-get install -y --no-install-recommends libldap2-dev \
 && docker-php-ext-configure ldap --with-libdir="lib/$(dpkg-architecture -q DEB_BUILD_MULTIARCH)" \
 && docker-php-ext-install -j"$(nproc)" ldap \
 && rm -rf /var/lib/apt/lists/* \
 && a2enmod ssl rewrite headers deflate \
 && a2dissite 000-default \
 && sed -i 's/^Listen 80$/#Listen 80/' /etc/apache2/ports.conf
RUN mv "$PHP_INI_DIR/php.ini-production" "$PHP_INI_DIR/php.ini"
COPY php-blackwall.ini /usr/local/etc/php/conf.d/zz-blackwall.ini
COPY apache.conf /etc/apache2/sites-available/blackwall.conf
RUN a2ensite blackwall \
 && mkdir -p /var/www/datos /var/www/app \
 && chown www-data:www-data /var/www/datos
COPY --from=vendor /app/vendor /var/www/app/vendor
COPY src /var/www/app/src
COPY public /var/www/app/public
EXPOSE 443
