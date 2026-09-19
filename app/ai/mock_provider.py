import re
from typing import List, Optional, Dict
from app.ai.base import (
    DocumentUnderstandingProvider,
    ExtractedQuestionSchema,
    ExtractedOptionSchema,
    AnswerKeyEntrySchema,
)


class RuleBasedDocumentUnderstandingProvider(DocumentUnderstandingProvider):
    """Deterministic, high-accuracy rule-based document understanding and NLP parsing provider."""

    QUESTION_START_REGEX = re.compile(
        r"^(?:Question\s*(?:Number|No\.?|#)?\s*[:\.]?\s*(\d+|[IVXLCDMivxlcdm]+)|(?:Q\.?\s*)(\d+|[IVXLCDMivxlcdm]+)|(\d+)[\.\:\)]|\((\d+)\))\s*[\.\:\-]?\s*(.*)$",
        re.IGNORECASE
    )

    OPTION_REGEX = re.compile(
        r"^(?:(?:\(([A-Za-z0-9])\)|([A-Za-z0-9])[\.\)\]]|([A-Da-d1-5])\s*[:\.]|([A-Da-d1-5])\s+(?=[A-Za-z0-9\-\(\$])|([1-5])(?=[A-Za-z])))\s*(.*)$"
    )

    OPTIONS_HEADER_REGEX = re.compile(r"^(?:Options\s*[:\.]?|:?s[uon\s]*d?o|:?su[on]*do|:?sdo)", re.IGNORECASE)

    BOILERPLATE_REGEX = re.compile(
        r"^(?:Question\s*Paper\s*Preview|Subject\s*Name\s*:?|Agniveer\s*General\s*Duty|Maximum\s*Instru[a-z]*\s*Time\s*:?|\d+\s*:\s*\d+)",
        re.IGNORECASE
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
        in_options: bool = False
        skip_bilingual: bool = False
        seen_q_nums = set()

        for line in lines:
            if self.BOILERPLATE_REGEX.match(line):
                continue

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
            is_explicit_q = bool(re.search(r"Question|Q\.?\s*\d", line, re.IGNORECASE))

            if q_match and (is_explicit_q or not in_options):
                q_num = q_match.group(1) or q_match.group(2) or q_match.group(3) or q_match.group(4)
                q_text = q_match.group(5).strip()

                # If this question number has already been seen on this page (bilingual duplicate)
                if str(q_num) in seen_q_nums:
                    skip_bilingual = True
                    in_options = False
                    current_option = None
                    continue
                else:
                    skip_bilingual = False
                    seen_q_nums.add(str(q_num))

                if current_q and (current_q.question_text or current_q.options or current_q.question_number):
                    questions.append(current_q)

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
                in_options = False
                continue

            if skip_bilingual:
                continue

            # Check for "Options :" header
            if self.OPTIONS_HEADER_REGEX.match(line):
                in_options = True
                current_option = None
                continue

            # Check for option boundary
            opt_match = self.OPTION_REGEX.match(line)
            is_opt = False
            if opt_match:
                k_candidate = (opt_match.group(1) or opt_match.group(2) or opt_match.group(3) or opt_match.group(4) or opt_match.group(5)).upper()
                if k_candidate in ("A", "B", "C", "D", "E"):
                    is_opt = True
                elif in_options or (current_q and is_explicit_q):
                    is_opt = True

            if is_opt and opt_match:
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
                if current_option.text:
                    current_option.text += " " + line
                else:
                    current_option.text = line
            elif current_q and not in_options:
                if current_q.question_text:
                    current_q.question_text += " " + line
                else:
                    current_q.question_text = line
            else:
                # Text preceding any question number - only match if starting with question word
                if current_q is None:
                    if any(line.lower().startswith(w) for w in ("what", "explain", "describe", "discuss", "state", "which", "how", "find", "evaluate")):
                        current_q = ExtractedQuestionSchema(
                            question_number=None,
                            question_text=line,
                            question_type="UNKNOWN",
                            options=[],
                            source_pages=[page_number],
                            confidence=0.70,
                            warnings=["MISSING_QUESTION_NUMBER"]
                        )

        if current_q and (current_q.question_text or current_q.options or current_q.question_number):
            questions.append(current_q)

        # Filter out empty dummy fragments
        valid_questions: List[ExtractedQuestionSchema] = []
        for q in questions:
            if not q.question_text and not q.options:
                if q.question_number:
                    valid_questions.append(q)
            elif len(q.question_text.strip()) < 3 and not q.options:
                continue
            else:
                valid_questions.append(q)

        # Refine question types and warn on incomplete structures
        for q in valid_questions:
            self._classify_and_validate_question(q)

        return valid_questions

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

    async def extract_questions_from_document(
        self,
        page_texts: Dict[int, str]
    ) -> List[ExtractedQuestionSchema]:
        """Extracts questions across multi-page document preserving continuous stream flows."""
        all_lines = []
        for p_num in sorted(page_texts.keys()):
            text = page_texts[p_num] or ""
            for line in text.splitlines():
                line = line.strip()
                if line:
                    all_lines.append((p_num, line))

        if not all_lines:
            return []

        questions: List[ExtractedQuestionSchema] = []
        curr_q: Optional[ExtractedQuestionSchema] = None
        curr_opt: Optional[ExtractedOptionSchema] = None
        in_options: bool = False
        skip_translation: bool = False
        seen_q_nums = set()

        for p_num, line in all_lines:
            if self.BOILERPLATE_REGEX.match(line):
                continue

            # Check for answer line inside question
            ans_match = self.ANSWER_LINE_REGEX.match(line)
            if ans_match and curr_q:
                ans_key = ans_match.group(1).strip().upper()
                curr_q.detected_answer = ans_key
                curr_q.answer_reference = line
                curr_opt = None
                continue

            # Check for new question boundary
            q_match = self.QUESTION_START_REGEX.match(line)
            is_explicit_q = bool(re.search(r"Question|Q\.?\s*\d", line, re.IGNORECASE))

            is_question = False
            q_num = None
            q_text = ""
            if q_match:
                cand_num = q_match.group(1) or q_match.group(2) or q_match.group(3) or q_match.group(4)
                cand_text = q_match.group(5).strip()
                if is_explicit_q:
                    is_question = True
                    q_num = cand_num
                    q_text = cand_text
                elif not in_options:
                    if curr_q is None:
                        is_question = True
                        q_num = cand_num
                        q_text = cand_text
                    elif cand_num.isdigit() and int(cand_num) > 5:
                        is_question = True
                        q_num = cand_num
                        q_text = cand_text
                    elif curr_q.options:
                        is_question = True
                        q_num = cand_num
                        q_text = cand_text
                    elif not curr_q.question_text:
                        is_question = True
                        q_num = cand_num
                        q_text = cand_text
                    elif cand_num.isdigit() and str(cand_num) != str(curr_q.question_number):
                        if len(curr_q.question_text) > 5 and ("?" in curr_q.question_text or int(cand_num) == int(curr_q.question_number or 0) + 1):
                            is_question = True
                            q_num = cand_num
                            q_text = cand_text
                elif in_options:
                    has_letter_opts = any(o.key in ("A", "B", "C", "D", "E") for o in (curr_q.options if curr_q else []))
                    if cand_num.isdigit() and (int(cand_num) > 5 or has_letter_opts or (curr_q and len(curr_q.options) >= 4)):
                        is_question = True
                        q_num = cand_num
                        q_text = cand_text

            if is_question and q_num:
                # If this question number has already been seen in this document (bilingual translation)
                if str(q_num) in seen_q_nums:
                    skip_translation = True
                    in_options = False
                    curr_opt = None
                    continue
                else:
                    skip_translation = False
                    seen_q_nums.add(str(q_num))

                if curr_q and (curr_q.question_text or curr_q.options or curr_q.question_number) and not (len(curr_q.question_text.strip()) < 3 and not curr_q.options):
                    questions.append(curr_q)

                curr_q = ExtractedQuestionSchema(
                    question_number=str(q_num),
                    question_text=q_text,
                    question_type="UNKNOWN",
                    options=[],
                    detected_answer=None,
                    source_pages=[p_num],
                    confidence=0.95,
                    warnings=[]
                )
                curr_opt = None
                in_options = False
                continue

            if skip_translation:
                continue

            # Check for "Options :" header
            if self.OPTIONS_HEADER_REGEX.match(line):
                in_options = True
                curr_opt = None
                continue

            # Check if line looks like an option (or starts option block)
            opt_match = self.OPTION_REGEX.match(line)
            if not in_options and opt_match and curr_q is not None:
                cand_k = (opt_match.group(1) or opt_match.group(2) or opt_match.group(3) or opt_match.group(4) or opt_match.group(5)).upper()
                if cand_k in ("1", "2", "A", "B") and (len(curr_q.question_text) > 10 or "?" in curr_q.question_text or ":" in curr_q.question_text):
                    in_options = True
                elif len(curr_q.options) > 0 and cand_k in ("2", "3", "4", "5", "B", "C", "D", "E"):
                    in_options = True

            if in_options:
                if opt_match:
                    k = (opt_match.group(1) or opt_match.group(2) or opt_match.group(3) or opt_match.group(4) or opt_match.group(5)).upper()
                    otext = opt_match.group(6).strip()

                    if curr_q is not None:
                        # If option key already exists in this question, it's the second language translation!
                        if any(o.key == k for o in curr_q.options):
                            skip_translation = True
                            in_options = False
                            curr_opt = None
                            continue

                        curr_opt = ExtractedOptionSchema(key=k, text=otext)
                        curr_q.options.append(curr_opt)
                        curr_q.question_type = "MULTIPLE_CHOICE"
                        if p_num not in curr_q.source_pages:
                            curr_q.source_pages.append(p_num)
                    continue
                else:
                    # Continuation of current option or an option without key
                    if curr_opt is not None:
                        if not curr_opt.text:
                            curr_opt.text = line
                        else:
                            curr_opt.text += " " + line
                        if curr_q and p_num not in curr_q.source_pages:
                            curr_q.source_pages.append(p_num)
                        continue
                    elif curr_q and len(curr_q.options) < 4:
                        curr_opt = ExtractedOptionSchema(key=str(len(curr_q.options) + 1), text=line)
                        curr_q.options.append(curr_opt)
                        curr_q.question_type = "MULTIPLE_CHOICE"
                        if p_num not in curr_q.source_pages:
                            curr_q.source_pages.append(p_num)
                        continue

            # If not in options, line belongs to question text
            if curr_q is not None and not in_options:
                if not curr_q.question_text:
                    curr_q.question_text = line
                else:
                    curr_q.question_text += " " + line
                if p_num not in curr_q.source_pages:
                    curr_q.source_pages.append(p_num)
            elif curr_q is None:
                # Text preceding any question number
                curr_q = ExtractedQuestionSchema(
                    question_number=None,
                    question_text=line,
                    question_type="UNKNOWN",
                    options=[],
                    source_pages=[p_num],
                    confidence=0.70,
                    warnings=["MISSING_QUESTION_NUMBER"]
                )

        if curr_q and (curr_q.question_text or curr_q.options or curr_q.question_number) and not (len(curr_q.question_text.strip()) < 3 and not curr_q.options):
            questions.append(curr_q)

        valid_questions: List[ExtractedQuestionSchema] = []
        for q in questions:
            if not q.question_text and not q.options:
                if q.question_number:
                    valid_questions.append(q)
            elif len(q.question_text.strip()) < 3 and not q.options:
                continue
            elif q.question_number is None and not q.options:
                continue
            else:
                valid_questions.append(q)

        for q in valid_questions:
            self._classify_and_validate_question(q)

        return valid_questions

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

