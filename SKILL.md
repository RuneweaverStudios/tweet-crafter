---
name: tweet-crafter
displayName: Tweet Crafter
description: Drafts engaging tweets in copy-paste friendly code blocks and generates companion blog posts for OpenClaw projects. Integrates with Agent Swarm for AI-powered content generation and enforces ClawHub link best practices.
version: 1.0.0
---

# Tweet Crafter

Streamlines the creation of social media content for OpenClaw skills and projects. Drafts tweets formatted for easy copy-pasting, generates companion blog posts, and enforces ClawHub link best practices.

## Purpose

Automates and standardizes the creation of marketing and announcement content for OpenClaw projects. Makes it easy to share progress and achievements across social media and blogs with consistent formatting and branding.

## Features

- **Tweet Drafting** -- Generates concise, engaging tweets within the character limit using Agent Swarm or local templates.
- **Code Block Output** -- Presents tweets in a code block for one-click copy-pasting without formatting issues.
- **ClawHub Link Enforcement** -- Automatically generates and includes ClawHub skill page links when a skill name is provided.
- **Companion Blog Posts** -- Creates a short blog post to expand on the tweet's announcement.
- **Customizable Content** -- Accepts mentions, hashtags, and context as structured JSON input with validation.
- **JSON Output** -- Supports `--json` flag for machine-readable output, suitable for pipelines and automation.
- **Config-Driven Defaults** -- Default hashtags, character limits, and Agent Swarm settings are configurable via `config.json`.

## Commands

```bash
# Draft a tweet and blog post
python3 scripts/tweet_crafter.py \
  --tweet-prompt "Launching auto-clipper: automatic video highlights" \
  --blog-context "AutoClipper scans folders and creates clips using ffmpeg"

# Include skill name (auto-generates ClawHub link)
python3 scripts/tweet_crafter.py \
  --tweet-prompt "New skill: auto-clipper" \
  --blog-context "Automatic video clip generation" \
  --skill-name auto-clipper

# Include mentions and hashtags
python3 scripts/tweet_crafter.py \
  --tweet-prompt "Check out our new skill" \
  --blog-context "We built something cool" \
  --mentions '["@OpenClaw"]' \
  --hashtags '["#DevTools", "#AI"]'

# Output as JSON (for pipelines)
python3 scripts/tweet_crafter.py \
  --tweet-prompt "OpenClaw update" \
  --blog-context "Latest changes" \
  --json

# Custom character limit
python3 scripts/tweet_crafter.py \
  --tweet-prompt "Short tweet" \
  --blog-context "Context" \
  --character-limit 140
```

## CLI Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--tweet-prompt` | Yes | -- | Core message or announcement for the tweet |
| `--blog-context` | Yes | -- | Background context for the blog post |
| `--skill-name` | No | None | OpenClaw skill name (auto-generates ClawHub link) |
| `--github-repo` | No | None | GitHub repository URL to reference |
| `--clawhub-link` | No | None | Explicit ClawHub link (overrides auto-generated) |
| `--mentions` | No | `[]` | JSON array of @mentions |
| `--hashtags` | No | `[]` | JSON array of #hashtags |
| `--character-limit` | No | 280 | Tweet character limit |
| `--json` | No | false | Output results as JSON |

## Configuration (config.json)

```json
{
  "defaults": {
    "characterLimit": 280,
    "style": "engaging",
    "includeClawHubLink": true
  },
  "hashtags": {
    "always": ["#OpenClaw"],
    "optional": ["#DevTools", "#AI", "#Automation", "#BuildInPublic"]
  },
  "mentions": {
    "default": []
  },
  "agentSwarm": {
    "model": "openrouter/moonshotai/kimi-k2.5",
    "tier": "CREATIVE",
    "timeoutSeconds": 60
  },
  "clawHub": {
    "baseUrl": "https://clawhub.dev/skills/"
  },
  "output": {
    "jsonIndent": 2
  }
}
```

## Output Format

### Standard Output

```
--- TWEET DRAFT ---
```text
Excited to share AutoClipper! Automatically generate video highlights from your recordings. Check it out: https://clawhub.dev/skills/auto-clipper #OpenClaw #DevTools
```

--- BLOG POST DRAFT ---
# AutoClipper

We are thrilled to announce AutoClipper...
```

### JSON Output (`--json`)

```json
{
  "tweet": "```text\nExcited to share AutoClipper!...\n```",
  "blog_post": "# AutoClipper\n\nWe are thrilled to announce..."
}
```

## Content Generation

Tweet Crafter uses a three-tier content generation strategy:

1. **Agent Swarm (Direct)** -- Calls the router.py script directly if the agent-swarm skill is installed locally.
2. **OpenClaw Exec** -- Falls back to `openclaw exec agent-swarm` for gateway-based generation.
3. **Local Templates** -- When no external service is available, generates content using built-in templates that extract key phrases from prompts.

## Input Validation

- `--mentions` and `--hashtags` must be valid JSON arrays of strings. Invalid input produces a clear error message.
- Tweets exceeding the character limit are automatically truncated with `...`.
- Empty prompts are rejected by argparse's `required=True` constraint.

## Dependencies

- **Python 3.8+** -- Runtime
- **Agent Swarm** (optional) -- For AI-powered content generation

## Directory Structure

```
tweet-crafter/
├── SKILL.md              # Skill specification
├── _meta.json            # Skill metadata
├── config.json           # Configuration defaults
├── README.md             # Quick-start guide
├── requirements.txt      # Python dependencies
├── .gitignore            # Git ignore rules
└── scripts/
    └── tweet_crafter.py  # Main entry point
```
