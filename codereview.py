#!/usr/bin/env python3
"""
CodeReview - AI-powered code review CLI tool
Usage: CodeReview [-branchname] [-o file]
"""

import sys
import csv
import subprocess
from pathlib import Path


REVIEW_PROMPT = """\
You are an expert code reviewer. Review the following git diff from \
branch '{current_branch}' targeting '{target_branch}'.

Provide a thorough code review covering:
1. **Summary** - Brief overview of the changes
2. **Potential Issues** - Bugs, logic errors, or security concerns
3. **Code Quality** - Readability, maintainability, naming conventions
4. **Performance** - Any performance concerns
5. **Suggestions** - Specific improvements with examples where helpful
6. **Verdict** - APPROVE / REQUEST CHANGES / NEEDS DISCUSSION

Git Diff:
```diff
{diff}
```"""


# ── git helpers ──────────────────────────────────────────────────────────────

def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"git error: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def get_current_branch() -> str:
    return _git("rev-parse", "--abbrev-ref", "HEAD")


_EXCLUDED_FILES = [
    "package-lock.json",  # npm
    "yarn.lock",          # Yarn
    "pnpm-lock.yaml",     # pnpm
    "bun.lockb",          # Bun
    "Pipfile.lock",       # Pipenv
    "poetry.lock",        # Poetry
    "uv.lock",            # uv
    "Gemfile.lock",       # Bundler
    "composer.lock",      # Composer
    "Cargo.lock",         # Cargo
    "go.sum",             # Go modules
    "Package.resolved",   # Swift PM
    "Podfile.lock",       # CocoaPods
    "pubspec.lock",       # Flutter/Dart
    "packages.lock.json", # NuGet
    "mix.lock",           # Elixir
]


def get_diff(target_branch: str) -> str:
    excludes = [f":(exclude){f}" for f in _EXCLUDED_FILES]
    return _git("diff", f"{target_branch}...HEAD", "--", ".", *excludes)


# ── config loading ────────────────────────────────────────────────────────────

def load_configs(csv_path: Path) -> list[dict]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    # strip whitespace from all values
    return [{k: v.strip() for k, v in row.items()} for row in rows]


def select_config(configs: list[dict]) -> dict:
    print("\nAvailable LLMs:")
    for i, c in enumerate(configs):
        tag = "  (default)" if i == 0 else ""
        print(f"  {i + 1}. {c['name']} — {c['model'] or 'server default'}{tag}")

    while True:
        raw = input(f"\nSelect LLM [1-{len(configs)}] or press Enter for default: ").strip()
        if not raw:
            return configs[0]
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(configs):
                return configs[idx]
        except ValueError:
            pass
        print("  Invalid selection, try again.")


# ── LLM backends ─────────────────────────────────────────────────────────────

def _stream_anthropic(config: dict, prompt: str, out=None) -> None:
    try:
        import anthropic
    except ImportError:
        print("Missing dependency: pip install anthropic", file=sys.stderr)
        sys.exit(1)

    kwargs: dict = {"api_key": config["api_key"]}
    if config.get("endpoint"):
        kwargs["base_url"] = config["endpoint"]

    client = anthropic.Anthropic(**kwargs)

    with client.messages.stream(
        model=config["model"],
        max_tokens=8096,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            if out:
                out.write(text)


def _stream_openai_compatible(config: dict, prompt: str, out=None) -> None:
    try:
        from openai import OpenAI
    except ImportError:
        print("Missing dependency: pip install openai", file=sys.stderr)
        sys.exit(1)

    api_key = config.get("api_key") or "no-key"
    endpoint = config.get("endpoint") or None
    model = config.get("model") or None

    client_kwargs: dict = {"api_key": api_key}
    if endpoint:
        client_kwargs["base_url"] = endpoint

    client = OpenAI(**client_kwargs)

    request: dict = {
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 8096,
        "stream": True,
    }
    if model:
        request["model"] = model

    stream = client.chat.completions.create(**request)
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            print(delta, end="", flush=True)
            if out:
                out.write(delta)


# ── entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    target_branch = "develop"
    output_file = None

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg in ("-h", "--help"):
            print(
                "Usage: CodeReview [-branchname] [-o file]\n\n"
                "  -branchname   Branch to diff against (default: develop)\n"
                "  -o file       Save review output to a file\n\n"
                "Examples:\n"
                "  CodeReview                        # diff against develop\n"
                "  CodeReview -main                  # diff against main\n"
                "  CodeReview -o review.md           # save output to file\n"
                "  CodeReview -main -o review.md     # both\n"
            )
            sys.exit(0)
        elif arg == "-o":
            if i + 1 >= len(sys.argv):
                print("Error: -o requires a filename.", file=sys.stderr)
                sys.exit(1)
            output_file = sys.argv[i + 1]
            i += 2
        elif arg.startswith("-") and len(arg) > 1:
            target_branch = arg[1:]
            i += 1
        else:
            print(f"Unknown argument: {arg}\nUse -h for help.", file=sys.stderr)
            sys.exit(1)

    script_dir = Path(__file__).parent
    csv_path = script_dir / "llm_config.csv"

    if not csv_path.exists():
        print(
            f"Config not found: {csv_path}\n"
            "Fill in llm_config.csv with your LLM settings.",
            file=sys.stderr,
        )
        sys.exit(1)

    configs = load_configs(csv_path)
    if not configs:
        print("No LLM entries found in llm_config.csv.", file=sys.stderr)
        sys.exit(1)

    current_branch = get_current_branch()
    print(f"Branch : {current_branch}  →  {target_branch}")

    diff = get_diff(target_branch)
    if not diff:
        print("No differences found — branches are identical.")
        sys.exit(0)

    line_count = diff.count("\n")
    print(f"Diff   : {line_count} lines")
    if line_count > 2000:
        print(
            f"Warning: large diff ({line_count} lines) — "
            "content may be truncated by the model's token limit."
        )

    config = select_config(configs)
    print(f"\nUsing  : {config['name']} ({config['model'] or 'server default'})")
    print("Generating review...\n")

    prompt = REVIEW_PROMPT.format(
        current_branch=current_branch,
        target_branch=target_branch,
        diff=diff,
    )

    header = "=" * 60 + "\nCODE REVIEW\n" + "=" * 60 + "\n"
    footer = "\n\n" + "=" * 60

    out = open(output_file, "w", encoding="utf-8") if output_file else None
    try:
        print(header)
        if out:
            out.write(header + "\n")

        llm_type = config.get("type", "").lower()
        if llm_type == "anthropic":
            _stream_anthropic(config, prompt, out)
        elif llm_type in ("llamacpp", "openai", "openai_compatible"):
            _stream_openai_compatible(config, prompt, out)
        else:
            print(
                f"Unknown LLM type '{llm_type}'.\n"
                "Supported: anthropic, llamacpp, openai_compatible",
                file=sys.stderr,
            )
            sys.exit(1)

        print(footer)
        if out:
            out.write(footer + "\n")
    finally:
        if out:
            out.close()
            print(f"\nReview saved to {output_file}")


if __name__ == "__main__":
    main()
