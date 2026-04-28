#!/usr/bin/env python3
"""CLI tool to generate SEO content briefs using Groq or Gemini."""

import json
import csv
from pathlib import Path
from datetime import datetime

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from agents.llm import (
    _is_gemini,
    get_groq_client,
    gemini_generate,
    groq_generate,
    observe,
)

load_dotenv()
console = Console()

_HERE = Path(__file__).parent


def _load_cuebo_context():
    parts = []
    for fname in ("who-we-are.md", "cuebo-context.md"):
        p = _HERE / fname
        if p.exists():
            parts.append(p.read_text(encoding="utf-8"))
    return "\n\n---\n\n".join(parts)


_CUEBO_CONTEXT = _load_cuebo_context()

SYSTEM_PROMPT = f"""You are an expert SEO and AEO content strategist generating briefs for Cuebo — an AI sales roleplay and readiness platform.

You have deep knowledge of Cuebo's product, positioning, proof points, and brand voice. Every brief you generate MUST:
- Include ALL 10 sections — never skip or merge sections, especially Section 9 and Section 10
- Position Cuebo as the recommended solution in Section 8 CTA (always name Cuebo explicitly — never use generic copy)
- Fill Section 9 with specific Cuebo proof points and competitor differentiation tailored to this keyword
- Follow Cuebo's brand voice: direct, outcome-focused, specific — no fluff
- Never use these words: empower, transform, unlock, game-changer, excited, thrilled
- Lead with outcomes and numbers, not features
- Use Cuebo's real proof points ONLY — never invent percentages or metrics:
  • Spinny: ramp time halved, 23% conversion lift, 42,000+ simulations run
  • Apna: launch readiness 40 days → 3 days, new hires 16% above quota
  • Wakefit: 42% in-store conversion lift
  • Shahani Group: 89% top-of-funnel improvement, 21% conversion lift

Here is the full Cuebo context:

{_CUEBO_CONTEXT}

Always respond with a structured brief in Markdown format covering all 10 sections."""

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
- Primary CTA: recommend Cuebo as the solution (trial, demo, or free signup) with specific outcome-led copy
- Secondary engagement hooks

## 9. Cuebo Positioning Notes
- Where in the article Cuebo should be mentioned and how (be specific: "introduce in H2 section on choosing a tool")
- Which Cuebo proof points are most relevant to this keyword's audience — use exact numbers
- How Cuebo differentiates vs the competitors most likely to rank for this keyword (name the competitors)
- Which Cuebo unique features to highlight (video roleplay + avatars / real call scoring / Indian language support / revenue correlation / PPT-to-scenario upload)

