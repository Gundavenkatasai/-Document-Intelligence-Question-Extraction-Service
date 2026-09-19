import json
import os
from typing import List, Optional
from app.core.config import settings
from app.core.logging import logger
from app.ai.base import (
    DocumentUnderstandingProvider,
    ExtractedQuestionSchema,
    AnswerKeyEntrySchema,
)
from app.ai.mock_provider import MockDocumentUnderstandingProvider


class OpenAIDocumentUnderstandingProvider(DocumentUnderstandingProvider):
    """Document understanding provider powered by OpenAI GPT."""

    def __init__(self):
        self.api_key = settings.AI_API_KEY or os.getenv("OPENAI_API_KEY")
        self.model_name = settings.AI_MODEL or "gpt-4o-mini"
        self._fallback = MockDocumentUnderstandingProvider()

    async def extract_questions_from_page(
        self,
        page_text: str,
        page_number: int,
        image_bytes: Optional[bytes] = None
    ) -> List[ExtractedQuestionSchema]:
        if not self.api_key:
            return await self._fallback.extract_questions_from_page(page_text, page_number, image_bytes)

        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.api_key)

            prompt = f"Extract all exam questions from Page {page_number} into a JSON list with fields: question_number, question_text, question_type, options, detected_answer, confidence, warnings.\n\nTEXT:\n{page_text}"

            response = await client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You extract structured exam questions into JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            raw_data = json.loads(content)
            items = raw_data.get("questions", raw_data if isinstance(raw_data, list) else [])
            questions: List[ExtractedQuestionSchema] = []
            for item in items:
                item["source_pages"] = [page_number]
                questions.append(ExtractedQuestionSchema(**item))
            return questions
        except Exception as e:
            logger.error(f"OpenAI extraction failed: {e}. Falling back to rule-based parser.")
            return await self._fallback.extract_questions_from_page(page_text, page_number, image_bytes)

    async def parse_answer_key(self, text: str) -> List[AnswerKeyEntrySchema]:
        if not self.api_key:
            return await self._fallback.parse_answer_key(text)

        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.api_key)

            response = await client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "Extract answer key mappings into JSON list of items with question_number and answer_text."},
                    {"role": "user", "content": text}
                ],
                response_format={"type": "json_object"}
            )
            raw = json.loads(response.choices[0].message.content)
            items = raw.get("answers", raw if isinstance(raw, list) else [])
            return [AnswerKeyEntrySchema(**item) for item in items]
        except Exception as e:
            logger.error(f"OpenAI answer key parse failed: {e}. Falling back to rule-based parser.")
            return await self._fallback.parse_answer_key(text)
