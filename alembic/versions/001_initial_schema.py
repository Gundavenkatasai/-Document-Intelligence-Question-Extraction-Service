"""initial schema

Revision ID: 001_initial
Revises: 
Create Date: 2026-09-19 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Users
    op.create_table(
        "users",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # 2. Document Groups
    op.create_table(
        "document_groups",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("user_id", sa.CHAR(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_document_groups_user_id", "document_groups", ["user_id"])

    # 3. Documents
    op.create_table(
        "documents",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("user_id", sa.CHAR(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("group_id", sa.CHAR(36), sa.ForeignKey("document_groups.id", ondelete="SET NULL"), nullable=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("storage_path", sa.String(512), nullable=False),
        sa.Column("file_type", sa.String(50), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="PENDING"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("total_pages", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_pages", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("doc_metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_documents_user_id", "documents", ["user_id"])
    op.create_index("ix_documents_group_id", "documents", ["group_id"])
    op.create_index("ix_documents_status", "documents", ["status"])

    # 4. Document Pages
    op.create_table(
        "document_pages",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("document_id", sa.CHAR(36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("extraction_method", sa.String(50), nullable=False, server_default="native_text"),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("character_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("page_image_path", sa.String(512), nullable=True),
        sa.Column("has_visual_content", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("page_metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_document_pages_document_id", "document_pages", ["document_id"])

    # 5. Processing Jobs
    op.create_table(
        "processing_jobs",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("document_id", sa.CHAR(36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="PENDING"),
        sa.Column("stage", sa.String(100), nullable=False, server_default="INITIALIZING"),
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_seconds", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_details", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_processing_jobs_document_id", "processing_jobs", ["document_id"])
    op.create_index("ix_processing_jobs_status", "processing_jobs", ["status"])

    # 6. Extracted Questions
    op.create_table(
        "extracted_questions",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("document_id", sa.CHAR(36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_number", sa.String(50), nullable=True),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(50), nullable=False, server_default="UNKNOWN"),
        sa.Column("source_pages", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("review_status", sa.String(50), nullable=False, server_default="ACCEPTED"),
        sa.Column("has_visual_content", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("visual_metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("raw_metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("warnings", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_extracted_questions_document_id", "extracted_questions", ["document_id"])
    op.create_index("ix_extracted_questions_question_number", "extracted_questions", ["question_number"])

    # 7. Question Options
    op.create_table(
        "question_options",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("question_id", sa.CHAR(36), sa.ForeignKey("extracted_questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("option_key", sa.String(50), nullable=False),
        sa.Column("option_text", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_question_options_question_id", "question_options", ["question_id"])

    # 8. Question Answers
    op.create_table(
        "question_answers",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("question_id", sa.CHAR(36), sa.ForeignKey("extracted_questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_document_id", sa.CHAR(36), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("answer_text", sa.Text(), nullable=True),
        sa.Column("answer_key_reference", sa.String(100), nullable=True),
        sa.Column("match_type", sa.String(50), nullable=False, server_default="not_available"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("raw_metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_question_answers_question_id", "question_answers", ["question_id"])

    # 9. Review Items
    op.create_table(
        "review_items",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("document_id", sa.CHAR(36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_id", sa.CHAR(36), sa.ForeignKey("extracted_questions.id", ondelete="CASCADE"), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="PENDING"),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("warnings", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_review_items_document_id", "review_items", ["document_id"])
    op.create_index("ix_review_items_question_id", "review_items", ["question_id"])
    op.create_index("ix_review_items_status", "review_items", ["status"])


def downgrade() -> None:
    op.drop_table("review_items")
    op.drop_table("question_answers")
    op.drop_table("question_options")
    op.drop_table("extracted_questions")
    op.drop_table("processing_jobs")
    op.drop_table("document_pages")
    op.drop_table("documents")
    op.drop_table("document_groups")
    op.drop_table("users")
