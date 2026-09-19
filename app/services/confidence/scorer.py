from typing import List, Tuple, Optional
from app.ai.base import ExtractedQuestionSchema
from app.services.answer_keys.matcher import MatchedAnswerResult
from app.core.config import settings


class ConfidenceScorer:
    """
    Transparent confidence scoring engine.
    Computes a composite score based on structural completeness,
    text quality, option validity, and warnings.
    """

    @classmethod
    def calculate_confidence(
        cls,
        question: ExtractedQuestionSchema,
        matched_answer: Optional[MatchedAnswerResult] = None,
        extraction_method: str = "native_text",
        ocr_confidence: float = 1.0
    ) -> Tuple[float, str, List[str]]:
        """
        Calculates normalized confidence score (0.0 to 1.0), review_status ('ACCEPTED' or 'PENDING_REVIEW'),
        and list of warning codes.

        Scoring Breakdown (Base = 1.0):
        - Native text extraction: 1.0 baseline.
        - OCR extraction: scaled by OCR average word confidence (e.g. 0.85).
        - Penalties:
          * Missing question number: -0.20
          * Question text too short (< 15 chars): -0.25
          * MCQ with < 2 options: -0.30
          * MCQ with only 2 or 3 options (non True/False): -0.05
          * Multi-page spanning ambiguity: -0.15
          * Unmatched or uncertain answer key (when key was expected): -0.10
          * Visual content requiring verification: -0.05
        """
        warnings: List[str] = list(question.warnings)

        # Baseline based on extraction method
        if extraction_method == "ocr":
            score = max(0.60, min(1.0, ocr_confidence))
            if ocr_confidence < 0.65:
                warnings.append("LOW_OCR_QUALITY")
        else:
            score = 1.0

        # Check question number
        if not question.question_number:
            score -= 0.20
            if "MISSING_QUESTION_NUMBER" not in warnings:
                warnings.append("MISSING_QUESTION_NUMBER")

        # Check question text length
        if len(question.question_text.strip()) < 15:
            score -= 0.25
            warnings.append("SHORT_QUESTION_TEXT")

        # Check options
        if question.question_type == "MULTIPLE_CHOICE":
            num_opts = len(question.options)
            if num_opts < 2:
                score -= 0.30
                if "INCOMPLETE_OPTIONS" not in warnings:
                    warnings.append("INCOMPLETE_OPTIONS")
            elif num_opts < 4:
                score -= 0.05

        # Check multi-page continuity
        if len(question.source_pages) > 1:
            # Spanned multiple pages
            if "MULTI_PAGE_AMBIGUITY" in warnings:
                score -= 0.15

        # Check answer key matching
        if matched_answer:
            if matched_answer.match_type == "uncertain":
                score -= 0.15
                warnings.append("UNCERTAIN_ANSWER")
            elif matched_answer.match_type == "unmatched" and matched_answer.source_document_id:
                # Answer key doc was provided but this question was missing
                score -= 0.08
                warnings.append("ANSWER_UNMATCHED")

        # Check visual content
        if question.has_visual:
            warnings.append("VISUAL_CONTENT_DETECTED")

        # Normalize score
        final_score = round(max(0.0, min(1.0, score)), 2)

        # Review status determination
        threshold = settings.CONFIDENCE_REVIEW_THRESHOLD
        if final_score < threshold or any(w in warnings for w in ("LOW_OCR_QUALITY", "INCOMPLETE_OPTIONS", "UNCERTAIN_ANSWER")):
            review_status = "PENDING_REVIEW"
        else:
            review_status = "ACCEPTED"

        return final_score, review_status, sorted(list(set(warnings)))
