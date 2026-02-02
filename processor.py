"""API interaction and processing logic for transcript cleaner."""

import json
import os
import time
from pathlib import Path
from typing import List, Optional, Tuple, Callable

import anthropic
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from prompts import (
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
    USER_PROMPT_WITH_CONTEXT_TEMPLATE
)
from chunker import get_overlap_context


class TranscriptProcessor:
    """Processes transcript chunks using the Anthropic API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        checkpoint_file: Optional[str] = None
    ):
        """
        Initialize the processor.

        Args:
            api_key: Anthropic API key. If None, uses ANTHROPIC_API_KEY env var.
            model: Model to use for processing.
            checkpoint_file: Path to checkpoint file for resuming interrupted runs.
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.checkpoint_file = checkpoint_file
        self.temperature = 0.0

    def _create_user_prompt(self, text: str, context: str = "") -> str:
        """Create the user prompt with optional context."""
        if context:
            return USER_PROMPT_WITH_CONTEXT_TEMPLATE.format(
                context=context,
                text=text
            )
        return USER_PROMPT_TEMPLATE.format(text=text)

    @retry(
        retry=retry_if_exception_type((
            anthropic.RateLimitError,
            anthropic.APIConnectionError,
            anthropic.InternalServerError
        )),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(5)
    )
    def _call_api(self, text: str, context: str = "") -> str:
        """
        Make an API call with retry logic.

        Args:
            text: Text to clean
            context: Optional context from previous chunk

        Returns:
            Cleaned text from the API
        """
        user_prompt = self._create_user_prompt(text, context)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=16000,
            temperature=self.temperature,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )

        return response.content[0].text

    def _load_checkpoint(self) -> Tuple[List[str], int]:
        """
        Load checkpoint if it exists.

        Returns:
            Tuple of (cleaned_chunks, next_index_to_process)
        """
        if not self.checkpoint_file or not os.path.exists(self.checkpoint_file):
            return [], 0

        with open(self.checkpoint_file, 'r') as f:
            data = json.load(f)
            return data.get('cleaned_chunks', []), data.get('next_index', 0)

    def _save_checkpoint(self, cleaned_chunks: List[str], next_index: int):
        """Save checkpoint to file."""
        if not self.checkpoint_file:
            return

        with open(self.checkpoint_file, 'w') as f:
            json.dump({
                'cleaned_chunks': cleaned_chunks,
                'next_index': next_index
            }, f)

    def process_chunks(
        self,
        chunks: List[Tuple[str, int, int]],
        verbose: bool = False,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        delay_between_calls: float = 1.0
    ) -> List[str]:
        """
        Process all chunks through the API.

        Args:
            chunks: List of (text, start, end) tuples
            verbose: Whether to print progress
            progress_callback: Optional callback(current, total) for progress
            delay_between_calls: Seconds to wait between API calls

        Returns:
            List of cleaned chunk texts
        """
        cleaned_chunks, start_index = self._load_checkpoint()

        if start_index > 0 and verbose:
            print(f"Resuming from checkpoint at chunk {start_index + 1}")

        total_chunks = len(chunks)

        for i in range(start_index, total_chunks):
            chunk_text, start_pos, end_pos = chunks[i]

            if verbose:
                print(f"Processing chunk {i + 1}/{total_chunks} "
                      f"(chars {start_pos}-{end_pos})...")

            if progress_callback:
                progress_callback(i + 1, total_chunks)

            # Get context from previous cleaned chunk
            context = get_overlap_context(chunks, cleaned_chunks, i)

            # Call the API
            cleaned_text = self._call_api(chunk_text, context)
            cleaned_chunks.append(cleaned_text)

            # Save checkpoint after each successful chunk
            self._save_checkpoint(cleaned_chunks, i + 1)

            # Delay between calls to avoid rate limits
            if i < total_chunks - 1:
                time.sleep(delay_between_calls)

        return cleaned_chunks

    def merge_chunks(self, cleaned_chunks: List[str]) -> str:
        """
        Merge cleaned chunks into final output.

        The chunks have overlap, so we need to handle potential duplicate
        content at boundaries. We use a simple approach: join with double
        newlines and let the paragraph structure handle it.

        Args:
            cleaned_chunks: List of cleaned text chunks

        Returns:
            Merged final text
        """
        if not cleaned_chunks:
            return ""

        if len(cleaned_chunks) == 1:
            return cleaned_chunks[0]

        # Join chunks with paragraph breaks
        # The overlap context helps ensure continuity, so simple joining works
        merged = "\n\n".join(cleaned_chunks)

        # Clean up any excessive newlines
        import re
        merged = re.sub(r'\n{3,}', '\n\n', merged)

        return merged.strip()
