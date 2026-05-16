#!/bin/bash
# ============================================================================
# Hermes Agent + kiro-cli Local Setup
# ============================================================================
# Sets up Hermes Agent to use kiro-cli as its native LLM backbone.
# No cloud APIs, no external dependencies — everything runs locally.
#
# Prerequisites:
#   - kiro-cli installed (~/.local/bin/kiro-cli)
#   - Python 3.11+
#   - uv (Python package manager)
#
# Usage:
#   chmod +x setup-kiro-local.sh
#   ./setup-kiro-local.sh
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WRAPPER_DIR="$(dirname "$SCRIPT_DIR")/kiro-openai-wrapper"

echo -e "${BOLD}${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     Hermes Agent + kiro-cli Local Setup                     ║"
echo "║     No cloud. No API keys. Pure local intelligence.         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ─── Step 1: Verify kiro-cli ──────────────────────────────────────────────────

echo -e "${BLUE}[1/6]${NC} Checking kiro-cli..."

KIRO_CLI="${KIRO_CLI_PATH:-$HOME/.local/bin/kiro-cli}"
if [ -x "$KIRO_CLI" ]; then
    echo -e "  ${GREEN}✓${NC} Found kiro-cli at $KIRO_CLI"
else
    echo -e "  ${RED}✗${NC} kiro-cli not found at $KIRO_CLI"
    echo -e "  ${YELLOW}Set KIRO_CLI_PATH if installed elsewhere${NC}"
    exit 1
fi

# ─── Step 2: Install Hermes Agent ─────────────────────────────────────────────

echo -e "${BLUE}[2/6]${NC} Installing Hermes Agent..."

if command -v uv &>/dev/null; then
    echo -e "  ${GREEN}✓${NC} uv found"
else
    echo -e "  ${YELLOW}Installing uv...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# Install in development mode from the fork
cd "$SCRIPT_DIR"
if [ -f "pyproject.toml" ]; then
    echo -e "  Installing from local source..."
    uv pip install -e "." --quiet 2>/dev/null || pip install -e "." --quiet
    echo -e "  ${GREEN}✓${NC} Hermes Agent installed (dev mode)"
else
    echo -e "  ${RED}✗${NC} pyproject.toml not found. Are you in the hermes-agent directory?"
    exit 1
fi

# ─── Step 3: Set up kiro-openai-wrapper ───────────────────────────────────────

echo -e "${BLUE}[3/6]${NC} Setting up kiro-openai-wrapper..."

if [ -d "$WRAPPER_DIR" ]; then
    cd "$WRAPPER_DIR"
    pip install -r requirements.txt --quiet 2>/dev/null
    echo -e "  ${GREEN}✓${NC} Wrapper dependencies installed"
else
    echo -e "  ${YELLOW}⚠${NC} kiro-openai-wrapper not found at $WRAPPER_DIR"
    echo -e "  ${YELLOW}  You'll need to start it manually${NC}"
fi

# ─── Step 4: Configure Hermes for local usage ─────────────────────────────────

echo -e "${BLUE}[4/6]${NC} Configuring Hermes for local-only usage..."

mkdir -p "$HERMES_HOME"

# Copy local config
cp "$SCRIPT_DIR/kiro-local-config.yaml" "$HERMES_HOME/config.yaml"
echo -e "  ${GREEN}✓${NC} Config written to $HERMES_HOME/config.yaml"

# Create SOUL.md if it doesn't exist
if [ ! -f "$HERMES_HOME/SOUL.md" ]; then
    cat > "$HERMES_HOME/SOUL.md" << 'SOUL'
# Identity

You are Hermes, a self-improving AI agent running locally via kiro-cli.
You learn from every interaction, create reusable skills, and maintain
persistent memory. You are direct, capable, and continuously improving.

## Principles

- Be helpful and thorough
- Remember what you learn across sessions
- Create skills for recurring tasks
- Be honest about limitations
- Respect the user's time — be concise unless asked for detail

## Local Context

You run entirely locally through kiro-cli. No cloud APIs are involved.
All your memory, skills, and session data live on the user's machine.
You have full filesystem access and can execute commands freely.
SOUL
    echo -e "  ${GREEN}✓${NC} Created default SOUL.md"
fi

# Create MEMORY.md if it doesn't exist
if [ ! -f "$HERMES_HOME/MEMORY.md" ]; then
    cat > "$HERMES_HOME/MEMORY.md" << 'MEMORY'
# Agent Memory

## Setup
- Running locally via kiro-cli + hermes-agent
- No cloud dependencies
- Full local filesystem access

## User Preferences
(Will be populated as I learn)

## Project Context
(Will be populated as I work on projects)
MEMORY
    echo -e "  ${GREEN}✓${NC} Created default MEMORY.md"
fi

# ─── Step 5: Create launcher script ──────────────────────────────────────────

echo -e "${BLUE}[5/6]${NC} Creating launcher..."

cat > "$HERMES_HOME/start-local.sh" << LAUNCHER
#!/bin/bash
# Start Hermes Agent with kiro-cli backend
# This starts the wrapper and then launches Hermes

WRAPPER_DIR="$WRAPPER_DIR"
WRAPPER_PID=""

cleanup() {
    if [ -n "\$WRAPPER_PID" ]; then
        kill \$WRAPPER_PID 2>/dev/null
        echo "Stopped kiro-openai-wrapper (PID \$WRAPPER_PID)"
    fi
}
trap cleanup EXIT

# Start the wrapper in background
if [ -d "\$WRAPPER_DIR" ]; then
    cd "\$WRAPPER_DIR"
    python main.py &
    WRAPPER_PID=\$!
    sleep 2
    echo "🔗 kiro-openai-wrapper started (PID \$WRAPPER_PID) on http://localhost:8000"
fi

# Launch Hermes
cd "$SCRIPT_DIR"
hermes "\$@"
LAUNCHER

chmod +x "$HERMES_HOME/start-local.sh"
echo -e "  ${GREEN}✓${NC} Launcher created at $HERMES_HOME/start-local.sh"

# ─── Step 6: Verify installation ─────────────────────────────────────────────

echo -e "${BLUE}[6/6]${NC} Verifying installation..."

if command -v hermes &>/dev/null; then
    echo -e "  ${GREEN}✓${NC} 'hermes' command available"
else
    echo -e "  ${YELLOW}⚠${NC} 'hermes' not in PATH — you may need to restart your shell"
fi

echo ""
echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${GREEN}  Setup complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${BOLD}Quick start:${NC}"
echo -e "    ${CYAN}$HERMES_HOME/start-local.sh${NC}  — Start wrapper + Hermes together"
echo ""
echo -e "  ${BOLD}Or manually:${NC}"
echo -e "    ${CYAN}cd $WRAPPER_DIR && python main.py &${NC}  — Start wrapper"
echo -e "    ${CYAN}hermes${NC}                                    — Start Hermes"
echo ""
echo -e "  ${BOLD}Configuration:${NC}"
echo -e "    Config:  ${CYAN}$HERMES_HOME/config.yaml${NC}"
echo -e "    Soul:    ${CYAN}$HERMES_HOME/SOUL.md${NC}"
echo -e "    Memory:  ${CYAN}$HERMES_HOME/MEMORY.md${NC}"
echo ""
echo -e "  ${BOLD}Key features enabled:${NC}"
echo -e "    • Microcompact (LLM-free context stripping every turn)"
echo -e "    • Persistent memory across sessions"
echo -e "    • Auto skill creation"
echo -e "    • No cloud dependencies"
echo -e "    • Full local filesystem access"
echo ""
