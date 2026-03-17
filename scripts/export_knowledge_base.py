#!/usr/bin/env python3
"""Export the technical writer knowledge base as a ZIP archive for external RAG use.

Usage:
    python scripts/export_knowledge_base.py                     # Default output: dist/knowledge-base.zip
    python scripts/export_knowledge_base.py -o my-kb.zip        # Custom output path
    python scripts/export_knowledge_base.py --validate          # Validate before export
"""

import argparse
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

KNOWLEDGE_DIR = Path("skills/engineering-technical-writer/knowledge")
DEFAULT_OUTPUT = Path("dist/knowledge-base.zip")


def validate_knowledge_base(kb_dir: Path) -> list[str]:
    """Validate knowledge base documents for completeness and structure.

    Returns a list of validation errors (empty if all pass).
    """
    errors = []

    # Check index exists
    index_path = kb_dir / "rag-index.json"
    if not index_path.exists():
        errors.append("Missing rag-index.json")
        return errors

    with open(index_path) as f:
        index = json.load(f)

    documents = index.get("documents", [])
    if not documents:
        errors.append("rag-index.json contains no documents")
        return errors

    # Validate each indexed document
    for doc in documents:
        doc_file = kb_dir / doc["file"]
        doc_id = doc.get("id", doc["file"])

        # File exists
        if not doc_file.exists():
            errors.append(f"[{doc_id}] File not found: {doc['file']}")
            continue

        content = doc_file.read_text(encoding="utf-8")

        # Has YAML frontmatter
        if not content.startswith("---"):
            errors.append(f"[{doc_id}] Missing YAML frontmatter")

        # Has grounding checklist
        if "Grounding Checklist" not in content:
            errors.append(f"[{doc_id}] Missing Grounding Checklist section")

        # Has claim tags
        has_tags = any(
            tag in content
            for tag in ["[observed]", "[inferred]", "[general]", "[unverified]"]
        )
        if not has_tags:
            errors.append(f"[{doc_id}] No claim tags found")

        # Has anti-patterns section
        if "Anti-Pattern" not in content:
            errors.append(f"[{doc_id}] Missing Anti-Patterns section")

        # Required index fields
        for field in ["id", "file", "title", "domain", "tags", "sections", "retrieval_queries"]:
            if field not in doc:
                errors.append(f"[{doc_id}] Missing index field: {field}")

    # Check for files not in index
    md_files = {f.name for f in kb_dir.glob("*.md")}
    indexed_files = {doc["file"] for doc in documents}
    unindexed = md_files - indexed_files
    if unindexed:
        for f in sorted(unindexed):
            errors.append(f"File not in rag-index.json: {f}")

    return errors


def build_manifest(kb_dir: Path) -> dict[str, Any]:
    """Build an export manifest with metadata about the knowledge base."""
    index_path = kb_dir / "rag-index.json"
    with open(index_path) as f:
        index = json.load(f)

    documents = index.get("documents", [])
    total_size = 0
    file_details = []

    for doc in documents:
        # Ensure required fields are present to avoid KeyError on malformed indexes
        required_fields = ("id", "file", "title")
        missing_fields = [field for field in required_fields if field not in doc]
        if missing_fields:
            doc_id = doc.get("id", "<unknown>")
            sys.stderr.write(
                f"Warning: skipping document in rag-index.json with missing fields "
                f"{missing_fields} (id={doc_id})\n"
            )
            continue

        doc_path = kb_dir / doc["file"]
        if doc_path.exists():
            size = doc_path.stat().st_size
            total_size += size
            file_details.append({
                "id": doc["id"],
                "file": doc["file"],
                "title": doc["title"],
                "size_bytes": size,
                "tags": doc.get("tags", []),
                "sections": doc.get("sections", []),
                "retrieval_queries": doc.get("retrieval_queries", []),
            })

    return {
        "name": "technical-writer-knowledge-base",
        "version": index.get("version", "1.0.0"),
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "source": "audhd-agents/skills/engineering-technical-writer/knowledge",
        "document_count": len(file_details),
        "total_size_bytes": total_size,
        "rag_compatible": True,
        "chunk_strategy": "section-based",
        "claim_tags": ["observed", "inferred", "general", "unverified"],
        "documents": file_details,
    }


def export_zip(kb_dir: Path, output_path: Path, validate: bool = False) -> None:
    """Package the knowledge base into a ZIP archive with manifest."""
    if not kb_dir.exists():
        print(f"Error: Knowledge base directory not found: {kb_dir}")
        sys.exit(1)

    if validate:
        print("Validating knowledge base...")
        errors = validate_knowledge_base(kb_dir)
        if errors:
            print(f"Validation failed with {len(errors)} error(s):")
            for err in errors:
                print(f"  - {err}")
            sys.exit(1)
        print("Validation passed.")

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build manifest
    manifest = build_manifest(kb_dir)

    # Create ZIP
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add all knowledge documents
        for f in sorted(kb_dir.iterdir()):
            if f.is_file():
                arcname = f"knowledge-base/{f.name}"
                zf.write(f, arcname)
                print(f"  Added: {arcname}")

        # Add manifest
        manifest_json = json.dumps(manifest, indent=2)
        zf.writestr("knowledge-base/manifest.json", manifest_json)
        print("  Added: knowledge-base/manifest.json")

    size_kb = output_path.stat().st_size / 1024
    print(f"\nExported: {output_path} ({size_kb:.1f} KB)")
    print(f"Documents: {manifest['document_count']}")
    print(f"Total content: {manifest['total_size_bytes'] / 1024:.1f} KB")


def main():
    parser = argparse.ArgumentParser(
        description="Export technical writer knowledge base as ZIP for external RAG"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output ZIP path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate knowledge base before export",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate; do not export",
    )
    args = parser.parse_args()

    if args.validate_only:
        errors = validate_knowledge_base(KNOWLEDGE_DIR)
        if errors:
            print(f"Validation failed with {len(errors)} error(s):")
            for err in errors:
                print(f"  - {err}")
            sys.exit(1)
        print("Validation passed. All documents are valid.")
        sys.exit(0)

    export_zip(KNOWLEDGE_DIR, args.output, validate=args.validate)


if __name__ == "__main__":
    main()
