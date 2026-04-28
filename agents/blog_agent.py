"""Blog generation agent — produces a publish-ready markdown blog post from an SEO brief."""

from pathlib import Path

from langfuse import observe

from agents.llm import gemini_generate

BLOG_MODEL = "gemini-2.5-pro"

BLOG_SYSTEM_PROMPT = """You are a senior B2B content writer who specialises in SaaS, AI, and sales technology.
You write blogs that rank AND convert — not keyword-stuffed SEO filler, but opinionated,
useful content that a practitioner would actually read.

Your writing principles:
- Lead with a sharp hook in the first 2 sentences. No "In today's landscape..." openers.
- Every H2 should make a distinct point, not restate the title in different words.
- Use short paragraphs (2–4 lines max). No walls of text.
- Include at least one concrete example or stat per major section.
- End with a specific, actionable CTA — not "learn more", something the reader can do right now.
- Avoid: "game-changing", "revolutionary", "leverage", "seamlessly", "robust", "cutting-edge".
- Write as if explaining to a smart peer, not a beginner. Assume they know their domain.
- Tone: confident, direct, slightly opinionated. Think "experienced practitioner" not "content marketer"."""

BLOG_USER_TEMPLATE = """Using the SEO brief below, write a complete blog post.

---SEO BRIEF---
{brief_content}
---END BRIEF---

OUTPUT REQUIREMENTS:

**Format:** Markdown
**Length:** 1,200–1,600 words (not counting frontmatter)
**Structure:**

---
title: {suggested title — H1, includes primary keyword, under 60 chars}
meta_description: {150–160 chars, includes primary keyword, written for CTR}
primary_keyword: {from brief}
secondary_keywords: {comma-separated from brief}
word_count: {actual count}
reading_time: {X min read}
---

# {Title}

{Hook paragraph — 2–3 sentences, opens with a specific problem or provocative claim}

## {H2 — first major section}
{Content}

## {H2 — second major section}
{Content}

## {H2 — third major section}
{Content}

## {H2 — fourth major section (optional, only if brief supports it)}
{Content}

## {Final H2 — practical takeaway or "what to do next"}
{Content}

{CTA paragraph — 2–3 sentences, specific action, not generic}

RULES:
- Use the exact primary keyword naturally in: title, first 100 words, at least 2 H2s, meta description.
- Use secondary keywords in body copy — do not force them into headings.
- No keyword stuffing. Read naturally first, SEO second.
- Do not invent statistics. If a stat is needed, write "[STAT NEEDED: X]" as a placeholder.
- Do not add a "Conclusion" heading — end with the CTA section instead.
- Output only the markdown. No preamble, no commentary."""


@observe()
def generate_blog(brief_content: str) -> str:
    user_prompt = BLOG_USER_TEMPLATE.replace("{brief_content}", brief_content)
    return gemini_generate(
        model=BLOG_MODEL,
        system_prompt=BLOG_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=4096,
        task_label="Writing blog post...",
    )


def save_blog(content: str, slug: str, output_dir: Path) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "blog.md"
    path.write_text(content, encoding="utf-8")
    return path
