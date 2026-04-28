"""Banner generation agent — produces a 1200×630 SVG blog banner from blog frontmatter."""

import re
from pathlib import Path

from langfuse import observe

from agents.llm import gemini_generate

BANNER_MODEL = "gemini-2.5-pro"

BANNER_SYSTEM_PROMPT = """You are a senior product designer who specialises in SaaS brand assets.
You produce SVG banners with a minimalist, modern aesthetic — white backgrounds,
violet/purple accents, clean geometric shapes. Your output is always valid,
self-contained SVG that renders perfectly in a browser with no external dependencies.

SVG rules you always follow:
- All SVG must be valid XML. Close every tag.
- Never use <image> tags or external hrefs.
- Never use fonts that require @import or external CDN. Use system-ui stack only.
- All text must be inside <text> elements with explicit x, y, font-family, font-size,
  fill attributes. Never rely on CSS classes for critical text rendering.
- Geometric shapes only — no path-based illustrations or icon-style art.
- Keep the file clean: group related elements with <g> and descriptive id attributes.
- Output only raw SVG. No markdown fences, no commentary, no preamble."""

BANNER_USER_TEMPLATE = """Generate a 1200×630px SVG blog banner for the following:

Blog title: {blog_title}
Primary keyword / topic domain: {primary_keyword}
Label tag (short category, 1–3 words): {label_tag}

DESIGN REQUIREMENTS:

Canvas: viewBox="0 0 1200 630", width="1200", height="630"

Palette — use exactly these hex values:
  background:    #FFFFFF
  primary:       #7C3AED
  primary-light: #EDE9FE
  primary-dark:  #5B21B6
  text-primary:  #1E1B4B
  text-secondary:#6B7280
  accent:        #A78BFA

Layout zones:
  LEFT ZONE  (x: 60–780):  label tag + title text + optional 1-line descriptor
  RIGHT ZONE (x: 800–1160): geometric composition only

Text rules:
  - Label tag: 13px, #7C3AED, font-weight 600, letter-spacing 2px, UPPERCASE
  - Thin 2px horizontal rule below label in #A78BFA, width ~120px
  - Title: font-weight 700, fill #1E1B4B
      · If title ≤ 40 chars → font-size 52px, single line
      · If title 41–65 chars → font-size 44px, split into 2 <text> lines manually
      · If title > 65 chars → font-size 36px, split into 3 <text> lines manually
      · Line height: 1.25 × font-size
  - No subtitle or descriptor text unless the title is very short (< 25 chars)

Geometric composition (right zone — be creative within these rules):
  - 1 large low-opacity circle or rounded rectangle as background anchor
      · fill: #EDE9FE, opacity: 0.6–0.8, size: 280–380px
  - 1–2 smaller filled circles in #7C3AED or #A78BFA, varying opacity
  - 1–2 thin lines or small rectangles as detail elements
  - Optionally: 1 medium ring (circle with stroke, no fill) in #A78BFA
  - Geometry should feel balanced and intentional, not scattered
  - Nothing in the geometry should look like a logo, icon, or illustration

White margin: 60px all sides. No element bleeds to edge except full-bleed background rect.

Output: raw SVG only, starting with <svg and ending with </svg>.
No markdown. No explanation. No comments inside the SVG."""

_STRICT_PREFIX = "Output only valid SVG XML. Start your response with <svg. Do not add any text before or after.\n\n"


def extract_frontmatter(blog_md: str) -> dict:
    match = re.search(r"^---\n(.*?)\n---", blog_md, re.DOTALL)
    if not match:
        return {}
    fields = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fields[k.strip()] = v.strip()
    return fields


def validate_svg(svg_content: str) -> bool:
    s = svg_content.strip()
    checks = [
        s.startswith("<svg"),
        s.endswith("</svg>"),
        "href=" not in s or "data:" in s,  # no external refs
        "@import" not in s,                # no external fonts
    ]
    return all(checks)


def _strip_markdown_fences(text: str) -> str:
    """Strip ```svg ... ``` or ``` ... ``` wrappers the model sometimes adds."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


@observe()
def generate_banner(blog_title: str, primary_keyword: str, label_tag: str) -> str:
    user_prompt = (
        BANNER_USER_TEMPLATE
        .replace("{blog_title}", blog_title)
        .replace("{primary_keyword}", primary_keyword)
        .replace("{label_tag}", label_tag)
    )

    svg = gemini_generate(
        model=BANNER_MODEL,
        system_prompt=BANNER_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=8192,
        task_label="Generating SVG banner...",
    )
    svg = _strip_markdown_fences(svg)

    if not validate_svg(svg):
        # Retry once with a stricter prefix
        svg = gemini_generate(
            model=BANNER_MODEL,
            system_prompt=BANNER_SYSTEM_PROMPT,
            user_prompt=_STRICT_PREFIX + user_prompt,
            max_tokens=8192,
            task_label="Retrying SVG banner (strict mode)...",
        )
        svg = _strip_markdown_fences(svg)
        if not validate_svg(svg):
            raise ValueError("Banner SVG failed validation after retry. Check model output.")

    return svg


def save_banner(content: str, output_dir: Path) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "banner.svg"
    path.write_text(content, encoding="utf-8")
    return path
