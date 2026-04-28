"""Shared LLM primitives — Gemini and Groq clients, retry wrappers, Langfuse tracing."""

import os
import re
import sys
import time

from dotenv import load_dotenv
from google import genai as google_genai
from google.genai import types as genai_types
from google.genai.errors import ClientError as GeminiClientError
from groq import Groq, RateLimitError
from langfuse import observe, get_client as get_langfuse_client
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

load_dotenv()

_console = Console()


def _is_gemini(model: str) -> bool:
    return model.startswith("gemini")


def _parse_retry_after(error_msg: str) -> int:
    m = re.search(r"try again in (\d+)m\s*([\d.]+)s", error_msg)
    if m:
        return int(m.group(1)) * 60 + int(float(m.group(2))) + 5
    m = re.search(r"try again in ([\d.]+)s", error_msg)
    if m:
        return int(float(m.group(1))) + 5
    return 60


def _get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        _console.print("[red]Error:[/red] GEMINI_API_KEY not set. Add it to .env or export it.")
        sys.exit(1)
    return google_genai.Client(api_key=api_key)


def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        _console.print("[red]Error:[/red] GROQ_API_KEY not set. Add it to .env or export it.")
        sys.exit(1)
    return Groq(api_key=api_key)


@observe(as_type="generation")
def _call_gemini(model: str, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    client = _get_gemini_client()
    response = client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=genai_types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.7,
            max_output_tokens=max_tokens,
        ),
    )
    usage = {
        "input": getattr(response.usage_metadata, "prompt_token_count", 0) or 0,
        "output": getattr(response.usage_metadata, "candidates_token_count", 0) or 0,
    }
    thoughts = getattr(response.usage_metadata, "thoughts_token_count", None)
    if thoughts:
        usage["cache_read"] = thoughts  # thinking tokens tracked as cache_read in Langfuse
    get_langfuse_client().update_current_generation(model=model, usage_details=usage)
    return response.text


@observe(as_type="generation")
def _call_groq(client, model: str, messages: list, max_tokens: int) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.7,
        max_tokens=max_tokens,
    )
    get_langfuse_client().update_current_generation(
        model=model,
        usage_details={
            "input": response.usage.prompt_tokens,
            "output": response.usage.completion_tokens,
        },
    )
    return response.choices[0].message.content


def gemini_generate(
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    task_label: str,
    max_retries: int = 5,
) -> str:
    for attempt in range(max_retries):
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
                console=_console,
            ) as progress:
                progress.add_task(task_label, total=None)
                return _call_gemini(model, system_prompt, user_prompt, max_tokens)
        except GeminiClientError as e:
            if e.code != 429 or attempt == max_retries - 1:
                raise
            wait = _parse_retry_after(str(e))
            _console.print(
                f"  [yellow]Rate limited — waiting {wait}s before retry "
                f"{attempt + 1}/{max_retries - 1}...[/yellow]"
            )
            time.sleep(wait)


def groq_generate(
    client,
    model: str,
    messages: list,
    max_tokens: int,
    task_label: str,
    max_retries: int = 5,
) -> str:
    for attempt in range(max_retries):
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
                console=_console,
            ) as progress:
                progress.add_task(task_label, total=None)
                return _call_groq(client, model, messages, max_tokens)
        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise
            wait = _parse_retry_after(str(e))
            _console.print(
                f"  [yellow]Rate limited — waiting {wait}s before retry "
                f"{attempt + 1}/{max_retries - 1}...[/yellow]"
            )
            time.sleep(wait)
