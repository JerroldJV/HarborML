FROM nginx:alpine
RUN apk update && apk add bash
COPY includes/nginx.conf /etc/nginx/nginx.conf
