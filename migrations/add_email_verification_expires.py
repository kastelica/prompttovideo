"""Add email_verification_expires field to users table

Revision ID: add_email_verification_expires
Revises: add_phase7_fields
Create Date: 2024-08-01 02:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_email_verification_expires'
down_revision = 'add_phase7_fields'
branch_labels = None
depends_on = None

def upgrade():
    # Add email_verification_expires column to users table
    op.add_column('users', sa.Column('email_verification_expires', sa.DateTime(), nullable=True))

def downgrade():
    # Remove email_verification_expires column from users table
    op.drop_column('users', 'email_verification_expires') 