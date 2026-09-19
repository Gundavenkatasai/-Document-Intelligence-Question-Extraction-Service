import re
from typing import Dict, Any, List


class VisualDetector:
    """Detects embedded diagrams, tables, figures, and charts."""

    TABLE_PATTERNS = [
        r"(?i)\btable\s+\d+",
        r"\|.*\|.*\|",  # Markdown-style table
        r"\+[-+]+\+",    # ASCII table border
        r"[-]{3,}\s+[-]{3,}",
    ]

    FIGURE_PATTERNS = [
        r"(?i)\bfigure\s+\d+",
        r"(?i)\bfig\.\s*\d+",
        r"(?i)\bdiagram\b",
        r"(?i)\bchart\b",
        r"(?i)\bgraph\b",
    ]

    @classmethod
    def detect_visual_references(cls, text: str) -> Dict[str, Any]:
        """Scans question text for explicit references to tables or figures."""
        has_table = any(re.search(pat, text) for pat in cls.TABLE_PATTERNS)
        has_fig = any(re.search(pat, text) for pat in cls.FIGURE_PATTERNS)

        return {
            "has_table_reference": bool(has_table),
            "has_figure_reference": bool(has_fig),
            "has_visual_reference": bool(has_table or has_fig),
        }
