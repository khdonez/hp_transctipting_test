"""Text preprocessing and chunking for transcript cleaner."""

import re
from typing import List, Tuple


def preprocess_text(text: str) -> str:
    """
    Preprocess transcript text by normalizing whitespace.

    Args:
        text: Raw transcript text

    Returns:
        Preprocessed text with normalized whitespace
    """
    # Remove blank lines and normalize whitespace
    lines = text.splitlines()
    non_empty_lines = [line.strip() for line in lines if line.strip()]

    # Join with single spaces
    text = ' '.join(non_empty_lines)

    # Normalize multiple spaces to single space
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def find_word_boundary(text: str, position: int, direction: str = 'backward') -> int:
    """
    Find the nearest word boundary from a position.

    Args:
        text: The text to search
        position: Starting position
        direction: 'backward' or 'forward'

    Returns:
        Position of the nearest word boundary (space)
    """
    if direction == 'backward':
        # Search backward for a space
        while position > 0 and text[position] != ' ':
            position -= 1
        return position
    else:
        # Search forward for a space
        while position < len(text) and text[position] != ' ':
            position += 1
        return position


def create_chunks(text: str, chunk_size: int = 9000, overlap: int = 500) -> List[Tuple[str, int, int]]:
    """
    Split text into overlapping chunks at word boundaries.

    Args:
        text: Preprocessed text to chunk
        chunk_size: Target size of each chunk in characters
        overlap: Number of characters to overlap between chunks

    Returns:
        List of tuples: (chunk_text, start_position, end_position)
    """
    if len(text) <= chunk_size:
        return [(text, 0, len(text))]

    chunks = []
    position = 0

    while position < len(text):
        # Calculate end position for this chunk
        end_pos = min(position + chunk_size, len(text))

        # If we're not at the end, find a word boundary
        if end_pos < len(text):
            end_pos = find_word_boundary(text, end_pos, 'backward')
            # Make sure we made progress
            if end_pos <= position:
                end_pos = find_word_boundary(text, position + chunk_size, 'forward')

        # Extract chunk
        chunk_text = text[position:end_pos].strip()

        if chunk_text:
            chunks.append((chunk_text, position, end_pos))

        # Move position for next chunk, accounting for overlap
        # The overlap ensures context continuity
        if end_pos >= len(text):
            break

        # Next chunk starts (chunk_size - overlap) characters from current start
        position = end_pos - overlap

        # Make sure we're at a word boundary
        if position > 0:
            position = find_word_boundary(text, position, 'forward')
            if text[position] == ' ':
                position += 1

    return chunks


def get_overlap_context(chunks: List[Tuple[str, int, int]],
                        cleaned_chunks: List[str],
                        current_index: int,
                        context_chars: int = 500) -> str:
    """
    Get the end of the previous cleaned chunk for context.

    Args:
        chunks: List of original chunk tuples
        cleaned_chunks: List of cleaned chunk texts
        current_index: Index of current chunk being processed
        context_chars: Number of characters of context to include

    Returns:
        Context string from previous chunk, or empty string if first chunk
    """
    if current_index == 0 or not cleaned_chunks:
        return ""

    previous_cleaned = cleaned_chunks[-1]

    # Get the last context_chars characters
    if len(previous_cleaned) <= context_chars:
        return previous_cleaned

    # Find a good break point (sentence or paragraph)
    context = previous_cleaned[-context_chars:]

    # Try to start at a sentence boundary
    sentence_ends = ['.', '!', '?']
    for i, char in enumerate(context):
        if char in sentence_ends and i < len(context) - 1:
            # Start after this sentence
            return context[i+1:].strip()

    # Fall back to word boundary
    space_pos = context.find(' ')
    if space_pos != -1:
        return context[space_pos+1:]

    return context
