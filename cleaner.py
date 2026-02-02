#!/usr/bin/env python3
"""
Transcript Cleaner CLI

Cleans YouTube auto-generated transcripts using Claude API.

Usage:
    python cleaner.py hp_transcript_full.txt -o hp_cleaned.txt --verbose
"""

import argparse
import os
import sys
from pathlib import Path

from chunker import preprocess_text, create_chunks
from processor import TranscriptProcessor


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Clean YouTube auto-generated transcripts using Claude API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python cleaner.py hp_transcript_full.txt -o hp_cleaned.txt --verbose
    python cleaner.py input.txt --api-key sk-ant-... --chunk-size 8000

Environment Variables:
    ANTHROPIC_API_KEY: Your Anthropic API key (if not using --api-key)
"""
    )

    parser.add_argument(
        "input_file",
        type=str,
        help="Path to the input transcript file"
    )

    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output file path (default: input_cleaned.txt)"
    )

    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Anthropic API key (or use ANTHROPIC_API_KEY env var)"
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=9000,
        help="Chunk size in characters (default: 9000)"
    )

    parser.add_argument(
        "--overlap",
        type=int,
        default=500,
        help="Overlap between chunks in characters (default: 500)"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print progress information"
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoint if available"
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between API calls in seconds (default: 1.0)"
    )

    return parser.parse_args()


def get_output_path(input_path: str, output_path: str = None) -> str:
    """Generate output path if not specified."""
    if output_path:
        return output_path

    input_p = Path(input_path)
    return str(input_p.parent / f"{input_p.stem}_cleaned{input_p.suffix}")


def get_checkpoint_path(input_path: str) -> str:
    """Generate checkpoint file path."""
    input_p = Path(input_path)
    return str(input_p.parent / f".{input_p.stem}_checkpoint.json")


def main():
    """Main entry point."""
    args = parse_args()

    # Validate input file
    if not os.path.exists(args.input_file):
        print(f"Error: Input file not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)

    # Check for API key
    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: No API key provided. Use --api-key or set ANTHROPIC_API_KEY",
              file=sys.stderr)
        sys.exit(1)

    # Determine output path
    output_path = get_output_path(args.input_file, args.output)

    # Checkpoint path for resuming
    checkpoint_path = get_checkpoint_path(args.input_file) if args.resume else None

    if args.verbose:
        print(f"Input:  {args.input_file}")
        print(f"Output: {output_path}")
        print(f"Chunk size: {args.chunk_size}, Overlap: {args.overlap}")
        print()

    # Read input file
    if args.verbose:
        print("Reading input file...")

    with open(args.input_file, 'r', encoding='utf-8') as f:
        raw_text = f.read()

    if args.verbose:
        print(f"Read {len(raw_text):,} characters")

    # Preprocess text
    if args.verbose:
        print("Preprocessing text...")

    processed_text = preprocess_text(raw_text)

    if args.verbose:
        print(f"Preprocessed to {len(processed_text):,} characters")

    # Create chunks
    if args.verbose:
        print("Creating chunks...")

    chunks = create_chunks(processed_text, args.chunk_size, args.overlap)

    if args.verbose:
        print(f"Created {len(chunks)} chunks")
        print()

    # Initialize processor
    processor = TranscriptProcessor(
        api_key=api_key,
        checkpoint_file=checkpoint_path
    )

    # Process chunks
    if args.verbose:
        print("Processing chunks with Claude API...")
        print("-" * 40)

    try:
        cleaned_chunks = processor.process_chunks(
            chunks,
            verbose=args.verbose,
            delay_between_calls=args.delay
        )
    except KeyboardInterrupt:
        print("\nInterrupted! Progress saved to checkpoint.", file=sys.stderr)
        if args.resume:
            print(f"Resume with: python cleaner.py {args.input_file} --resume",
                  file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        print("-" * 40)
        print("Merging chunks...")

    # Merge chunks
    final_text = processor.merge_chunks(cleaned_chunks)

    # Write output
    if args.verbose:
        print(f"Writing output to {output_path}...")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_text)

    if args.verbose:
        print(f"Done! Output: {len(final_text):,} characters")

    # Clean up checkpoint if successful
    if checkpoint_path and os.path.exists(checkpoint_path):
        os.remove(checkpoint_path)
        if args.verbose:
            print("Checkpoint cleaned up.")

    print(f"Transcript cleaned successfully: {output_path}")


if __name__ == "__main__":
    main()
