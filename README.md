# SEO Brief Generator

A CLI tool that generates detailed SEO content briefs powered by [Groq](https://groq.com/).

## Features

- Generates structured briefs covering title/meta, keyword strategy, content outline, on-page SEO checklist, and more
- Multiple content types: blog post, landing page, product page, guide, listicle, comparison
- Save briefs as Markdown files
- JSON output mode for pipeline integration
- Renders output with rich formatting in the terminal

## Requirements

- Python 3.9+
- A [Groq API key](https://console.groq.com/)

## Installation

```bash
git clone https://github.com/ishaR025/seo-brief.git
cd seo-brief
pip install -e .
```

## Setup

Copy `.env.example` to `.env` and add your Groq API key:

```bash
cp .env.example .env
# then edit .env and set GROQ_API_KEY=your_key_here
```

## Usage

```bash
# Basic usage
brief generate "content marketing strategy"

# Specify content type and word count
brief generate "best crm software" --type comparison --words 2500

# Target a specific audience and save to file
brief generate "how to start a podcast" --audience "beginner entrepreneurs" --save

# Output as JSON
brief generate "python tutorials" --json

# Save to a custom directory
brief generate "remote work tools" --save --output-dir ./my-briefs
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--audience`, `-a` | `general audience` | Target audience |
| `--type` | `blog post` | Content type (`blog post`, `landing page`, `product page`, `guide`, `listicle`, `comparison`) |
| `--words`, `-w` | `1500` | Target word count |
| `--model`, `-m` | `llama-3.3-70b-versatile` | Groq model to use |
| `--save`, `-s` | off | Save brief as a Markdown file |
| `--output-dir`, `-o` | `./briefs` | Directory to save briefs |
| `--json` | off | Output metadata + brief as JSON |

### List available models

```bash
brief models
```

## Brief Structure

Each generated brief includes:

1. **Overview** — search intent, content goal, difficulty estimate
2. **Title & Meta** — title tag options, meta description, URL slug
3. **Keyword Strategy** — primary keyword guidance, LSI keywords, long-tail variations
4. **Content Outline** — H1/H2/H3 structure with section notes
5. **Competitor Insights** — common angles, content gaps, unique value propositions
6. **On-Page SEO Checklist** — internal linking, image alt text, schema markup
7. **Writing Guidelines** — tone, reading level, key points
8. **CTAs & Conversion** — primary CTA and engagement hooks
