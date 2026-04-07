#!/usr/bin/env bash
# AI Translate Agent - Linux/macOS Startup Script
# Usage: chmod +x start.sh && ./start.sh
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT/backend"
FRONTEND_DIR="$ROOT/frontend"
VENV_DIR="$BACKEND_DIR/.venv"
ENV_FILE="$ROOT/.env"

# ── Colors ──
info()  { printf "\033[36m[INFO]\033[0m  %s\n" "$1"; }
ok()    { printf "\033[32m[ OK ]\033[0m  %s\n" "$1"; }
warn()  { printf "\033[33m[WARN]\033[0m  %s\n" "$1"; }
fatal() { printf "\033[31m[FAIL]\033[0m  %s\n" "$1"; exit 1; }

echo ""
echo -e "\033[35m  AI Translate Agent\033[0m"
echo ""

# ── 1. Check Python 3.10+ ──
info "Checking Python..."
if command -v python3 &>/dev/null; then
    PY=python3
elif command -v python &>/dev/null; then
    PY=python
else
    fatal "Python not found. Install Python 3.10+: https://www.python.org"
fi
PY_VER=$($PY --version 2>&1)
ok "Found $PY_VER"

# ── 2. Check/Install uv ──
info "Checking uv..."
if ! command -v uv &>/dev/null; then
    warn "uv not found, installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    if ! command -v uv &>/dev/null; then
        fatal "uv install failed. Manual install: https://docs.astral.sh/uv/"
    fi
fi
ok "Found $(uv --version)"

# ── 3. Check Node.js ──
info "Checking Node.js..."
if ! command -v node &>/dev/null; then
    fatal "Node.js not found. Install: https://nodejs.org or 'curl -fsSL https://fnm.vercel.app/install | bash'"
fi
ok "Found Node.js $(node --version)"

# ── 4. Check npm ──
if ! command -v npm &>/dev/null; then
    fatal "npm not found. It should come with Node.js."
fi

# ── 5. Check .env ──
info "Checking .env..."
if [ ! -f "$ENV_FILE" ]; then
    warn ".env not found, creating template..."
    cat > "$ENV_FILE" << 'ENVEOF'
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://openrouter.ai/api/v1
DEFAULT_MODEL=qwen/qwen3.6-plus:free
ENVEOF
    warn "Please edit .env and set a real OPENAI_API_KEY, then re-run."
    exit 0
fi
if grep -q "your_api_key_here" "$ENV_FILE"; then
    fatal "Please set a real OPENAI_API_KEY in .env first."
fi
ok ".env is ready"

# ── 6. Backend: create venv & install deps ──
info "Setting up backend Python environment..."
if [ -f "$VENV_DIR/bin/uvicorn" ]; then
    ok "Backend venv already exists, skipping uv sync"
else
    cd "$BACKEND_DIR"
    uv sync --quiet
    cd "$ROOT"
    ok "Backend dependencies installed"
fi
ok "Backend venv ready: $VENV_DIR"

# ── 7. Frontend: npm install ──
info "Checking frontend dependencies..."
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    info "Running npm install (first time)..."
    cd "$FRONTEND_DIR"
    npm install --silent
    cd "$ROOT"
    ok "Frontend dependencies installed"
else
    ok "node_modules already present"
fi

# ── 8. Stop old processes ──
info "Stopping old processes..."
pkill -f "uvicorn.*app.main:app" 2>/dev/null && warn "Stopped old backend" || true
pkill -f "node.*vite" 2>/dev/null && warn "Stopped old frontend" || true
sleep 1
ok "Old processes cleaned"

# ── 9. Load .env ──
set -a
source "$ENV_FILE"
set +a

# ── 10. Start backend ──
info "Starting backend on port 8000..."
cd "$BACKEND_DIR"
export PYTHONPATH="$BACKEND_DIR"
"$VENV_DIR/bin/uvicorn" app.main:app --reload --port 8000 --host 0.0.0.0 &
BACKEND_PID=$!
cd "$ROOT"
sleep 2

# ── 11. Start frontend ──
info "Starting frontend on port 5173..."
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!
cd "$ROOT"
sleep 2

# ── Done ──
echo ""
ok "=== Services started ==="
echo ""
echo -e "  Frontend : \033[36mhttp://localhost:5173\033[0m"
echo -e "  Backend  : \033[36mhttp://localhost:8000\033[0m"
echo -e "  Swagger  : \033[36mhttp://localhost:8000/docs\033[0m"
echo ""
info "Press Ctrl+C to stop all services."

# Trap Ctrl+C to clean up
cleanup() {
    echo ""
    warn "Shutting down..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    wait 2>/dev/null
    ok "All services stopped."
    exit 0
}
trap cleanup SIGINT SIGTERM

# Wait for background processes
wait
