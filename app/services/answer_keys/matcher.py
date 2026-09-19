import uuid
from typing import List, Dict, Optional, Tuple
from app.ai.base import ExtractedQuestionSchema, AnswerKeyEntrySchema
from app.core.logging import logger


class MatchedAnswerResult:
    def __init__(
        self,
        question_id: Optional[uuid.UUID],
        question_number: Optional[str],
        answer_text: Optional[str],
        reference: Optional[str],
        match_type: str,  # matched, unmatched, uncertain, not_available
        confidence_score: float,
        source_document_id: Optional[uuid.UUID] = None,
        explanation: Optional[str] = None
    ):
        self.question_id = question_id
        self.question_number = question_number
        self.answer_text = answer_text
        self.reference = reference
        self.match_type = match_type
        self.confidence_score = confidence_score
        self.source_document_id = source_document_id
        self.explanation = explanation


class AnswerKeyMatcher:
    """Matches questions with answer keys safely without hallucination."""

    @classmethod
    def match_answers(
        cls,
        questions: List[ExtractedQuestionSchema],
        answer_keys: List[AnswerKeyEntrySchema],
        source_document_id: Optional[uuid.UUID] = None
    ) -> List[MatchedAnswerResult]:
        results: List[MatchedAnswerResult] = []
        # Index answer keys by question number (cleaned)
        key_map: Dict[str, AnswerKeyEntrySchema] = {}
        for k in answer_keys:
            norm_num = k.question_number.strip().lstrip("0")
            key_map[norm_num] = k

        for q in questions:
            # First check if question had an embedded answer in its text
            if q.detected_answer:
                ans_text = q.detected_answer.strip().upper()
                valid_match = True
                confidence = 0.95
                match_type = "matched"
                explanation = f"Detected inline answer in question text: {q.answer_reference or ans_text}"

                # If MCQ, verify option exists
                if q.options:
                    opt_keys = {opt.key.strip().upper() for opt in q.options}
                    if ans_text not in opt_keys:
                        match_type = "uncertain"
                        confidence = 0.40
                        explanation = f"Detected answer '{ans_text}' does not match available options: {sorted(opt_keys)}"

                results.append(MatchedAnswerResult(
                    question_id=None,
                    question_number=q.question_number,
                    answer_text=ans_text if match_type == "matched" else None,
                    reference=q.answer_reference,
                    match_type=match_type,
                    confidence_score=confidence,
                    source_document_id=source_document_id,
                    explanation=explanation
                ))
                continue

            # Second: Look up in separate/table answer key
            if not answer_keys:
                results.append(MatchedAnswerResult(
                    question_id=None,
                    question_number=q.question_number,
                    answer_text=None,
                    reference=None,
                    match_type="not_available",
                    confidence_score=0.0,
                    source_document_id=None,
                    explanation="No answer key provided for document."
                ))
                continue

            if not q.question_number:
                results.append(MatchedAnswerResult(
                    question_id=None,
                    question_number=None,
                    answer_text=None,
                    reference=None,
                    match_type="unmatched",
                    confidence_score=0.0,
                    source_document_id=source_document_id,
                    explanation="Question is missing a question number, cannot match with answer key."
                ))
                continue

            norm_q_num = q.question_number.strip().lstrip("0")
            if norm_q_num in key_map:
                key_entry = key_map[norm_q_num]
                ans_val = key_entry.answer_text.strip().upper()

                # Validate against options if MCQ
                if q.options:
                    opt_keys = {opt.key.strip().upper() for opt in q.options}
                    if ans_val not in opt_keys:
                        results.append(MatchedAnswerResult(
                            question_id=None,
                            question_number=q.question_number,
                            answer_text=None,
                            reference=key_entry.reference,
                            match_type="uncertain",
                            confidence_score=0.35,
                            source_document_id=source_document_id,
                            explanation=f"Answer key indicates '{ans_val}', but options only include {sorted(opt_keys)}."
                        ))
                        continue

                results.append(MatchedAnswerResult(
                    question_id=None,
                    question_number=q.question_number,
                    answer_text=ans_val,
                    reference=key_entry.reference,
                    match_type="matched",
                    confidence_score=0.96,
                    source_document_id=source_document_id,
                    explanation=f"Matched with answer key reference: {key_entry.reference}"
                ))
            else:
                results.append(MatchedAnswerResult(
                    question_id=None,
                    question_number=q.question_number,
                    answer_text=None,
                    reference=None,
                    match_type="unmatched",
                    confidence_score=0.0,
                    source_document_id=source_document_id,
                    explanation=f"Question {q.question_number} not found in answer key."
                ))

        return results
