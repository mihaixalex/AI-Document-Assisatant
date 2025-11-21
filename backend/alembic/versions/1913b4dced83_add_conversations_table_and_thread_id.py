"""add_conversations_table_and_thread_id

Revision ID: 1913b4dced83
Revises: 
Create Date: 2025-11-21 15:17:21.485214

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1913b4dced83'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Creates:
    1. conversations table for managing chat history metadata
    2. thread_id column in documents table with index

    Note: PostgresSaver checkpoint tables (checkpoints, writes) are created
    automatically by PostgresSaver.setup() and are NOT managed by Alembic.
    """
    # Create conversations table
    op.create_table(
        'conversations',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('thread_id', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('thread_id', name='uq_conversations_thread_id')
    )

    # Create index on thread_id for faster lookups
    op.create_index('ix_conversations_thread_id', 'conversations', ['thread_id'])

    # Create index on user_id for filtering by user
    op.create_index('ix_conversations_user_id', 'conversations', ['user_id'])

    # Create index on created_at for sorting
    op.create_index('ix_conversations_created_at', 'conversations', ['created_at'])

    # Add thread_id column to documents table if it exists
    # Using batch_alter_table to check if table exists first
    try:
        op.add_column('documents', sa.Column('thread_id', sa.String(length=255), nullable=True))

        # Create index on documents.thread_id
        op.create_index('ix_documents_thread_id', 'documents', ['thread_id'])
    except Exception:
        # If documents table doesn't exist yet, skip this step
        # The Supabase vector store will create it when first used
        pass


def downgrade() -> None:
    """Downgrade schema.

    Removes:
    1. thread_id column and index from documents table
    2. conversations table and all its indexes
    """
    # Drop indexes and column from documents table if they exist
    try:
        op.drop_index('ix_documents_thread_id', table_name='documents')
        op.drop_column('documents', 'thread_id')
    except Exception:
        # If table or column doesn't exist, skip
        pass

    # Drop conversations table indexes
    op.drop_index('ix_conversations_created_at', table_name='conversations')
    op.drop_index('ix_conversations_user_id', table_name='conversations')
    op.drop_index('ix_conversations_thread_id', table_name='conversations')

    # Drop conversations table
    op.drop_table('conversations')
