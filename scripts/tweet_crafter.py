#!/usr/bin/env python3
"""
Tweet Crafter - Drafts engaging tweets and companion blog posts for OpenClaw projects.

Integrates with Agent Swarm for AI-powered content generation and falls back to
a local template-based generator when the router is unavailable. Outputs tweets
in copy-paste friendly code blocks and enforces ClawHub link best practices.
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

SKILL_DIR = Path(__file__).parent.parent
CONFIG_PATH = SKILL_DIR / "config.json"


def load_config() -> dict:
    """Load configuration from config.json, returning empty dict if missing."""
    if not CONFIG_PATH.exists():
        logging.warning("config.json not found at %s; using defaults.", CONFIG_PATH)
        return {}
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        logging.error("Invalid JSON in config.json: %s", exc)
        return {}


_config = load_config()

AGENT_SWARM_SCRIPT = SKILL_DIR.parent / "agent-swarm" / "scripts" / "router.py"


def _validate_json_list(raw: str, label: str) -> List[str]:
    """Parse a JSON string that should be an array of strings. Raises ValueError on bad input."""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON for --{label}: {exc}. Expected a JSON array, e.g. '[\"@user\"]'.")
    if not isinstance(parsed, list):
        raise ValueError(f"--{label} must be a JSON array, got {type(parsed).__name__}.")
    for i, item in enumerate(parsed):
        if not isinstance(item, str):
            raise ValueError(f"--{label}[{i}] must be a string, got {type(item).__name__}.")
    return parsed


def _call_agent_swarm(prompt: str, model: str = None, tier: str = None) -> str:
    """Call Agent Swarm's router to generate content.

    Tries three methods in order:
      1. Direct router.py invocation
      2. openclaw exec agent-swarm
      3. Local template-based generator (fallback)
    """
    swarm_cfg = _config.get("agentSwarm", {})
    model = model or swarm_cfg.get("model", "openrouter/moonshotai/kimi-k2.5")
    tier = tier or swarm_cfg.get("tier", "CREATIVE")
    timeout = swarm_cfg.get("timeoutSeconds", 60)

    logging.info("Generating content (model: %s, tier: %s)", model, tier)

    # Method 1: Direct router.py
    if AGENT_SWARM_SCRIPT.exists():
        try:
            result = subprocess.run(
                ["python3", str(AGENT_SWARM_SCRIPT), "spawn", "--json", prompt],
                capture_output=True, text=True, timeout=timeout
            )
            if result.returncode == 0 and result.stdout.strip():
                try:
                    data = json.loads(result.stdout)
                    if "generated_content" in data and not data["generated_content"].startswith("[MOCKED"):
                        return data["generated_content"]
                    logging.info(
                        "Router returned routing metadata (tier=%s, model=%s). Using local generator.",
                        data.get("recommendation", {}).get("tier", "?"),
                        data.get("model", "?"),
                    )
                except json.JSONDecodeError:
                    pass
        except (subprocess.TimeoutExpired, OSError) as exc:
            logging.warning("Agent Swarm call failed: %s. Using local generator.", exc)

    # Method 2: openclaw exec
    try:
        result = subprocess.run(
            ["openclaw", "exec", "agent-swarm", "--json", json.dumps({"prompt": prompt, "model": model})],
            capture_output=True, text=True, timeout=timeout
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass

    # Method 3: Local fallback
    logging.info("Using local template-based generation (Agent Swarm not available).")
    return _generate_locally(prompt)


def _generate_locally(prompt: str) -> str:
    """Template-based content generator that produces tweets and blog posts
    without requiring an external LLM."""
    prompt_lower = prompt.lower()

    if "tweet" in prompt_lower:
        quoted = re.findall(r'["\']([^"\']+)["\']', prompt)
        topic = quoted[0] if quoted else "our latest update"

        mentions = re.findall(r"@\w+", prompt)
        hashtags = re.findall(r"#\w+", prompt)

        parts = [f"Excited to share {topic}!"]
        if mentions:
            parts.append(" ".join(mentions))
        parts.append("Check it out and let us know what you think.")
        if hashtags:
            parts.append(" ".join(hashtags))

        tweet = " ".join(parts)
        if len(tweet) > 280:
            tweet = tweet[:277] + "..."
        return tweet

    elif "blog" in prompt_lower:
        quoted = re.findall(r'["\']([^"\']+)["\']', prompt)
        topic = quoted[0] if quoted else "our latest project"

        return textwrap.dedent(f"""\
        # {topic.title()}

        We are thrilled to announce {topic}. This has been a labor of love, and we
        cannot wait for you to try it out.

        ## What It Does

        {topic.capitalize()} brings a fresh approach to solving everyday development
        challenges. Whether you are a seasoned developer or just getting started, this
        tool is designed to fit right into your workflow.

        ## Getting Started

        Head over to the project page for installation instructions and examples. We
        have put together comprehensive documentation to help you get up and running
        quickly.

        ## What is Next

        We have exciting plans on the roadmap. Stay tuned for updates, and do not
        hesitate to open an issue or reach out with feedback.

        Happy building!
        """)

    else:
        return f"Content generated for: {prompt[:100]}"


def draft_content(
    tweet_prompt: str,
    blog_context: str,
    skill_name: Optional[str] = None,
    github_repo: Optional[str] = None,
    clawhub_link: Optional[str] = None,
    mentions: Optional[List[str]] = None,
    hashtags: Optional[List[str]] = None,
    character_limit: int = 280,
) -> Dict[str, Any]:
    """Draft a tweet and a companion blog post.

    Args:
        tweet_prompt: Core message or announcement for the tweet.
        blog_context: Background context for the blog post.
        skill_name: OpenClaw skill name (auto-generates ClawHub link if not provided).
        github_repo: GitHub repository URL to include.
        clawhub_link: Explicit ClawHub link (overrides auto-generated one).
        mentions: List of @mentions to include.
        hashtags: List of #hashtags to include.
        character_limit: Maximum tweet character count (default: 280).

    Returns:
        Dict with 'tweet' (formatted in a code block) and 'blog_post' keys.
    """
    logging.info("Drafting tweet and blog content...")

    # Auto-generate ClawHub link if skill_name is provided and no explicit link
    hub_cfg = _config.get("clawHub", {})
    if skill_name and not clawhub_link and hub_cfg.get("baseUrl"):
        clawhub_link = f"{hub_cfg['baseUrl'].rstrip('/')}/{skill_name}"

    # Merge config defaults
    defaults_cfg = _config.get("defaults", {})
    character_limit = character_limit or defaults_cfg.get("characterLimit", 280)

    cfg_hashtags = _config.get("hashtags", {}).get("always", [])
    if hashtags:
        hashtags = list(set(hashtags + cfg_hashtags))
    elif cfg_hashtags:
        hashtags = cfg_hashtags

    # Build tweet prompt
    full_tweet_prompt = f'Craft a tweet (max {character_limit} chars) based on: """{tweet_prompt}""" '
    if skill_name:
        full_tweet_prompt += f"about the skill {skill_name} "
    if clawhub_link:
        full_tweet_prompt += f"Include the ClawHub link: {clawhub_link}. "
    if mentions:
        full_tweet_prompt += f"Mention: {' '.join(mentions)}. "
    if hashtags:
        full_tweet_prompt += f"Include hashtags: {' '.join(hashtags)}. "
    full_tweet_prompt += "Ensure it's engaging and concise."

    drafted_tweet = _call_agent_swarm(full_tweet_prompt, tier="CREATIVE")

    # Enforce character limit
    if len(drafted_tweet) > character_limit:
        drafted_tweet = drafted_tweet[: character_limit - 3] + "..."

    # Build blog prompt
    full_blog_prompt = f'Write a blog post about """{tweet_prompt}""" using this context: """{blog_context}""" '
    if skill_name:
        full_blog_prompt += f"Focus on the {skill_name} skill. "
    if github_repo:
        full_blog_prompt += f"Mention the GitHub repository: {github_repo}. "
    if clawhub_link:
        full_blog_prompt += f"Also link the ClawHub page: {clawhub_link}. "
    full_blog_prompt += "Make it human, witty, intelligent, not overly technical."

    drafted_blog = _call_agent_swarm(full_blog_prompt, tier="CREATIVE")

    # Format tweet as a code block for easy copying
    formatted_tweet = f"```text\n{drafted_tweet}\n```"
    return {"tweet": formatted_tweet, "blog_post": drafted_blog}


def main():
    parser = argparse.ArgumentParser(
        description="Tweet Crafter - Draft engaging tweets and companion blog posts for OpenClaw projects."
    )
    parser.add_argument("--tweet-prompt", "--tweet_prompt", type=str, required=True, help="Prompt for the tweet.")
    parser.add_argument("--blog-context", "--blog_context", type=str, required=True, help="Context for the blog post.")
    parser.add_argument("--skill-name", "--skill_name", type=str, default=None, help="OpenClaw skill name.")
    parser.add_argument("--github-repo", "--github_repo", type=str, default=None, help="GitHub repository URL.")
    parser.add_argument("--clawhub-link", "--clawhub_link", type=str, default=None, help="ClawHub link.")
    parser.add_argument(
        "--mentions", type=str, default="[]",
        help='JSON array of @mentions (e.g., \'["@openclaw", "@user"]\'). Must be valid JSON.'
    )
    parser.add_argument(
        "--hashtags", type=str, default="[]",
        help='JSON array of #hashtags (e.g., \'["#OpenClaw", "#AI"]\'). Must be valid JSON.'
    )
    parser.add_argument("--character-limit", "--character_limit", type=int, default=280, help="Tweet character limit.")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format.")

    args = parser.parse_args()

    try:
        mentions_list = _validate_json_list(args.mentions, "mentions")
        hashtags_list = _validate_json_list(args.hashtags, "hashtags")
    except ValueError as exc:
        logging.error(str(exc))
        sys.exit(1)

    try:
        result = draft_content(
            tweet_prompt=args.tweet_prompt,
            blog_context=args.blog_context,
            skill_name=args.skill_name,
            github_repo=args.github_repo,
            clawhub_link=args.clawhub_link,
            mentions=mentions_list,
            hashtags=hashtags_list,
            character_limit=args.character_limit,
        )

        if args.json:
            print(json.dumps(result, indent=_config.get("output", {}).get("jsonIndent", 2)))
        else:
            print("--- TWEET DRAFT ---")
            print(result["tweet"])
            print("\n--- BLOG POST DRAFT ---")
            print(result["blog_post"])

    except Exception as exc:
        logging.error("Error in Tweet Crafter: %s", exc)
        if args.json:
            print(json.dumps({"error": str(exc)}))
        else:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
