"""
Turns a list of {'page': int, 'text': str} page records into overlapping
token-window chunks, each tagged with the page range it came from so the
chatbot can cite "p. 12" style sources like the paper's "Related Link"
feature.
"""
import tiktoken

_ENC = None


def _enc():
    global _ENC
    if _ENC is None:
        _ENC = tiktoken.get_encoding("cl100k_base")
    return _ENC


def chunk_document(pages: list[dict], source_document: str,
                    chunk_size: int, overlap: int) -> list[dict]:
    if not pages:
        return []

    full_text = ""
    page_offsets = []  # (page_num, char_start)
    for p in pages:
        page_offsets.append((p["page"], len(full_text)))
        full_text += p["text"] + "\n\n"

    tokens = _enc().encode(full_text)
    if not tokens:
        return []

    def page_for_char_offset(char_offset: int) -> int:
        page_num = page_offsets[0][0]
        for pn, start in page_offsets:
            if start <= char_offset:
                page_num = pn
            else:
                break
        return page_num

    chunks = []
    step = max(chunk_size - overlap, 1)
    idx = 0
    chunk_index = 0
    while idx < len(tokens):
        window = tokens[idx: idx + chunk_size]
        chunk_text = _enc().decode(window).strip()
        if chunk_text:
            start_char = len(_enc().decode(tokens[:idx]))
            end_char = len(_enc().decode(tokens[: idx + len(window)]))
            chunks.append({
                "text": chunk_text,
                "source_document": source_document,
                "page_start": page_for_char_offset(start_char),
                "page_end": page_for_char_offset(max(end_char - 1, start_char)),
                "chunk_index": chunk_index,
                "token_count": len(window),
            })
            chunk_index += 1
        idx += step

    return chunks
