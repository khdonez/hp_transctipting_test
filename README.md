# Transcript Cleaner

A CLI tool that cleans YouTube auto-generated transcripts using Claude API.

## Features

- Fixes punctuation and capitalisation
- Corrects speech-to-text errors
- Converts to British English spelling
- Fixes proper nouns (especially Harry Potter names)
- Preserves verbal fillers ("um", "uh")
- Supports checkpointing for interrupted runs

## Installation

```bash
# Create virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate

# Or with uv
uv venv && source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Setup

Set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Or pass it directly with `--api-key`.

## Usage

```bash
# Basic usage
python cleaner.py hp_transcript_full.txt -o hp_cleaned.txt

# With progress output
python cleaner.py hp_transcript_full.txt -o hp_cleaned.txt --verbose

# Resume interrupted run
python cleaner.py hp_transcript_full.txt -o hp_cleaned.txt --resume --verbose
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `input_file` | Input transcript file | (required) |
| `-o, --output` | Output file path | `{input}_cleaned.txt` |
| `--api-key` | Anthropic API key | `$ANTHROPIC_API_KEY` |
| `--chunk-size` | Chunk size in characters | 9000 |
| `--overlap` | Overlap between chunks | 500 |
| `--delay` | Delay between API calls (seconds) | 1.0 |
| `--verbose, -v` | Print progress | off |
| `--resume` | Resume from checkpoint | off |

## How It Works

1. Preprocesses text (removes blank lines, normalises whitespace)
2. Splits into ~9000 character chunks with 500 char overlap
3. Sends each chunk to Claude with context from the previous chunk
4. Merges cleaned chunks into final output

## Cost Estimate

For a ~100KB transcript (~11 chunks): approximately $0.50
