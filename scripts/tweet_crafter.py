#!/usr/bin/env python3
import os
import sys
import json
import argparse
import logging
import subprocess
import textwrap

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SKILL_DIR, "..", "config.json")

def load_config():
    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

_config = load_config()

AGENT_SWARM_SCRIPT = os.path.join(
    SKILL_DIR, "..", "..", "agent-swarm", "scripts", "router.py"
)


def _call_agent_swarm(prompt: str, model: str = "openrouter/moonshotai/kimi-k2.5", tier: str = "CREATIVE") -> str:
    """
    Call Agent Swarm's router to generate content.  Falls back to a local
    template-based generator when the router is unavailable.
    """
    logging.info(f"Generating content (model: {model}, tier: {tier})")

    # Try Agent Swarm router if it exists.
    # Note: The router returns routing/classification metadata (model selection,
    # tier, sessionTarget) -- it does NOT generate content itself.  The actual
    # content generation would be handled by the OpenClaw orchestrator via
    # sessions_spawn.  When running standalone we use the local generator.
    if os.path.exists(AGENT_SWARM_SCRIPT):
        try:
            result = subprocess.run(
                ["python3", AGENT_SWARM_SCRIPT, "spawn", "--json", prompt],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0 and result.stdout.strip():
                try:
                    data = json.loads(result.stdout)
                    # If the router returned actual generated content, use it
                    if "generated_content" in data and not data["generated_content"].startswith("[MOCKED"):
                        return data["generated_content"]
                    # Otherwise the router only provided routing metadata --
                    # fall through to local generation
                    logging.info(f"Router classified as tier={data.get('recommendation', {}).get('tier', '?')}, "
                                 f"model={data.get('model', '?')}. Using local generator for content.")
                except json.JSONDecodeError:
                    pass
        except (subprocess.TimeoutExpired, OSError) as e:
            logging.warning(f"Agent Swarm call failed: {e}. Using local generator.")

    # Try openclaw exec agent-swarm
    try:
        result = subprocess.run(
            ["openclaw", "exec", "agent-swarm", "--json", json.dumps({"prompt": prompt, "model": model})],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass

    # Fallback: generate content locally using templates
    logging.info("Using local template-based generation (Agent Swarm not available).")
    return _generate_locally(prompt)


def _generate_locally(prompt: str) -> str:
    """
    Template-based content generator that produces reasonable tweets and blog
    posts without requiring an external LLM.
    """
    prompt_lower = prompt.lower()

    if "tweet" in prompt_lower:
        # Extract key phrases from the prompt for the tweet
        # Look for quoted content
        import re
        quoted = re.findall(r'["\']([^"\']+)["\']', prompt)
        topic = quoted[0] if quoted else "our latest update"

        # Extract mentions and hashtags if present
        mentions = re.findall(r'@\w+', prompt)
        hashtags = re.findall(r'#\w+', prompt)

        tweet_parts = []
        tweet_parts.append(f"Excited to share {topic}!")
        if mentions:
            tweet_parts.append(" ".join(mentions))
        tweet_parts.append("Check it out and let us know what you think.")
        if hashtags:
            tweet_parts.append(" ".join(hashtags))

        tweet = " ".join(tweet_parts)
        # Trim to character limit if needed
        if len(tweet) > 280:
            tweet = tweet[:277] + "..."
        return tweet

    elif "blog" in prompt_lower:
        import re
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
    skill_name: str = None,
    github_repo: str = None,
    clawhub_link: str = None,
    mentions: list = None,
    hashtags: list = None,
    character_limit: int = 280
) -> dict:
    logging.info("Drafting tweet and blog content...")

    # Build tweet prompt
    full_tweet_prompt = f"Craft a tweet (max {character_limit} chars) based on: '\"\"\"{tweet_prompt}\"\"\"' "
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
        drafted_tweet = drafted_tweet[:character_limit - 3] + "..."

    # Build blog prompt
    full_blog_prompt = f"Write a blog post about '\"\"\"{tweet_prompt}\"\"\"' using this context: '\"\"\"{blog_context}\"\"\"' "
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Tweet Crafter Skill for OpenClaw.")
    parser.add_argument('--tweet_prompt', type=str, required=True, help='Prompt for the tweet.')
    parser.add_argument('--blog_context', type=str, required=True, help='Context for the blog post.')
    parser.add_argument('--skill_name', type=str, default=None, help='Name of the skill.')
    parser.add_argument('--github_repo', type=str, default=None, help='GitHub repository URL.')
    parser.add_argument('--clawhub_link', type=str, default=None, help='ClawHub link.')
    parser.add_argument('--mentions', type=str, default='[]', help='JSON string of mentions (e.g., ["@user1"]).')
    parser.add_argument('--hashtags', type=str, default='[]', help='JSON string of hashtags (e.g., ["#tag1"]).')
    parser.add_argument('--character_limit', type=int, default=280, help='Tweet character limit.')

    args = parser.parse_args()

    try:
        mentions_list = json.loads(args.mentions)
        hashtags_list = json.loads(args.hashtags)

        result = draft_content(
            tweet_prompt=args.tweet_prompt,
            blog_context=args.blog_context,
            skill_name=args.skill_name,
            github_repo=args.github_repo,
            clawhub_link=args.clawhub_link,
            mentions=mentions_list,
            hashtags=hashtags_list,
            character_limit=args.character_limit
        )
        print("--- TWEET DRAFT ---")
        print(result["tweet"])
        print("\n--- BLOG POST DRAFT ---")
        print(result["blog_post"])
    except Exception as e:
        logging.error(f"Error in Tweet Crafter: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
