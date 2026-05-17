#!/bin/bash
# ============================================================================
# Install MCP servers into kiro-cli
# ============================================================================
# Run this once to add the MCP servers that Hermes uses via kiro-cli.
# These give you: web search, browser automation, arxiv papers,
# library docs, and structured reasoning.
#
# Prerequisites: kiro-cli installed, npm/npx available, uv/uvx available
# ============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

echo "🔧 Installing MCP servers into kiro-cli..."
echo ""

# Check prerequisites
if ! command -v kiro-cli &>/dev/null && ! [ -x ~/.local/bin/kiro-cli ]; then
    echo "❌ kiro-cli not found. Install Kiro IDE first."
    exit 1
fi

KIRO_CLI="${KIRO_CLI:-$(which kiro-cli 2>/dev/null || echo ~/.local/bin/kiro-cli)}"

if ! command -v npx &>/dev/null; then
    echo "❌ npx not found. Install Node.js first: brew install node"
    exit 1
fi

if ! command -v uvx &>/dev/null; then
    echo "${YELLOW}⚠ uvx not found. Installing uv...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# Install each MCP server
echo -e "${GREEN}[1/5]${NC} steelmind (structured reasoning: think + verify)"
$KIRO_CLI mcp add --name steelmind --command npx --args "-y,@stabgan/steelmind-mcp@latest" --force 2>/dev/null || true

echo -e "${GREEN}[2/5]${NC} playwright (browser automation)"
$KIRO_CLI mcp add --name playwright --command npx --args "@playwright/mcp@latest" --force 2>/dev/null || true

echo -e "${GREEN}[3/5]${NC} arxiv (academic paper search)"
$KIRO_CLI mcp add --name arxiv --command uvx --args "arxiv-mcp-server,--storage-path,$HOME/.arxiv-mcp-papers" --force 2>/dev/null || true

echo -e "${GREEN}[4/5]${NC} tavily-remote (web search, crawl, extract)"
if [ -z "${TAVILY_API_KEY:-}" ]; then
    echo -e "  ${YELLOW}⚠ TAVILY_API_KEY not set. Get one free at https://tavily.com${NC}"
    read -p "  Enter your Tavily API key (or press Enter to skip): " TAVILY_KEY
    if [ -z "$TAVILY_KEY" ]; then
        echo "  Skipping tavily (you can add it later with: kiro-cli mcp add ...)"
    else
        $KIRO_CLI mcp add --name tavily-remote --command npx --args "-y,mcp-remote@latest,https://mcp.tavily.com/mcp/?tavilyApiKey=${TAVILY_KEY}" --force 2>/dev/null || true
    fi
else
    $KIRO_CLI mcp add --name tavily-remote --command npx --args "-y,mcp-remote@latest,https://mcp.tavily.com/mcp/?tavilyApiKey=${TAVILY_API_KEY}" --force 2>/dev/null || true
fi

echo -e "${GREEN}[5/5]${NC} Context7 (library documentation)"
$KIRO_CLI mcp add --name Context7 --command npx --args "-y,@upstash/context7-mcp@latest" --force 2>/dev/null || true

echo ""
echo -e "${GREEN}✅ Done! MCP servers installed.${NC}"
echo ""
echo "Verify with: kiro-cli mcp list"
echo ""
echo "Servers added:"
echo "  • steelmind  — structured thinking (think/verify tools)"
echo "  • playwright — browser automation (navigate, click, screenshot)"
echo "  • arxiv      — search/download academic papers"
echo "  • tavily     — web search, crawl, extract, research"
echo "  • Context7   — library documentation lookup"
