#!/usr/bin/env bash
set -euo pipefail

# Install fde-agent-skills into Claude Code, OpenAI Codex / Antigravity, or a project repo.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

TARGET="claude"
MODE="symlink"
DEST=""
WITH_AGENTS=0
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: ./scripts/install.sh [options]

Options:
  --target <claude|agents|project>  Destination runtime (default: claude)
                                    claude  -> ~/.claude/skills (and ~/.claude/agents with --with-agents)
                                    agents  -> ~/.agents/skills
                                    project -> <dest>/.claude/skills (requires --dest)
  --dest <path>                     Custom base directory (required for --target project; overrides home)
  --mode <symlink|copy>             Install via symlinks or standalone copies (default: symlink)
  --with-agents                     Also install the 5 subagent specs from agents/
  --dry-run                         Print planned actions without changing any files
  -h, --help                        Show this help message
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --target)
      [ $# -ge 2 ] || { echo "error: --target requires a value" >&2; exit 2; }
      TARGET="$2"
      shift 2
      ;;
    --dest)
      [ $# -ge 2 ] || { echo "error: --dest requires a value" >&2; exit 2; }
      DEST="$2"
      shift 2
      ;;
    --mode)
      [ $# -ge 2 ] || { echo "error: --mode requires a value" >&2; exit 2; }
      MODE="$2"
      shift 2
      ;;
    --with-agents)
      WITH_AGENTS=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "$MODE" in
  symlink|copy) ;;
  *)
    echo "error: --mode must be 'symlink' or 'copy', got '$MODE'" >&2
    exit 2
    ;;
esac

case "$TARGET" in
  claude)
    BASE="${DEST:-$HOME/.claude}"
    SKILLS_DEST="$BASE/skills"
    AGENTS_DEST="$BASE/agents"
    ;;
  agents)
    BASE="${DEST:-$HOME/.agents}"
    SKILLS_DEST="$BASE/skills"
    AGENTS_DEST="$BASE/agents"
    ;;
  project)
    if [ -z "$DEST" ]; then
      echo "error: --target project requires --dest <repo-path>" >&2
      exit 2
    fi
    BASE="$DEST/.claude"
    SKILLS_DEST="$BASE/skills"
    AGENTS_DEST="$BASE/agents"
    ;;
  *)
    echo "error: --target must be 'claude', 'agents', or 'project', got '$TARGET'" >&2
    exit 2
    ;;
esac

install_dir() {
  local src="$1"
  local dst="$2"
  if [ "$DRY_RUN" -eq 1 ]; then
    echo "[dry-run] $MODE $src -> $dst"
    return 0
  fi
  mkdir -p "$(dirname "$dst")"
  if [ -L "$dst" ]; then
    rm "$dst"
  elif [ -e "$dst" ]; then
    echo "error: destination already exists and is not a symlink (move or remove it first): $dst" >&2
    exit 1
  fi
  if [ "$MODE" = "symlink" ]; then
    ln -s "$src" "$dst"
  else
    cp -R "$src" "$dst"
  fi
  echo "installed ($MODE): $dst"
}

install_file() {
  local src="$1"
  local dst="$2"
  if [ "$DRY_RUN" -eq 1 ]; then
    echo "[dry-run] $MODE $src -> $dst"
    return 0
  fi
  mkdir -p "$(dirname "$dst")"
  if [ -L "$dst" ]; then
    rm "$dst"
  elif [ -e "$dst" ]; then
    echo "error: destination already exists and is not a symlink (move or remove it first): $dst" >&2
    exit 1
  fi
  if [ "$MODE" = "symlink" ]; then
    ln -s "$src" "$dst"
  else
    cp "$src" "$dst"
  fi
  echo "installed ($MODE): $dst"
}

SKILL_COUNT=0
for skill_dir in "$REPO_ROOT"/skills/*; do
  [ -d "$skill_dir" ] || continue
  [ -f "$skill_dir/SKILL.md" ] || continue
  name="$(basename "$skill_dir")"
  install_dir "$skill_dir" "$SKILLS_DEST/$name"
  SKILL_COUNT=$((SKILL_COUNT + 1))
done

AGENT_COUNT=0
if [ "$WITH_AGENTS" -eq 1 ]; then
  for agent_file in "$REPO_ROOT"/agents/*.md; do
    [ -f "$agent_file" ] || continue
    name="$(basename "$agent_file")"
    install_file "$agent_file" "$AGENTS_DEST/$name"
    AGENT_COUNT=$((AGENT_COUNT + 1))
  done
fi

echo "done: $SKILL_COUNT skill(s), $AGENT_COUNT agent(s) ($MODE -> $BASE)"
