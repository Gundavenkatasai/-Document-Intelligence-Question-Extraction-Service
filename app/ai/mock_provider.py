import re
from typing import List, Optional
from app.ai.base import (
    DocumentUnderstandingProvider,
    ExtractedQuestionSchema,
    ExtractedOptionSchema,
    AnswerKeyEntrySchema,
)


class RuleBasedDocumentUnderstandingProvider(DocumentUnderstandingProvider):
    """Deterministic, high-accuracy rule-based document understanding and NLP parsing provider."""

    # Regex to detect question starts:
    # Matches: "Q1. ", "Q1: ", "Question 1: ", "1. ", "1) ", "(1) ", "1: ", "2.If"
    QUESTION_START_REGEX = re.compile(
        r"^(?:(?:Question\s+|Q\.?\s*)(\d+|[IVXLCDMivxlcdm]+)|(\d+)[\.\:\)]|\((\d+)\))\s*[\.\:\-]?\s*(.+)",
        re.MULTILINE
    )

    # Regex to detect options across clean and imperfect OCR formats:
    # (A), A., A), [A], A:, A cos(x), A3, B.5
    OPTION_REGEX = re.compile(
        r"^(?:\(([A-Za-z0-9])\)|([A-Za-z0-9])[\.\)\]]|([A-Da-d])\s*[:\.]|([A-Da-d])\s+(?=[A-Za-z0-9\-\(\$])|([A-Da-d])(?=\d))\s*(.+)",
        re.MULTILINE
    )

    ANSWER_LINE_REGEX = re.compile(
        r"^(?:Answer|Ans\.?|Correct\s*Option)\s*[:\-]?\s*\(?([A-Za-z0-9]+)\)?(?:\s*[:\-]\s*(.*))?",
        re.MULTILINE | re.IGNORECASE
    )

    ANSWER_KEY_PAIR_REGEX = re.compile(
        r"(?:(?:Q\.?|Question\s*)?(\d+)\s*[\.\:\-\)]\s*\(?([A-Za-z0-9]+)\)?)",
        re.IGNORECASE
    )

    async def extract_questions_from_page(
        self,
        page_text: str,
        page_number: int,
        image_bytes: Optional[bytes] = None
    ) -> List[ExtractedQuestionSchema]:
        """Extracts questions and options from page text."""
        if not page_text or not page_text.strip():
            return []

        lines = [line.strip() for line in page_text.splitlines() if line.strip()]
        questions: List[ExtractedQuestionSchema] = []

        current_q: Optional[ExtractedQuestionSchema] = None
        current_option: Optional[ExtractedOptionSchema] = None

        for line in lines:
            # Check for answer line inside question
            ans_match = self.ANSWER_LINE_REGEX.match(line)
            if ans_match and current_q:
                ans_key = ans_match.group(1).strip().upper()
                current_q.detected_answer = ans_key
                current_q.answer_reference = line
                current_option = None
                continue

            # Check for new question boundary
            q_match = self.QUESTION_START_REGEX.match(line)
            if q_match:
                if current_q:
                    questions.append(current_q)

                q_num = q_match.group(1) or q_match.group(2) or q_match.group(3)
                q_text = q_match.group(4).strip()

                current_q = ExtractedQuestionSchema(
                    question_number=q_num,
                    question_text=q_text,
                    question_type="UNKNOWN",
                    options=[],
                    detected_answer=None,
                    source_pages=[page_number],
                    confidence=0.95,
                    warnings=[]
                )
                current_option = None
                continue

            # Check for option boundary
            opt_match = self.OPTION_REGEX.match(line)
            if opt_match:
                key = (opt_match.group(1) or opt_match.group(2) or opt_match.group(3) or opt_match.group(4) or opt_match.group(5)).upper()
                opt_text = opt_match.group(6).strip()
                if current_q is None:
                    # Orphan options at top of page continuing from previous page
                    current_q = ExtractedQuestionSchema(
                        question_number=None,
                        question_text="",
                        question_type="MULTIPLE_CHOICE",
                        options=[],
                        source_pages=[page_number],
                        confidence=0.90,
                        warnings=[]
                    )
                current_option = ExtractedOptionSchema(key=key, text=opt_text)
                current_q.options.append(current_option)
                current_q.question_type = "MULTIPLE_CHOICE"
                continue

            # Continuation of existing option or question text
            if current_option:
                current_option.text += " " + line
            elif current_q:
                current_q.question_text += " " + line
            else:
                # Text preceding any question number - might be unnumbered question
                if any(line.lower().startswith(w) for w in ("what", "explain", "describe", "discuss", "state", "which")):
                    current_q = ExtractedQuestionSchema(
                        question_number=None,
                        question_text=line,
                        question_type="UNKNOWN",
                        options=[],
                        source_pages=[page_number],
                        confidence=0.70,  # Lower confidence due to missing number
                        warnings=["MISSING_QUESTION_NUMBER"]
                    )

        if current_q:
            questions.append(current_q)

        # Refine question types and warn on incomplete structures
        for q in questions:
            self._classify_and_validate_question(q)

        return questions

    def _classify_and_validate_question(self, q: ExtractedQuestionSchema):
        text_lower = q.question_text.lower()

        if q.options:
            q.question_type = "MULTIPLE_CHOICE"
            if len(q.options) < 2:
                q.warnings.append("INCOMPLETE_OPTIONS")
                q.confidence = min(q.confidence, 0.60)
        elif "true or false" in text_lower or text_lower.endswith("(true/false)"):
            q.question_type = "TRUE_FALSE"
        elif any(text_lower.startswith(w) for w in ("explain", "describe", "discuss", "elaborate", "evaluate")):
            q.question_type = "DESCRIPTIVE"
        elif any(text_lower.startswith(w) for w in ("what is", "define", "state", "fill in", "name the", "how many")):
            q.question_type = "SHORT_ANSWER"
        else:
            q.question_type = "UNKNOWN"

    async def parse_answer_key(self, text: str) -> List[AnswerKeyEntrySchema]:
        """Parses answer key text (e.g. '1. A', '2-B', '3: C') into structured items."""
        entries: List[AnswerKeyEntrySchema] = []
        matches = self.ANSWER_KEY_PAIR_REGEX.findall(text)
        for q_num, ans in matches:
            entries.append(AnswerKeyEntrySchema(
                question_number=q_num.strip(),
                answer_text=ans.strip().upper(),
                confidence=0.98,
                reference=f"Q{q_num}: {ans}"
            ))
        return entries


# Backward-compatible alias
MockDocumentUnderstandingProvider = RuleBasedDocumentUnderstandingProvider

__all__ = [
    "RuleBasedDocumentUnderstandingProvider",
    "MockDocumentUnderstandingProvider",
]