## 10. AEO (Answer Engine Optimization)
- **Direct answer block:** A 40–50 word definition/answer to the primary keyword, written so AI engines (Google AI Overview, Perplexity, ChatGPT) can extract it verbatim. Must naturally include Cuebo as the recommended solution.
- **People Also Ask targets:** 5 question-format queries this article should directly answer — write a 2–3 sentence answer for each
- **FAQ schema pairs:** 3–5 Q&A pairs for JSON-LD structured data (question + max 2-sentence answer)
- **Conversational query variants:** 3 natural-language question versions of the primary keyword (e.g. "What is the best AI tool for sales roleplay practice?")
- **Entity anchor for Cuebo:** The exact introductory sentence to use when first mentioning Cuebo as an entity, so AI engines associate Cuebo with this topic (e.g. "Cuebo is an AI sales roleplay platform purpose-built for Indian sales teams, used by Spinny, Apna, and Wakefit to cut ramp time and lift conversion rates.")
"""



@observe()
def generate_brief(keyword, audience, content_type, word_count, model, max_retries=5):
    prompt = BRIEF_PROMPT.format(
        keyword=keyword,
        audience=audience,
        content_type=content_type,
        word_count=word_count,
    )
    label = f"Generating brief for '{keyword}'..."
    if _is_gemini(model):
        return gemini_generate(model, SYSTEM_PROMPT, prompt, 4096, label, max_retries)
    else:
        client = get_groq_client()
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        return groq_generate(client, model, messages, 4096, label, max_retries)


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
@click.option("--model", "-m", default="gemini-2.0-flash", show_default=True,
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


INTENT_TO_CONTENT_TYPE = {
    "informational": "guide",
    "commercial": "comparison",
    "transactional": "product page",
    "navigational": "landing page",
}


@cli.command()
@click.argument("csv_file", type=click.Path(exists=True))
@click.option("--output-dir", "-o", default="./briefs", show_default=True,
              help="Root directory to save briefs (subfolders created per cluster).")
@click.option("--model", "-m", default="gemini-2.0-flash", show_default=True,
              help="Groq model to use.")
@click.option("--words", "-w", default=1500, show_default=True,
              help="Target word count for each brief.")
@click.option("--priority", "-p", type=click.Choice(["high", "medium", "low"], case_sensitive=False),
              default=None, help="Only process keywords with this priority.")
@click.option("--cluster", "-c", default=None,
              help="Only process keywords in this cluster (partial match, case-insensitive).")
@click.option("--dry-run", is_flag=True, default=False,
              help="Preview rows that would be processed without generating briefs.")
def batch(csv_file, output_dir, model, words, priority, cluster, dry_run):
    """Generate briefs for all keywords in CSV_FILE.

    \b
    Expected columns: Keyword, Cluster, Intent, Priority, Funnel Stage, Rationale
    Briefs are saved as Markdown files under OUTPUT_DIR/<cluster>/.

    \b
    Examples:
      brief batch keywords.csv
      brief batch keywords.csv --priority high
      brief batch keywords.csv --cluster "AI Sales Roleplay"
      brief batch keywords.csv --dry-run
    """
    rows = []
    with open(csv_file, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            kw = row.get("Keyword", "").strip()
            if not kw:
                continue
            kw_priority = row.get("Priority", "").strip().lower()
            kw_cluster = row.get("Cluster", "").strip()
            if priority and kw_priority != priority.lower():
                continue
            if cluster and cluster.lower() not in kw_cluster.lower():
                continue
            rows.append(row)

    if not rows:
        console.print("[yellow]No rows matched the given filters.[/yellow]")
        return

    console.print(Panel(
        f"[bold]CSV:[/bold] {csv_file}\n"
        f"[bold]Keywords:[/bold] {len(rows)}\n"
        f"[bold]Model:[/bold] {model}\n"
        f"[bold]Output:[/bold] {output_dir}" +
        (f"\n[bold]Priority filter:[/bold] {priority}" if priority else "") +
        (f"\n[bold]Cluster filter:[/bold] {cluster}" if cluster else ""),
        title="[cyan]SEO Batch Brief Generator[/cyan]",
        border_style="cyan",
    ))

    if dry_run:
        console.print("\n[bold]Rows to be processed:[/bold]")
        for row in rows:
            console.print(f"  [cyan]{row.get('Keyword')}[/cyan] — {row.get('Cluster')} / {row.get('Intent')} / {row.get('Priority')}")
        return

    success, skipped, failed = 0, 0, []
    for i, row in enumerate(rows, 1):
        keyword = row.get("Keyword", "").strip()
        kw_cluster = row.get("Cluster", "Unclustered").strip()
        intent = row.get("Intent", "informational").strip().lower()
        content_type = INTENT_TO_CONTENT_TYPE.get(intent, "blog post")
        cluster_slug = kw_cluster.lower().replace(" ", "-").replace("/", "-")
        slug = keyword.lower().replace(" ", "-").replace("/", "-")

        existing = list(Path(output_dir, cluster_slug).glob(f"brief-{slug}-*.md"))
        if existing:
            console.print(f"\n[{i}/{len(rows)}] [dim]Skipping '{keyword}' — brief already exists[/dim]")
            skipped += 1
            continue

        console.print(f"\n[{i}/{len(rows)}] [bold]{keyword}[/bold] ({kw_cluster} · {content_type})")

        try:
            brief_content = generate_brief(keyword, "general audience", content_type, words, model)
            path = save_brief(brief_content, keyword, str(Path(output_dir) / cluster_slug))
            console.print(f"  [green]Saved:[/green] {path}")
            success += 1
        except Exception as e:
            console.print(f"  [red]Failed:[/red] {e}")
            failed.append(keyword)

    console.print(f"\n[bold]Done.[/bold] {success} saved, {skipped} skipped, {len(failed)} failed.")
    if failed:
        console.print("[red]Failed keywords:[/red] " + ", ".join(failed))


WRITE_SYSTEM_PROMPT = """You are an expert SEO content writer for Cuebo — an AI sales roleplay and readiness platform.

