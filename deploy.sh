#!/usr/bin/env bash
# ============================================================
# deploy.sh — Despliegue de Replicador Platform
# Uso: ./deploy.sh [frontend|backend|all]
# Requiere: docker, docker-compose, node, npm, angular-cli
# ============================================================
set -euo pipefail

APP_NAME="replicador"
FRONTEND_DIR="frontend"
BACKEND_DIR="backend"
NGINX_SITES="/etc/nginx/sites-available"
NGINX_ENABLED="/etc/nginx/sites-enabled"
DEPLOY_DIR="/var/www/${APP_NAME}-frontend"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
err()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ─── Frontend ───────────────────────────────────────────────
build_frontend() {
    info "Compilando frontend Angular (baseHref=/replicador/)..."
    cd "$FRONTEND_DIR"
    npm ci || npm install
    npx ng build --configuration production
    cd ..

    if [ ! -d "$FRONTEND_DIR/dist" ]; then
        err "Build de Angular falló — no existe dist/"
    fi

    sudo mkdir -p "$DEPLOY_DIR"
    sudo cp -r "$FRONTEND_DIR/dist/"* "$DEPLOY_DIR/"
    sudo chown -R www-data:www-data "$DEPLOY_DIR" 2>/dev/null || true
    ok "Frontend desplegado en $DEPLOY_DIR"
}

# ─── Backend (Docker) ───────────────────────────────────────
build_backend() {
    info "Construyendo e iniciando servicios Docker..."
    local dc
    if command -v docker-compose &>/dev/null; then
        dc="docker-compose"
    else
        dc="docker compose"
    fi

    # Baja contenedores existentes y libera puertos antes de levantar
    sudo $dc down --remove-orphans 2>/dev/null || true

    sudo $dc build
    sudo $dc up -d
    sudo $dc ps
    ok "Backend desplegado. Revisa '$dc logs -f'"
}

# ─── Nginx ──────────────────────────────────────────────────
setup_nginx() {
    local conf="replicador.nginx.conf"
    if [ ! -f "$conf" ]; then
        err "No se encuentra $conf"
    fi

    info "Instalando configuración de nginx..."
    sudo cp "$conf" "${NGINX_SITES}/${APP_NAME}"
    if [ -f "${NGINX_ENABLED}/${APP_NAME}" ]; then
        sudo rm "${NGINX_ENABLED}/${APP_NAME}"
    fi
    sudo ln -sf "${NGINX_SITES}/${APP_NAME}" "${NGINX_ENABLED}/${APP_NAME}"

    sudo nginx -t || err "Configuración de nginx inválida"
    sudo systemctl reload nginx || sudo systemctl restart nginx

    ok "Nginx configurado con ruta /${APP_NAME}:"
    echo "  - https://tudominio.com/${APP_NAME}        → Frontend Angular"
    echo "  - https://tudominio.com/${APP_NAME}/api    → API Flask"
}

setup_ssl() {
    if ! command -v certbot &>/dev/null; then
        err "certbot no instalado. Ejecuta: sudo apt install certbot python3-certbot-nginx"
    fi

    info "Solicitando certificados SSL..."
    sudo certbot --nginx --non-interactive --agree-tos -m admin@tudominio.com || {
        sudo certbot --nginx
    }
    ok "SSL configurado"
}

# ─── SSL con Certbot ────────────────────────────────────────
setup_ssl() {
    if ! command -v certbot &>/dev/null; then
        err "certbot no instalado. Ejecuta: sudo apt install certbot python3-certbot-nginx"
    fi

    local domains=(
        "-d app.${APP_NAME}.tudominio.com"
        "-d api.${APP_NAME}.tudominio.com"
    )

    info "Solicitando certificados SSL..."
    sudo certbot --nginx "${domains[@]}" --non-interactive --agree-tos -m admin@tudominio.com || {
        sudo certbot --nginx "${domains[@]}"
    }
    ok "SSL configurado. Los subdominios ahora usan HTTPS"
}

# ─── Todo ───────────────────────────────────────────────────
deploy_all() {
    build_frontend
    build_backend
    setup_nginx
    echo ""
    ok "=== Despliegue completo finalizado ==="
}

# ─── Main ───────────────────────────────────────────────────
case "${1:-all}" in
    frontend)      build_frontend ;;
    backend)       build_backend ;;
    nginx)         setup_nginx ;;
    ssl)           setup_ssl ;;
    all)           deploy_all ;;
    *)
        echo "Uso: $0 [frontend|backend|nginx|ssl|all]"
        echo ""
        echo "  frontend  → Compila Angular (baseHref=/replicador/) y copia a ${DEPLOY_DIR}"
        echo "  backend   → Build & up con docker compose"
        echo "  nginx     → Instala config bajo /replicador"
        echo "  ssl       → Certbot SSL para el dominio"
        echo "  all       → Ejecuta todo lo anterior"
        exit 1
        ;;
esac
