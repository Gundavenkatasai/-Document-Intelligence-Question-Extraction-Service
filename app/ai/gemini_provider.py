import json
import os
from typing import List, Optional
from pydantic import ValidationError

from app.core.config import settings
from app.core.logging import logger
from app.ai.base import (
    DocumentUnderstandingProvider,
    ExtractedQuestionSchema,
    AnswerKeyEntrySchema,
)
from app.ai.mock_provider import MockDocumentUnderstandingProvider


class GeminiDocumentUnderstandingProvider(DocumentUnderstandingProvider):
    """Multimodal document understanding provider powered by Google Gemini."""

    def __init__(self):
        self.api_key = settings.AI_API_KEY or os.getenv("GEMINI_API_KEY")
        self.model_name = settings.AI_MODEL or "gemini-1.5-flash"
        self._fallback = MockDocumentUnderstandingProvider()

    async def extract_questions_from_page(
        self,
        page_text: str,
        page_number: int,
        image_bytes: Optional[bytes] = None
    ) -> List[ExtractedQuestionSchema]:
        if not self.api_key:
            logger.info("No Gemini API key configured. Utilizing local fallback provider.")
            return await self._fallback.extract_questions_from_page(page_text, page_number, image_bytes)

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)

            prompt = f"""
            You are an expert Document Intelligence and Examination Question Extraction engine.
            Extract all questions, options, detected answers, and metadata from the following text (from Page {page_number}).
            
            RULES:
            - Do not invent missing information.
            - Return null for question_number if uncertain or unnumbered.
            - Question types must be one of: MULTIPLE_CHOICE, TRUE_FALSE, SHORT_ANSWER, DESCRIPTIVE, UNKNOWN.
            - Preserve exact source page: {page_number}.
            
            TEXT:
            {page_text}
            
            Return JSON in this exact structure:
            [
              {{
                "question_number": "1",
                "question_text": "text of question",
                "question_type": "MULTIPLE_CHOICE",
                "options": [
                  {{"key": "A", "text": "option A text"}},
                  {{"key": "B", "text": "option B text"}}
                ],
                "detected_answer": "A",
                "confidence": 0.95,
                "warnings": []
              }}
            ]
            """

            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )

            raw_json = json.loads(response.text)
            questions: List[ExtractedQuestionSchema] = []
            for item in raw_json:
                item["source_pages"] = [page_number]
                questions.append(ExtractedQuestionSchema(**item))
            return questions

        except Exception as e:
            logger.error(f"Gemini AI extraction failed: {e}. Falling back to rule-based parser.")
            return await self._fallback.extract_questions_from_page(page_text, page_number, image_bytes)

    async def parse_answer_key(self, text: str) -> List[AnswerKeyEntrySchema]:
        if not self.api_key:
            return await self._fallback.parse_answer_key(text)

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            prompt = f"""
            Extract all answer key pairs (question number -> correct answer) from this text:
            {text}
            
            Return JSON list:
            [
              {{
                "question_number": "1",
                "answer_text": "A",
                "confidence": 0.98,
                "reference": "1. A"
              }}
            ]
            """
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            raw_json = json.loads(response.text)
            return [AnswerKeyEntrySchema(**item) for item in raw_json]
        except Exception as e:
            logger.error(f"Gemini answer key parse failed: {e}. Falling back to rule-based parser.")
            return await self._fallback.parse_answer_key(text)