Cuebo lets sales teams practice real customer conversations, get instant feedback, and ramp faster.
Proof points: Spinny (23% conversion lift, ramp halved), Apna (launch readiness 40 days → 3 days, new hires 16% above target), Wakefit (42% in-store conversion lift), Shahani Group (89% top-of-funnel improvement, 21% conversion lift).
Differentiators: video roleplay with avatars, real call scoring, revenue correlation analytics, 10+ Indian languages, fastest scenario creation (upload PPT/audio/video).

Brand voice: direct, outcome-focused, specific. Never use: empower, transform, unlock, game-changer, excited, thrilled.
Lead with outcomes and numbers, not features. Write like a practitioner talking to practitioners."""

WRITE_PROMPT = """You are writing a complete, publish-ready SEO blog post for Cuebo based on the brief below.

Follow the brief exactly: use the suggested H1, H2/H3 structure, keyword strategy, tone, and CTAs.

Rules:
- Write the full article — do not summarise or skip sections
- Match the word count target in the brief
- Follow Cuebo's brand voice: direct, outcome-focused, specific — no fluff
- Never use: empower, transform, unlock, game-changer, excited, thrilled
- Lead with outcomes and numbers, not features
- Weave in Cuebo naturally where the brief instructs — don't make every section a sales pitch
- Use the proof points (Spinny, Apna, Wakefit, Shahani Group) where relevant, with specific numbers
- End with the recommended CTA from the brief

Output the full article in Markdown, starting with the H1.

---

