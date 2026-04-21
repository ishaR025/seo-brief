#!/usr/bin/env python3
"""CLI tool to generate SEO content briefs using Groq."""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

import click
from dotenv import load_dotenv
from groq import Groq
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn

load_dotenv()
console = Console()

SYSTEM_PROMPT = """You are an expert SEO content strategist. Generate comprehensive, actionable SEO content briefs.

Your briefs should be detailed, practical, and tailored to help content writers create high-ranking articles.
Always respond with a structured brief in Markdown format."""

BRIEF_PROMPT = """Generate a detailed SEO content brief for the following:

**Primary Keyword:** {keyword}
**Target Audience:** {audience}
**Content Type:** {content_type}
**Word Count Target:** {word_count}

The brief must include:

## 1. Overview
- Search intent (informational/commercial/transactional/navigational)
- Content goal
- Estimated difficulty

## 2. Title & Meta
- 3 title tag options (under 60 chars)
- Meta description (under 155 chars)
- URL slug suggestion

## 3. Keyword Strategy
- Primary keyword usage guidance
- 5–8 semantic/LSI keywords to include naturally
- 3–5 long-tail keyword variations to target

## 4. Content Outline
- H1 suggestion
- Full H2/H3 structure with notes on what to cover in each section
- Recommended content types per section (e.g., table, list, code block)

## 5. Competitor Insights
- What angles top-ranking articles typically cover
- Content gaps to exploit
- Unique value propositions to include

## 6. On-Page SEO Checklist
- Internal linking suggestions (generic anchors)
- Image alt text guidance
- Schema markup recommendations

## 7. Writing Guidelines
- Tone and voice
- Reading level target
- Key points to emphasize
- What to avoid

## 8. CTAs & Conversion
- Primary CTA recommendation
- Secondary engagement hooks
"""


def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        console.print("[red]Error:[/red] GROQ_API_KEY not set. Add it to .env or export it.")
        sys.exit(1)
    return Groq(api_key=api_key)


def generate_brief(keyword, audience, content_type, word_count, model):
    client = get_groq_client()
    prompt = BRIEF_PROMPT.format(
        keyword=keyword,
        audience=audience,
        content_type=content_type,
        word_count=word_count,
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console,
    ) as progress:
        progress.add_task(f"Generating brief for '{keyword}'...", total=None)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=4096,
        )

    return response.choices[0].message.content


def save_brief(content, keyword, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = keyword.lower().replace(" ", "-").replace("/", "-")
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = output_dir / f"brief-{slug}-{timestamp}.md"
    filename.write_text(content, encoding="utf-8")
    return filename


@click.group()
def cli():
    """SEO Brief Generator — powered by Groq."""
    pass


@cli.command()
@click.argument("keyword")
@click.option("--audience", "-a", default="general audience", show_default=True,
              help="Target audience for the content.")
@click.option("--type", "content_type", default="blog post",
              type=click.Choice(["blog post", "landing page", "product page", "guide", "listicle", "comparison"], case_sensitive=False),
              show_default=True, help="Type of content to create.")
@click.option("--words", "-w", default=1500, show_default=True,
              help="Target word count.")
@click.option("--model", "-m", default="llama-3.3-70b-versatile", show_default=True,
              help="Groq model to use.")
@click.option("--save", "-s", is_flag=True, default=False,
              help="Save the brief to a Markdown file.")
@click.option("--output-dir", "-o", default="./briefs", show_default=True,
              help="Directory to save briefs (used with --save).")
@click.option("--json", "as_json", is_flag=True, default=False,
              help="Output metadata as JSON (brief text + params).")
def generate(keyword, audience, content_type, words, model, save, output_dir, as_json):
    """Generate an SEO content brief for KEYWORD.

    \b
    Examples:
      brief generate "content marketing strategy"
      brief generate "best crm software" --type comparison --words 2500
      brief generate "how to start a podcast" --audience "beginner entrepreneurs" --save
    """
    console.print(Panel(
        f"[bold]Keyword:[/bold] {keyword}\n"
        f"[bold]Audience:[/bold] {audience}\n"
        f"[bold]Type:[/bold] {content_type}\n"
        f"[bold]Words:[/bold] {words}\n"
        f"[bold]Model:[/bold] {model}",
        title="[cyan]SEO Brief Generator[/cyan]",
        border_style="cyan",
    ))

    brief_content = generate_brief(keyword, audience, content_type, words, model)

    if as_json:
        data = {
            "keyword": keyword,
            "audience": audience,
            "content_type": content_type,
            "word_count": words,
            "model": model,
            "generated_at": datetime.now().isoformat(),
            "brief": brief_content,
        }
        click.echo(json.dumps(data, indent=2))
    else:
        console.print()
        console.print(Markdown(brief_content))

    if save:
        path = save_brief(brief_content, keyword, output_dir)
        console.print(f"\n[green]Saved:[/green] {path}")


@cli.command()
def models():
    """List recommended Groq models for content generation."""
    rows = [
        ("llama-3.3-70b-versatile", "Best quality, thorough briefs"),
        ("llama-3.1-8b-instant", "Fastest, good for quick drafts"),
        ("mixtral-8x7b-32768", "Large context, good for complex briefs"),
        ("gemma2-9b-it", "Lightweight alternative"),
    ]
    console.print(Panel("[bold]Recommended Groq Models[/bold]", border_style="cyan"))
    for model, note in rows:
        console.print(f"  [cyan]{model}[/cyan] — {note}")


if __name__ == "__main__":
    cli()
