FROM nginx:latest

# Remove default nginx config
RUN rm /etc/nginx/nginx.conf

# Copy custom nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Create cache directory
RUN mkdir -p /var/cache/nginx && \
    chmod -R 755 /var/cache/nginx

# Create nginx user and adjust permissions
RUN chown -R nginx:nginx /var/cache/nginx && \
    chown nginx:nginx /var/run/nginx.pid

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/api/health || exit 1

# Expose ports
EXPOSE 80 443

# Run nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
