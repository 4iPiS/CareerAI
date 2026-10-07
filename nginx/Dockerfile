FROM nginx:1.27-alpine

# Конфиг сайта кладётся в conf.d/: он включается внутрь http{} основного
# конфига nginx, поэтому limit_req_zone и server{} здесь валидны.
COPY default.conf /etc/nginx/conf.d/careerai.conf
