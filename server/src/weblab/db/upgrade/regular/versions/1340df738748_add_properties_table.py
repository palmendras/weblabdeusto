"""Add *Properties tables, and Locations to the UserUsedExperiment table

Revision ID: 1340df738748
Revises: 3fab9480c190
Create Date: 2015-06-02 16:49:57.936592

"""

# revision identifiers, used by Alembic.
revision = '1340df738748'
down_revision = '3fab9480c190'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('ClientProperties',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.Unicode(length=50), nullable=False),
    sa.Column('_value', sa.UnicodeText(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('ServerProperties',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.Unicode(length=50), nullable=False),
    sa.Column('_value', sa.UnicodeText(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column(u'UserUsedExperiment', sa.Column('city', sa.Unicode(length=255), nullable=True))
    op.add_column(u'UserUsedExperiment', sa.Column('hostname', sa.Unicode(length=255), nullable=True))
    op.add_column(u'UserUsedExperiment', sa.Column('most_specific_subdivision', sa.Unicode(length=255), nullable=True))
    op.add_column(u'UserUsedExperiment', sa.Column('country', sa.Unicode(length=255), nullable=True))
    ### end Alembic commands ###
    op.create_index('ix_ClientProperties_name', 'ClientProperties', ['name'])
    op.create_index('ix_ServerProperties_name', 'ServerProperties', ['name'])
    op.create_index('ix_UserUsedExperiment_city', 'UserUsedExperiment', ['city'])
    op.create_index('ix_UserUsedExperiment_hostname', 'UserUsedExperiment', ['hostname'])
    op.create_index('ix_UserUsedExperiment_most_specific_subdivision', 'UserUsedExperiment', ['most_specific_subdivision'])
    op.create_index('ix_UserUsedExperiment_country', 'UserUsedExperiment', ['country'])


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column(u'UserUsedExperiment', 'country')
    op.drop_column(u'UserUsedExperiment', 'most_specific_subdivision')
    op.drop_column(u'UserUsedExperiment', 'hostname')
    op.drop_column(u'UserUsedExperiment', 'city')
    op.drop_table('ServerProperties')
    op.drop_table('ClientProperties')
    ### end Alembic commands ###
