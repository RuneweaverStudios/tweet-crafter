# Tweet Crafter

Draft engaging tweets and companion blog posts for OpenClaw projects. Outputs tweets in copy-paste friendly code blocks and enforces ClawHub link best practices.

## Quick Start

```bash
# Draft a tweet and blog post
python3 scripts/tweet_crafter.py \
  --tweet-prompt "Launching our new video clipper skill" \
  --blog-context "AutoClipper automatically generates video highlights using ffmpeg"

# Include a skill name (auto-generates ClawHub link)
python3 scripts/tweet_crafter.py \
  --tweet-prompt "New skill alert" \
  --blog-context "We just shipped auto-clipper" \
  --skill-name auto-clipper

# Output as JSON for pipelines
python3 scripts/tweet_crafter.py \
  --tweet-prompt "OpenClaw update" \
  --blog-context "Latest changes" \
  --json
```

## Requirements

- **Python 3.8+**
- **Agent Swarm** skill (optional) -- used for AI-powered content generation. Falls back to local templates when unavailable.

## Installation

No external Python packages required. Clone the repo and run directly:

```bash
git clone https://github.com/RuneweaverStudios/tweet-crafter.git
cd tweet-crafter
python3 scripts/tweet_crafter.py --help
```

## Configuration

Edit `config.json` to set defaults:

- **Default hashtags** -- Tags like `#OpenClaw` are automatically appended to every tweet
- **Character limit** -- Default tweet length (280)
- **Agent Swarm model** -- Which model to use for content generation
- **ClawHub base URL** -- For auto-generating skill page links

## Usage Examples

```bash
# With mentions and hashtags
python3 scripts/tweet_crafter.py \
  --tweet-prompt "Check out our new skill" \
  --blog-context "We built something cool" \
  --mentions '["@OpenClaw"]' \
  --hashtags '["#DevTools", "#AI"]'

# Custom character limit (e.g., for shorter platforms)
python3 scripts/tweet_crafter.py \
  --tweet-prompt "Short post" \
  --blog-context "Context" \
  --character-limit 140
```

## Output

Standard output shows the tweet in a code block (for easy copying) followed by the blog post. Use `--json` for structured output suitable for automation pipelines.

See `SKILL.md` for full CLI reference, configuration options, and architecture details.
