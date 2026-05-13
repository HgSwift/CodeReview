# CodeReview

AI-powered code review CLI tool. Diffs your current branch against a target branch and streams a structured review from an LLM.

## Requirements

- Python 3.10+
- Git

## Installation

1. Clone this repo and navigate into it:

   ```bash
   git clone https://github.com/HgSwift/CodeReview.git
   cd CodeReview
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

   > You only need `anthropic` or `openai` depending on which backend(s) you use — installing both is fine.

3. Create `llm_config.csv` in the CodeReview folder and fill in your API key(s):

   ```csv
   name,type,model,api_key,endpoint
   Claude Sonnet 4.6,anthropic,claude-sonnet-4-6,YOUR_ANTHROPIC_API_KEY,
   GPT-4o,openai,gpt-4o,YOUR_OPENAI_API_KEY,
   Local llama.cpp,llamacpp,,no-key,http://localhost:8080/v1
   ```

   Replace `YOUR_ANTHROPIC_API_KEY` (or `YOUR_OPENAI_API_KEY`) with your actual key. See [Configuration](#configuration) for all column details.

   > `llm_config.csv` is gitignored so your keys are never accidentally committed.

## Adding to PATH (run from anywhere)

Once on your PATH you can type `CodeReview` from inside any git repo without specifying the full script path.

### Windows

Add the folder containing `CodeReview.bat` to your user PATH:

**Option A — GUI**
1. Search for **"Edit the system environment variables"** in the Start menu
2. Click **Environment Variables**
3. Under **User variables**, select **Path** and click **Edit**
4. Click **New** and paste the full path to the CodeReview folder (e.g. `C:\Tools\CodeReview`)
5. Click **OK** on all dialogs, then open a new terminal

**Option B — PowerShell (one-liner)**
```powershell
[Environment]::SetEnvironmentVariable(
    "Path",
    [Environment]::GetEnvironmentVariable("Path", "User") + ";C:\Tools\CodeReview",
    "User"
)
```
Replace `C:\Tools\CodeReview` with your actual clone path. Open a new terminal after running this.

> The `.bat` launcher is picked up automatically by `cmd` and PowerShell once the folder is on PATH. If you use PowerShell exclusively and want tab-completion, you can also add this to your `$PROFILE`:
> ```powershell
> function CodeReview { & "C:\Tools\CodeReview\CodeReview.ps1" @args }
> ```

### macOS / Linux

Make the script executable and symlink it somewhere already on your PATH:

```bash
chmod +x /path/to/CodeReview/codereview.py
ln -s /path/to/CodeReview/codereview.py /usr/local/bin/CodeReview
```

Or add a shell function to your `~/.bashrc` / `~/.zshrc`:

```bash
CodeReview() { python "/path/to/CodeReview/codereview.py" "$@"; }
```

Reload your shell (`source ~/.bashrc`) and you're done.

---

## Usage

Run from within any git repository:

```bash
# Review against the default target branch (develop)
CodeReview

# Review against a specific branch
CodeReview -main
CodeReview -feature/my-feature

# Help
CodeReview -h
```

If multiple LLMs are configured you'll be prompted to pick one. The first entry in `llm_config.csv` is the default (press Enter to select it).

## Configuration

`llm_config.csv` must live in the same directory as `codereview.py`. The file uses the following columns:

| Column | Description |
|---|---|
| `name` | Display name shown in the selection menu |
| `type` | LLM backend: `anthropic`, `openai`, `openai_compatible`, or `llamacpp` |
| `model` | Model ID to request. Leave blank to use the server's default (local servers only). |
| `api_key` | API key for the service. Use any non-empty string (e.g. `no-key`) for local servers that don't require auth. |
| `endpoint` | Optional. Override the default API base URL. Required for local servers. Leave blank for official cloud APIs. |

### Example `llm_config.csv`

```csv
name,type,model,api_key,endpoint
Claude Sonnet 4.6,anthropic,claude-sonnet-4-6,YOUR_ANTHROPIC_API_KEY,
GPT-4o,openai,gpt-4o,YOUR_OPENAI_API_KEY,
Local llama.cpp,llamacpp,,no-key,http://localhost:8080/v1
```

- **Anthropic** — get your API key at [console.anthropic.com](https://console.anthropic.com)
- **OpenAI** — get your API key at [platform.openai.com](https://platform.openai.com)
- **Local servers** — set `endpoint` to your server's OpenAI-compatible base URL (e.g. llama.cpp server, Ollama with `OLLAMA_ORIGINS=*`)

## Review Output

Each review covers:

1. **Summary** — what the diff does
2. **Potential Issues** — bugs, logic errors, security concerns
3. **Code Quality** — readability, naming, maintainability
4. **Performance** — any performance concerns
5. **Suggestions** — specific improvements with examples
6. **Verdict** — `APPROVE` / `REQUEST CHANGES` / `NEEDS DISCUSSION`

## Notes

- Diffs larger than 2000 lines will trigger a warning. Very large diffs may be truncated by the model's context window.
- The tool reads the diff between your current branch and the target branch using `git diff <target>...HEAD`. Make sure the target branch exists locally.

## License

MIT
