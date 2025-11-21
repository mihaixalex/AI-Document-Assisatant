"""add conversations table and thread_id

Revision ID: 1913b4dced83
Revises:
Create Date: 2025-01-21 14:23:45.123456

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1913b4dced83'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create conversations table and add thread_id column to documents table.

    This migration supports conversation persistence by:
    1. Creating a conversations table to store conversation metadata
    2. Adding a thread_id column to documents for per-conversation isolation
    3. Adding a foreign key constraint to ensure referential integrity
    """
    # Create conversations table
    op.create_table(
        'conversations',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('thread_id', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('thread_id', name='uq_conversations_thread_id')
    )

    # Create indexes on conversations table
    op.create_index('ix_conversations_thread_id', 'conversations', ['thread_id'])
    op.create_index('ix_conversations_user_id', 'conversations', ['user_id'])
    op.create_index('ix_conversations_created_at', 'conversations', ['created_at'])

    # Add thread_id column to documents table
    op.add_column('documents', sa.Column('thread_id', sa.String(length=255), nullable=True))

    # Add foreign key constraint from documents.thread_id to conversations.thread_id
    # Using SET NULL on delete to preserve documents when conversation is soft-deleted
    op.create_foreign_key(
        'fk_documents_thread_id_conversations',
        'documents', 'conversations',
        ['thread_id'], ['thread_id'],
        ondelete='SET NULL'
    )

    # Create index on documents.thread_id for query performance
    op.create_index('ix_documents_thread_id', 'documents', ['thread_id'])


def downgrade() -> None:
    """
    Reverse the migration by dropping the foreign key constraint,
    indexes, thread_id column, and conversations table.
    """
    # Drop foreign key constraint, index, and column from documents table
    try:
        op.drop_constraint('fk_documents_thread_id_conversations', 'documents', type_='foreignkey')
        op.drop_index('ix_documents_thread_id', table_name='documents')
        op.drop_column('documents', 'thread_id')
    except Exception:
        # Handle case where documents table might not exist or constraints already dropped
        pass

    # Drop indexes and table for conversations
    op.drop_index('ix_conversations_created_at', table_name='conversations')
    op.drop_index('ix_conversations_user_id', table_name='conversations')
    op.drop_index('ix_conversations_thread_id', table_name='conversations')
    op.drop_table('conversations')
