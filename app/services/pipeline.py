import re
import time
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.logging import logger
from app.db.models import (
    Document,
    DocumentPage,
    ProcessingJob,
    ExtractedQuestion,
    QuestionOption,
    QuestionAnswer,
    ReviewItem,
)
from app.services.storage import get_storage_service
from app.services.preprocessing.pdf_processor import PDFProcessor
from app.services.preprocessing.image_processor import ImageProcessor
from app.services.extraction.native_extractor import NativeExtractor
from app.services.extraction.ocr_extractor import OCRExtractor
from app.services.extraction.visual_detector import VisualDetector
from app.services.extraction.multipage_resolver import MultipageResolver
from app.services.answer_keys.matcher import AnswerKeyMatcher
from app.services.confidence.scorer import ConfidenceScorer
from app.ai.factory import get_ai_provider
from app.ai.base import ExtractedQuestionSchema, AnswerKeyEntrySchema


class DocumentProcessingPipeline:
    """End-to-end asynchronous document processing pipeline."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.storage = get_storage_service()
        self.ocr_extractor = OCRExtractor()
        self.ai_provider = get_ai_provider()

    @staticmethod
    def _is_hollow_native_text(native_text: str, visual_info: Dict[str, Any]) -> bool:
        """
        Determines if a PDF page's native text stream is incomplete, placeholder,
        or contains empty option labels masking embedded question images.
        """
        if not native_text or len(native_text.strip()) < settings.MIN_CHARS_FOR_NATIVE_TEXT:
            return True

        if native_text.count("\ufffd") >= 2:
            return True

        has_images = visual_info.get("embedded_image_count", 0) > 0 or visual_info.get("has_visual_content", False)
        if has_images:
            # Empty option numbers (e.g. 1.\n2.\n or A.\nB.\n with nothing in between)
            if re.search(r"(?:1\.|A\.)\s*[\r\n]+\s*(?:2\.|B\.)", native_text):
                return True
            # Question headers immediately followed by Options with no question body text
            if re.search(r"Question\s*(?:Number|No\.?|#)?\s*[:\.]?\s*\d+\s*[\r\n]+\s*Options\s*[:\.]?", native_text, re.IGNORECASE):
                return True
            # Very low meaningful word density relative to page having embedded images
            words = re.findall(r"[a-zA-Z]{3,}", native_text)
            if len(words) < 12:
                return True

        return False

    async def run(self, document_id: uuid.UUID) -> None:
        start_time = time.time()
        logger.info(f"Starting processing pipeline for document {document_id}", extra={"document_id": str(document_id), "stage": "INITIALIZE"})

        # Load document
        stmt = select(Document).where(Document.id == document_id).options(selectinload(Document.jobs))
        result = await self.db.execute(stmt)
        doc = result.scalar_one_or_none()

        if not doc:
            logger.error(f"Document {document_id} not found.")
            return

        # Create or update processing job
        job = ProcessingJob(
            document_id=doc.id,
            status="RUNNING",
            stage="INITIALIZING",
            progress_percent=5,
        )
        self.db.add(job)
        doc.status = "PROCESSING"
        doc.error_message = None

        # Clean up any existing pages/questions/reviews from previous runs
        await self.db.execute(
            delete(QuestionOption).where(
                QuestionOption.question_id.in_(
                    select(ExtractedQuestion.id).where(ExtractedQuestion.document_id == doc.id)
                )
            )
        )
        await self.db.execute(
            delete(QuestionAnswer).where(
                QuestionAnswer.question_id.in_(
                    select(ExtractedQuestion.id).where(ExtractedQuestion.document_id == doc.id)
                )
            )
        )
        await self.db.execute(delete(ExtractedQuestion).where(ExtractedQuestion.document_id == doc.id))
        await self.db.execute(delete(ReviewItem).where(ReviewItem.document_id == doc.id))
        await self.db.execute(delete(DocumentPage).where(DocumentPage.document_id == doc.id))
        await self.db.commit()

        try:
            # 1. Fetch file content from storage
            content = await self.storage.get_file(doc.storage_path)

            job.stage = "PAGE_PARSING"
            job.progress_percent = 15
            await self.db.commit()

            # 2. Page rendering and text extraction
            page_records: List[DocumentPage] = []
            page_texts: Dict[int, str] = {}
            page_ocr_confs: Dict[int, float] = {}

            if doc.file_type == "PDF":
                total_pages = PDFProcessor.get_page_count(content)
                doc.total_pages = total_pages

                for p_num in range(1, total_pages + 1):
                    # Try native text extraction
                    native_text, char_count = NativeExtractor.extract_text(content, p_num)
                    visual_info = PDFProcessor.detect_page_visual_elements(content, p_num)

                    if not self._is_hollow_native_text(native_text, visual_info):
                        ext_method = "native_text"
                        page_text = native_text
                        page_ocr_confs[p_num] = 1.0
                    else:
                        # Scanned or image-embedded PDF page fallback to OCR
                        ext_method = "ocr"
                        img_bytes = PDFProcessor.render_page_to_image(content, p_num, dpi=72)
                        page_text, ocr_conf, _ = self.ocr_extractor.extract_text(img_bytes)
                        page_ocr_confs[p_num] = ocr_conf

                    page_rec = DocumentPage(
                        document_id=doc.id,
                        page_number=p_num,
                        extraction_method=ext_method,
                        raw_text=page_text,
                        character_count=len(page_text),
                        has_visual_content=visual_info["has_visual_content"],
                        page_metadata=visual_info,
                    )
                    page_records.append(page_rec)
                    page_texts[p_num] = page_text
                    doc.processed_pages = p_num

            else:
                # Single Image (PNG / JPG)
                doc.total_pages = 1
                ocr_text, ocr_conf, ocr_meta = self.ocr_extractor.extract_text(content)
                page_ocr_confs[1] = ocr_conf

                page_rec = DocumentPage(
                    document_id=doc.id,
                    page_number=1,
                    extraction_method="ocr",
                    raw_text=ocr_text,
                    character_count=len(ocr_text),
                    has_visual_content=False,
                    page_metadata=ocr_meta,
                )
                page_records.append(page_rec)
                page_texts[1] = ocr_text
                doc.processed_pages = 1

            for pr in page_records:
                self.db.add(pr)
            await self.db.flush()

            # 3. Question Extraction using AI / Segmenter
            job.stage = "QUESTION_EXTRACTION"
            job.progress_percent = 40
            await self.db.commit()

            resolved_questions = await self.ai_provider.extract_questions_from_document(page_texts)

            # Check for visual references in question texts
            for q in resolved_questions:
                vis_ref = VisualDetector.detect_visual_references(q.question_text)
                if vis_ref["has_visual_reference"]:
                    q.has_visual = True

            # 4. Multi-page question resolution
            job.stage = "MULTIPAGE_RESOLUTION"
            job.progress_percent = 60
            await self.db.commit()

            # 5. Answer Key Detection & Cross-document Matching
            job.stage = "ANSWER_KEY_MATCHING"
            job.progress_percent = 75
            await self.db.commit()

            # Scan current document for answer key sections
            full_text = "\n".join(page_texts.values())
            detected_keys = await self.ai_provider.parse_answer_key(full_text)
            answer_source_doc_id = doc.id

            # If document belongs to a group, check other documents in group for answer key
            if doc.group_id:
                group_docs_stmt = select(Document).where(
                    Document.group_id == doc.group_id,
                    Document.id != doc.id
                ).options(selectinload(Document.pages))
                group_docs_res = await self.db.execute(group_docs_stmt)
                sibling_docs = group_docs_res.scalars().all()

                for sib in sibling_docs:
                    sib_text = "\n".join([p.raw_text or "" for p in sib.pages])
                    if "answer key" in sib.filename.lower() or "answer" in sib.filename.lower() or "answer key" in sib_text.lower():
                        sib_keys = await self.ai_provider.parse_answer_key(sib_text)
                        if sib_keys:
                            detected_keys.extend(sib_keys)
                            answer_source_doc_id = sib.id
                            logger.info(f"Loaded {len(sib_keys)} answer keys from related document {sib.filename}")

            matched_answers = AnswerKeyMatcher.match_answers(
                questions=resolved_questions,
                answer_keys=detected_keys,
                source_document_id=answer_source_doc_id if detected_keys else None
            )

            # Map matched answers by question number / index
            ans_map = {ans.question_number: ans for ans in matched_answers if ans.question_number}

            # 6. Confidence Scoring and Review Generation
            job.stage = "CONFIDENCE_AND_REVIEW"
            job.progress_percent = 85
            await self.db.commit()

            saved_questions: List[ExtractedQuestion] = []
            review_items: List[ReviewItem] = []

            for i, q_schema in enumerate(resolved_questions):
                matched_ans = ans_map.get(q_schema.question_number) or (matched_answers[i] if i < len(matched_answers) else None)
                p_first = q_schema.source_pages[0] if q_schema.source_pages else 1
                ocr_conf = page_ocr_confs.get(p_first, 1.0)
                ext_meth = page_records[p_first - 1].extraction_method if p_first <= len(page_records) else "native_text"

                conf_score, review_status, warnings = ConfidenceScorer.calculate_confidence(
                    question=q_schema,
                    matched_answer=matched_ans,
                    extraction_method=ext_meth,
                    ocr_confidence=ocr_conf
                )

                db_q = ExtractedQuestion(
                    document_id=doc.id,
                    question_number=q_schema.question_number,
                    question_text=q_schema.question_text,
                    question_type=q_schema.question_type,
                    source_pages=q_schema.source_pages,
                    confidence_score=conf_score,
                    review_status=review_status,
                    has_visual_content=q_schema.has_visual,
                    visual_metadata={"has_visual": q_schema.has_visual},
                    raw_metadata={"confidence_breakdown": {"base": ocr_conf, "final": conf_score}},
                    warnings=warnings
                )

                # Add options
                for opt in q_schema.options:
                    is_corr = None
                    if matched_ans and matched_ans.answer_text and opt.key.upper() == matched_ans.answer_text.upper():
                        is_corr = True
                    db_opt = QuestionOption(
                        option_key=opt.key,
                        option_text=opt.text,
                        is_correct=is_corr
                    )
                    db_q.options.append(db_opt)

                # Add answer
                if matched_ans:
                    db_ans = QuestionAnswer(
                        source_document_id=matched_ans.source_document_id,
                        answer_text=matched_ans.answer_text,
                        answer_key_reference=matched_ans.reference,
                        match_type=matched_ans.match_type,
                        confidence_score=matched_ans.confidence_score,
                        explanation=matched_ans.explanation,
                        raw_metadata={"reference": matched_ans.reference}
                    )
                    db_q.answer = db_ans

                self.db.add(db_q)
                saved_questions.append(db_q)

                # If review status is PENDING_REVIEW, add to Review Queue
                if review_status == "PENDING_REVIEW":
                    reason = f"Low confidence score ({conf_score:.2f}) or warnings: {', '.join(warnings)}"
                    rev = ReviewItem(
                        document_id=doc.id,
                        question=db_q,
                        status="PENDING",
                        reason=reason,
                        confidence_score=conf_score,
                        warnings=warnings,
                        notes="Automated review item flagged during document intelligence pipeline."
                    )
                    review_items.append(rev)
                    self.db.add(rev)

            # 7. Finalize document status
            doc.status = "COMPLETED"
            duration = round(time.time() - start_time, 2)
            job.status = "SUCCESS"
            job.stage = "COMPLETED"
            job.progress_percent = 100
            job.duration_seconds = duration

            await self.db.commit()
            logger.info(
                f"Successfully completed processing for document {doc.id} in {duration}s. Extracted {len(saved_questions)} questions, flagged {len(review_items)} reviews.",
                extra={"document_id": str(doc.id), "stage": "DONE", "duration_ms": int(duration * 1000)}
            )

        except Exception as e:
            logger.exception(f"Document processing failed for {doc.id}: {e}", extra={"document_id": str(doc.id), "stage": "FAILURE"})
            await self.db.rollback()
            # Mark document as failed with sanitized message
            doc.status = "FAILED"
            doc.error_message = f"Processing error: {str(e)}"
            job.status = "FAILED"
            job.stage = "ERROR"
            job.error_details = {"error": str(e)}
            job.duration_seconds = round(time.time() - start_time, 2)
            await self.db.commit()
