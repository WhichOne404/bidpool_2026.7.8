FROM nginx:alpine
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx/conf.d/platform.conf /etc/nginx/conf.d/platform.conf
COPY platform-web/index.html /usr/share/nginx/html/index.html
RUN apk add --no-cache curl
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1
CMD ["nginx", "-g", "daemon off;"]
