# Builds the dashboard and packages it with Caddy. Build context: repository root.
FROM node:22-alpine AS dashboard
WORKDIR /build
COPY dashboard/package.json dashboard/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY dashboard/ ./
# The dashboard calls the API at this address (baked in at build time)
ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL}
RUN test -n "$VITE_API_URL" || (echo "VITE_API_URL build argument is required" && exit 1) \
 && npx tsc -b && npx vite build

FROM caddy:2.10-alpine
COPY infra/caddy/Caddyfile /etc/caddy/Caddyfile
COPY --from=dashboard /build/dist /srv/dashboard
