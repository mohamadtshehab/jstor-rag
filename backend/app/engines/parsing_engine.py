from __future__ import annotations

import re
import uuid

from ..contracts.dtos import DocumentChunk, DocumentMetadata
from ..contracts.interfaces import IParsingEngine

_SECTION_PATTERN = re.compile(
    r"^(?:"
    r"(?:(?:\d+\.?\s+)?)"  # optional numbering  "1. " or "1 "
    r"(?:ABSTRACT|INTRODUCTION|BACKGROUND|LITERATURE\s+REVIEW|"
    r"RELATED\s+WORK|METHODOLOGY|METHODS?|MATERIALS?\s+AND\s+METHODS?|"
    r"RESULTS?|FINDINGS?|DISCUSSION|ANALYSIS|CONCLUSION|CONCLUSIONS|"
    r"SUMMARY|ACKNOWLEDGMENTS?|ACKNOWLEDGEMENTS?|REFERENCES?|"
    r"APPENDIX|BIBLIOGRAPHY|NOTES)"
    r")\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)

_MAX_CHUNK_SIZE = 1500
_CHUNK_OVERLAP = 200


class ParsingEngine(IParsingEngine):
    """Semantic chunking for academic texts.

    Detects logical section boundaries, splits within sections at paragraph
    breaks, and tracks character offsets so SourceLocators remain UI-agnostic.
    """

    def create_chunks(
        self, text: str, document_id: str, metadata: DocumentMetadata
    ) -> list[DocumentChunk]:
        sections = self._split_sections(text)
        chunks: list[DocumentChunk] = []

        for section_name, section_text, section_offset in sections:
            section_chunks = self._chunk_text(
                section_text, section_offset, section_name, document_id
            )
            chunks.extend(section_chunks)

        return chunks

    def _split_sections(
        self, text: str
    ) -> list[tuple[str, str, int]]:
        matches = list(_SECTION_PATTERN.finditer(text))
        if not matches:
            return [("Body", text, 0)]

        sections: list[tuple[str, str, int]] = []

        if matches[0].start() > 0:
            preamble = text[: matches[0].start()]
            if preamble.strip():
                sections.append(("Preamble", preamble, 0))

        for i, match in enumerate(matches):
            name = match.group().strip().rstrip(":")
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[start:end]
            if body.strip():
                sections.append((name, body, start))

        return sections

    def _chunk_text(
        self,
        text: str,
        base_offset: int,
        section_name: str,
        document_id: str,
    ) -> list[DocumentChunk]:
        if len(text) <= _MAX_CHUNK_SIZE:
            return [
                DocumentChunk(
                    chunk_id=str(uuid.uuid4()),
                    document_id=document_id,
                    text=text.strip(),
                    logical_section=section_name,
                    start_offset=base_offset,
                    end_offset=base_offset + len(text),
                )
            ]

        paragraphs = re.split(r"\n\s*\n", text)
        chunks: list[DocumentChunk] = []
        current_text = ""
        current_start = base_offset

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_text) + len(para) + 1 > _MAX_CHUNK_SIZE and current_text:
                chunks.append(
                    DocumentChunk(
                        chunk_id=str(uuid.uuid4()),
                        document_id=document_id,
                        text=current_text,
                        logical_section=section_name,
                        start_offset=current_start,
                        end_offset=current_start + len(current_text),
                    )
                )
                overlap = current_text[-_CHUNK_OVERLAP:] if len(current_text) > _CHUNK_OVERLAP else ""
                current_start = current_start + len(current_text) - len(overlap)
                current_text = overlap + ("\n\n" if overlap else "") + para
            else:
                if current_text:
                    current_text += "\n\n" + para
                else:
                    current_text = para

        if current_text.strip():
            chunks.append(
                DocumentChunk(
                    chunk_id=str(uuid.uuid4()),
                    document_id=document_id,
                    text=current_text.strip(),
                    logical_section=section_name,
                    start_offset=current_start,
                    end_offset=current_start + len(current_text),
                )
            )

        return chunks
