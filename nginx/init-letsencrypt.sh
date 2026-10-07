#!/bin/bash
# Инициализация Let's Encrypt сертификатов.
# Запуск (один раз, на хосте):  ./nginx/init-letsencrypt.sh
# Требует: DOMAIN и CERTBOT_EMAIL в .env, открытые порты 80/443.

set -e

if [ -z "$DOMAIN" ]; then
  echo "Ошибка: задайте DOMAIN в .env"
  exit 1
fi

if [ -z "$CERTBOT_EMAIL" ]; then
  echo "Ошибка: задайте CERTBOT_EMAIL в .env (email для Let's Encrypt)"
  exit 1
fi

rsa_key_size=4096
data_path="./certbot/conf"
www_path="./certbot/www"

mkdir -p "$data_path/live/$DOMAIN" "$www_path"

# --- 1. Скачиваем рекомендованные параметры TLS ---
if [ ! -s "$data_path/options-ssl-nginx.conf" ] || [ ! -s "$data_path/ssl-dhparams.pem" ]; then
  echo "### Скачивание рекомендуемых параметров TLS ..."
  curl -sL "https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf" \
    -o "$data_path/options-ssl-nginx.conf"
  curl -sL "https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem" \
    -o "$data_path/ssl-dhparams.pem"

  # Проверка, что скачалось
  if [ ! -s "$data_path/options-ssl-nginx.conf" ] || [ ! -s "$data_path/ssl-dhparams.pem" ]; then
    echo "Ошибка: не удалось скачать параметры TLS. Проверьте интернет и URL."
    exit 1
  fi
fi

# --- 2. Временный self-signed сертификат (только если настоящего нет) ---
if [ ! -e "$data_path/live/$DOMAIN/fullchain.pem" ]; then
  echo "### Создание временного self-signed сертификата для старта nginx ..."
  openssl req -x509 -nodes -newkey rsa:"$rsa_key_size" -days 1 \
    -keyout "$data_path/live/$DOMAIN/privkey.pem" \
    -out "$data_path/live/$DOMAIN/fullchain.pem" \
    -subj "/CN=$DOMAIN"
fi

# --- 3. Запускаем nginx (с временным сертификатом) ---
echo "### Запуск nginx ..."
docker compose up -d nginx
sleep 3

# --- 4. Удаляем временный сертификат и запрашиваем настоящий ---
echo "### Удаление временного сертификата ..."
rm -rf "$data_path/live/$DOMAIN"
mkdir -p "$data_path/live/$DOMAIN"

echo "### Запрос настоящего сертификата ..."
docker compose run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  --email "$CERTBOT_EMAIL" --agree-tos --no-eff-email \
  -d "$DOMAIN" \
  --rsa-key-size "$rsa_key_size"

# --- 5. Проверка, что сертификат получен ---
if [ ! -e "$data_path/live/$DOMAIN/fullchain.pem" ]; then
  echo "Ошибка: сертификат не получен. Проверьте логи certbot."
  exit 1
fi

# --- 6. Перезагружаем nginx ---
echo "### Перезагрузка nginx ..."
docker compose exec nginx nginx -s reload

echo ""
echo " Готово! Сайт доступен по https://$DOMAIN"
echo ""
echo "Для автообновления добавьте в cron (crontab -e):"
echo "  15 3 * * * cd $(pwd) && docker compose run --rm certbot renew --webroot -w /var/www/certbot && docker compose exec nginx nginx -s reload"