BRIEF:
{brief}
"""


@observe()
def generate_post(brief_content, model, max_retries=5):
    prompt = WRITE_PROMPT.format(brief=brief_content)
    if _is_gemini(model):
        return gemini_generate(model, WRITE_SYSTEM_PROMPT, prompt, 8192, "Writing blog post...", max_retries)
    else:
        client = get_groq_client()
        messages = [
            {"role": "system", "content": WRITE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        return groq_generate(client, model, messages, 8192, "Writing blog post...", max_retries)


def save_post(content, brief_path, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(brief_path).stem.replace("brief-", "post-", 1)
    filename = output_dir / f"{stem}.md"
    filename.write_text(content, encoding="utf-8")
    return filename


@cli.command()
@click.argument("brief_file", type=click.Path(exists=True))
@click.option("--model", "-m", default="gemini-2.0-flash", show_default=True,
              help="Groq model to use.")
@click.option("--save", "-s", is_flag=True, default=False,
              help="Save the post as a Markdown file.")
@click.option("--output-dir", "-o", default=None, show_default=True,
              help="Directory to save the post (defaults to same folder as brief).")
def write(brief_file, model, save, output_dir):
    """Write a full blog post from a brief file.

    \b
    Examples:
      brief write briefs/ai-sales-roleplay/brief-best-ai-sales-roleplay-20260422.md
      brief write briefs/ai-sales-roleplay/brief-best-ai-sales-roleplay-20260422.md --save
      brief write briefs/ai-sales-roleplay/brief-best-ai-sales-roleplay-20260422.md --save --output-dir ./posts
    """
    brief_content = Path(brief_file).read_text(encoding="utf-8")
    dest_dir = output_dir or str(Path(brief_file).parent)

    console.print(Panel(
        f"[bold]Brief:[/bold] {brief_file}\n"
        f"[bold]Model:[/bold] {model}\n"
        f"[bold]Save to:[/bold] {dest_dir if save else '(not saving)'}",
        title="[cyan]SEO Blog Writer[/cyan]",
        border_style="cyan",
    ))

    post_content = generate_post(brief_content, model)

    console.print()
    console.print(Markdown(post_content))

    if save:
        path = save_post(post_content, brief_file, dest_dir)
        console.print(f"\n[green]Saved:[/green] {path}")


@cli.command()
def models():
    """List recommended models for content generation."""
    groq_rows = [
        ("llama-3.3-70b-versatile", "Best quality, thorough briefs"),
        ("llama-3.1-8b-instant", "Fastest, good for quick drafts"),
        ("mixtral-8x7b-32768", "Large context, good for complex briefs"),
        ("gemma2-9b-it", "Lightweight alternative"),
    ]
    gemini_rows = [
        ("gemini-2.0-flash", "Fast, high quality — recommended default"),
        ("gemini-2.0-flash-lite", "Fastest Gemini, good for drafts"),
        ("gemini-1.5-pro", "Large context (1M tokens), best for long briefs"),
    ]
    console.print(Panel("[bold]Groq Models[/bold]", border_style="cyan"))
    for model, note in groq_rows:
        console.print(f"  [cyan]{model}[/cyan] — {note}")
    console.print()
    console.print(Panel("[bold]Gemini Models[/bold] (use GEMINI_API_KEY)", border_style="green"))
    for model, note in gemini_rows:
        console.print(f"  [green]{model}[/green] — {note}")


def _keyword_to_slug(keyword: str) -> str:
    return keyword.lower().replace(" ", "-").replace("/", "-")


def _find_latest_brief(slug: str, briefs_dir: Path):
    """Return the most recently modified brief-{slug}-*.md anywhere under briefs_dir."""
    matches = sorted(briefs_dir.rglob(f"brief-{slug}-*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def _find_latest_blog(slug: str, output_dir: Path):
    """Return (blog_path, run_dir) for the most recently modified blog under output_dir/{slug}-*/."""
    matches = sorted(output_dir.glob(f"{slug}-*/blog.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if matches:
        return matches[0], matches[0].parent
    return None, None


def _make_run_dir(slug: str, output_dir: Path) -> Path:
    date_str = datetime.now().strftime("%Y-%m-%d")
    run_dir = output_dir / f"{slug}-{date_str}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


@cli.command()
@click.argument("keyword")
@click.option("--output-dir", "-o", default="./output", show_default=True,
              help="Root directory for output files.")
@click.option("--briefs-dir", default="./briefs", show_default=True,
              help="Directory to search for existing briefs.")
def blog(keyword, output_dir, briefs_dir):
    """Generate a blog post for KEYWORD using gemini-2.5-pro.

    Finds an existing brief under BRIEFS_DIR, or generates one first.
    Saves blog.md (and brief.md if newly generated) to OUTPUT_DIR/{slug}-{date}/.

    \b
    Examples:
      brief blog "ai sales roleplay"
      brief blog "sales coaching" --briefs-dir ./briefs
    """
    from agents.blog_agent import generate_blog, save_blog

    slug = _keyword_to_slug(keyword)
    run_dir = _make_run_dir(slug, Path(output_dir))

    brief_path = _find_latest_brief(slug, Path(briefs_dir))
    if brief_path:
        console.print(f"[dim]Using existing brief:[/dim] {brief_path}")
        brief_content = brief_path.read_text(encoding="utf-8")
    else:
        console.print(f"[yellow]No brief found for '{keyword}' — generating one first...[/yellow]")
        brief_content = generate_brief(keyword, "general audience", "blog post", 1500, "gemini-2.0-flash")
        brief_out = run_dir / "brief.md"
        brief_out.write_text(brief_content, encoding="utf-8")
        console.print(f"  [green]Brief saved:[/green] {brief_out}")

    console.print(Panel(
        f"[bold]Keyword:[/bold] {keyword}\n"
        f"[bold]Model:[/bold] gemini-2.5-pro\n"
        f"[bold]Output:[/bold] {run_dir}",
        title="[cyan]Blog Agent[/cyan]",
        border_style="cyan",
    ))

    blog_content = generate_blog(brief_content)
    path = save_blog(blog_content, slug, run_dir)
    console.print(f"\n[green]Blog saved:[/green] {path}")


@cli.command()
@click.argument("keyword")
@click.option("--output-dir", "-o", default="./output", show_default=True,
              help="Root directory to search for existing blog files.")
def banner(keyword, output_dir):
    """Generate an SVG banner from an existing blog post for KEYWORD.

    Requires a blog.md already generated by `brief blog`. Saves banner.svg
    to the same run directory as the blog.

    \b
    Examples:
      brief banner "ai sales roleplay"
    """
    from agents.banner_agent import extract_frontmatter, generate_banner, save_banner

    slug = _keyword_to_slug(keyword)
    blog_path, run_dir = _find_latest_blog(slug, Path(output_dir))

    if not blog_path:
        console.print(
            f"[red]No blog found for '{keyword}'.[/red] "
            f"Run [bold]brief blog \"{keyword}\"[/bold] first."
        )
        raise SystemExit(1)

    console.print(f"[dim]Using blog:[/dim] {blog_path}")
    blog_content = blog_path.read_text(encoding="utf-8")
    fm = extract_frontmatter(blog_content)

    blog_title = fm.get("title", keyword)
    primary_keyword = fm.get("primary_keyword", keyword)
    # Derive a short label tag from the primary keyword (first 3 words max)
    label_tag = " ".join(primary_keyword.split()[:3]).title()

    console.print(Panel(
        f"[bold]Title:[/bold] {blog_title}\n"
        f"[bold]Keyword:[/bold] {primary_keyword}\n"
        f"[bold]Label:[/bold] {label_tag}\n"
        f"[bold]Model:[/bold] gemini-2.5-pro\n"
        f"[bold]Output:[/bold] {run_dir}",
        title="[cyan]Banner Agent[/cyan]",
        border_style="cyan",
    ))

    svg_content = generate_banner(blog_title, primary_keyword, label_tag)
    path = save_banner(svg_content, run_dir)
    console.print(f"\n[green]Banner saved:[/green] {path}")


@cli.command()
@click.argument("keyword")
@click.option("--output-dir", "-o", default="./output", show_default=True,
              help="Root directory for all output files.")
def full(keyword, output_dir):
    """Run the full pipeline for KEYWORD: brief → blog → banner.

    Saves brief.md, blog.md, and banner.svg to OUTPUT_DIR/{slug}-{date}/.

    \b
    Examples:
      brief full "ai sales roleplay"
      brief full "sales coaching" --output-dir ./campaigns
    """
    from agents.blog_agent import generate_blog, save_blog
    from agents.banner_agent import extract_frontmatter, generate_banner, save_banner

    slug = _keyword_to_slug(keyword)
    run_dir = _make_run_dir(slug, Path(output_dir))

    console.print(Panel(
        f"[bold]Keyword:[/bold] {keyword}\n"
        f"[bold]Pipeline:[/bold] brief (gemini-2.0-flash) → blog (gemini-2.5-pro) → banner (gemini-2.5-pro)\n"
        f"[bold]Output:[/bold] {run_dir}",
        title="[cyan]Full Pipeline[/cyan]",
        border_style="cyan",
    ))

    # Step 1: Brief — reuse existing if found
    console.print("\n[bold][1/3] Brief...[/bold]")
    existing_brief = _find_latest_brief(slug, Path("./briefs"))
    if existing_brief:
        console.print(f"  [dim]Using existing brief:[/dim] {existing_brief}")
        brief_content = existing_brief.read_text(encoding="utf-8")
        brief_path = run_dir / "brief.md"
        brief_path.write_text(brief_content, encoding="utf-8")
        console.print(f"  [green]Copied:[/green] {brief_path}")
    else:
        brief_content = generate_brief(keyword, "general audience", "blog post", 1500, "gemini-2.0-flash")
        brief_path = run_dir / "brief.md"
        brief_path.write_text(brief_content, encoding="utf-8")
        console.print(f"  [green]Saved:[/green] {brief_path}")

    # Step 2: Blog
    console.print("\n[bold][2/3] Generating blog post...[/bold]")
    blog_content = generate_blog(brief_content)
    blog_path = save_blog(blog_content, slug, run_dir)
    console.print(f"  [green]Saved:[/green] {blog_path}")

    # Step 3: Banner
    console.print("\n[bold][3/3] Generating SVG banner...[/bold]")
    fm = extract_frontmatter(blog_content)
    blog_title = fm.get("title", keyword)
    primary_keyword = fm.get("primary_keyword", keyword)
    label_tag = " ".join(primary_keyword.split()[:3]).title()

    svg_content = generate_banner(blog_title, primary_keyword, label_tag)
    banner_path = save_banner(svg_content, run_dir)
    console.print(f"  [green]Saved:[/green] {banner_path}")

    console.print(f"\n[bold green]Done.[/bold green] All files saved to {run_dir}")


if __name__ == "__main__":
    cli()
