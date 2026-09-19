import re
from typing import List, Optional, Tuple, Dict
from app.ai.base import ExtractedQuestionSchema, ExtractedOptionSchema
from app.core.logging import logger


class MultipageResolver:
    """
    Resolves questions and options that span across page boundaries.
    Prevents artificially splitting a question merely because of a page break.
    """

    # Matches orphan options at top of next page: e.g. "C. ...", "(c) ...", "D. ..."
    ORPHAN_OPTION_REGEX = re.compile(
        r"^(?:\(([C-Zc-z0-9])\)|([C-Zc-z0-9])[\.\)\]]|\b([C-D])\b\s*[:\-])\s+(.+)",
        re.MULTILINE
    )

    @classmethod
    def resolve_page_continuation(
        cls,
        current_page_questions: List[ExtractedQuestionSchema],
        next_page_raw_text: str,
        next_page_number: int,
    ) -> Tuple[List[ExtractedQuestionSchema], str]:
        """
        Checks if the last question on current page continues at the beginning of next page.
        Returns:
            (updated_current_page_questions, consumed_next_page_text_prefix)
        """
        # We will handle multi-page resolution on the list of questions across pages
        pass

    @classmethod
    def merge_multipage_questions(
        cls,
        page_question_map: dict[int, List[ExtractedQuestionSchema]]
    ) -> List[ExtractedQuestionSchema]:
        """
        Processes questions ordered by page number and resolves cross-page boundaries.
        """
        sorted_pages = sorted(page_question_map.keys())
        all_questions: List[ExtractedQuestionSchema] = []

        for p_num in sorted_pages:
            page_qs = page_question_map[p_num]

            for q in page_qs:
                if not all_questions:
                    all_questions.append(q)
                    continue

                prev_q = all_questions[-1]

                # Case 1: Current item is an unnumbered question starting with option C, D, etc.
                # and previous question has options A, B
                if (
                    q.question_number is None
                    and q.options
                    and prev_q.options
                    and q.options[0].key.upper() in ("C", "D", "E", "3", "4")
                    and prev_q.options[-1].key.upper() in ("A", "B", "1", "2")
                ):
                    logger.info(
                        f"Merging multi-page MCQ options from page {p_num} into question {prev_q.question_number} (pages {prev_q.source_pages})"
                    )
                    # Merge options
                    existing_keys = {opt.key.upper() for opt in prev_q.options}
                    for opt in q.options:
                        if opt.key.upper() not in existing_keys:
                            prev_q.options.append(opt)
                            existing_keys.add(opt.key.upper())

                    # Merge text if any
                    if q.question_text and q.question_text.strip():
                        prev_q.question_text += "\n" + q.question_text.strip()

                    # Merge source page
                    if p_num not in prev_q.source_pages:
                        prev_q.source_pages.append(p_num)

                    # Merge detected answer if present
                    if q.detected_answer and not prev_q.detected_answer:
                        prev_q.detected_answer = q.detected_answer
                        prev_q.answer_reference = q.answer_reference

                    continue

                # Case 2: Current item has no question number, no options, and previous question has no options
                # and ends mid-sentence (e.g. without '.', '?', ':')
                if (
                    q.question_number is None
                    and not q.options
                    and not prev_q.options
                    and prev_q.question_text
                    and not prev_q.question_text.strip().endswith((".", "?", ":", "!"))
                ):
                    logger.info(
                        f"Merging multi-page descriptive question stem from page {p_num} into question {prev_q.question_number}"
                    )
                    prev_q.question_text += " " + q.question_text.strip()
                    if p_num not in prev_q.source_pages:
                        prev_q.source_pages.append(p_num)
                    continue

                all_questions.append(q)

        return all_questions
