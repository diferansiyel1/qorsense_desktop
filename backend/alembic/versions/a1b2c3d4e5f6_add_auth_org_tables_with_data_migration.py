"""add_auth_org_tables_with_data_migration

Revision ID: a1b2c3d4e5f6
Revises: e18689250622
Create Date: 2025-12-09 12:15:00.000000

CRITICAL: This migration converts the database to multi-tenant architecture.
- Converts Integer IDs to UUID format (String(36))
- Adds new Role enum (SUPER_ADMIN, ORG_ADMIN, ENGINEER)
- Creates Default Organization for existing sensors
- Preserves all existing sensor data and relationships

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite
from datetime import datetime
import uuid


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str]] = 'e18689250622'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Default Organization UUID (consistent for all installations)
DEFAULT_ORG_UUID = "00000000-0000-0000-0000-000000000001"
DEFAULT_ORG_NAME = "Default Organization"


def upgrade() -> None:
    """
    Upgrade to multi-tenant architecture with data preservation.
    
    Migration Strategy:
    1. Create new tables with UUID-based IDs
    2. Migrate existing organization data
    3. Create default organization for orphan sensors
    4. Update sensor foreign keys
    5. Create new users table with Role enum
    6. Drop legacy tables and constraints
    """
    
    # Get connection for data operations
    connection = op.get_bind()
    
    # =========================================================================
    # STEP 1: Create new organizations_new table with UUID
    # =========================================================================
    op.create_table(
        'organizations_new',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('subscription_plan', sa.String(50), default='Free'),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_organizations_new_id', 'organizations_new', ['id'], unique=False)
    op.create_index('ix_organizations_new_name', 'organizations_new', ['name'], unique=True)
    
    # =========================================================================
    # STEP 2: Migrate existing organizations with new UUIDs
    # =========================================================================
    # First, get existing organizations
    existing_orgs = connection.execute(
        sa.text("SELECT id, name, subscription_plan FROM organizations")
    ).fetchall()
    
    # Map old integer IDs to new UUIDs
    org_id_mapping = {}
    
    for org in existing_orgs:
        old_id = org[0]
        new_uuid = str(uuid.uuid4())
        org_id_mapping[old_id] = new_uuid
        
        connection.execute(
            sa.text("""
                INSERT INTO organizations_new (id, name, subscription_plan, created_at)
                VALUES (:id, :name, :plan, :created_at)
            """),
            {
                'id': new_uuid,
                'name': org[1],
                'plan': org[2] or 'Free',
                'created_at': datetime.utcnow()
            }
        )
    
    # =========================================================================
    # STEP 3: Create Default Organization for orphan sensors
    # =========================================================================
    # Check if there are sensors without org_id or with non-existent org_id
    connection.execute(
        sa.text("""
            INSERT INTO organizations_new (id, name, subscription_plan, created_at)
            VALUES (:id, :name, :plan, :created_at)
        """),
        {
            'id': DEFAULT_ORG_UUID,
            'name': DEFAULT_ORG_NAME,
            'plan': 'Free',
            'created_at': datetime.utcnow()
        }
    )
    
    # =========================================================================
    # STEP 4: Create new sensors table with String FK
    # =========================================================================
    op.create_table(
        'sensors_new',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations_new.id', ondelete='SET NULL'), nullable=True),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('source_type', sa.Enum('CSV', 'SCADA', 'IoT', name='sourcetype', create_constraint=False), nullable=True),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_sensors_new_id', 'sensors_new', ['id'], unique=False)
    op.create_index('ix_sensors_new_organization_id', 'sensors_new', ['organization_id'], unique=False)
    
    # =========================================================================
    # STEP 5: Migrate sensors with updated FK (preserve all data!)
    # =========================================================================
    existing_sensors = connection.execute(
        sa.text("SELECT id, org_id, name, location, source_type, config FROM sensors")
    ).fetchall()
    
    for sensor in existing_sensors:
        old_org_id = sensor[1]
        # Map to new UUID or use Default Organization
        new_org_id = org_id_mapping.get(old_org_id, DEFAULT_ORG_UUID) if old_org_id else DEFAULT_ORG_UUID
        
        connection.execute(
            sa.text("""
                INSERT INTO sensors_new (id, organization_id, name, location, source_type, config, created_at)
                VALUES (:id, :org_id, :name, :location, :source_type, :config, :created_at)
            """),
            {
                'id': sensor[0],
                'org_id': new_org_id,
                'name': sensor[2],
                'location': sensor[3],
                'source_type': sensor[4],
                'config': sensor[5],
                'created_at': datetime.utcnow()
            }
        )
    
    # =========================================================================
    # STEP 6: Update sensor_readings and analysis_results FK references
    # =========================================================================
    # These tables reference sensors.id which is String, so no change needed
    # Just need to update the FK constraint after table rename
    
    # =========================================================================
    # STEP 7: Create new users table with Role enum
    # =========================================================================
    # Drop old users table if exists (it has different structure)
    try:
        op.drop_table('users')
    except Exception:
        pass  # Table might not exist
    
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('role', sa.Enum('super_admin', 'org_admin', 'engineer', name='role', create_constraint=False), nullable=False, default='engineer'),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations_new.id', ondelete='CASCADE'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_users_id', 'users', ['id'], unique=False)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_organization_id', 'users', ['organization_id'], unique=False)
    
    # =========================================================================
    # STEP 8: Handle FK constraints for sensor_readings
    # =========================================================================
    # SQLite doesn't support ALTER FOREIGN KEY, so we need to recreate tables
    # For now, we'll just drop and recreate the FK constraint via batch operations
    
    # Create temporary tables with correct FKs
    op.create_table(
        'sensor_readings_new',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('sensor_id', sa.String(50), sa.ForeignKey('sensors_new.id', ondelete='CASCADE'), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('value', sa.Float(), nullable=False),
    )
    op.create_index('ix_sensor_readings_new_id', 'sensor_readings_new', ['id'], unique=False)
    op.create_index('ix_sensor_readings_new_sensor_id', 'sensor_readings_new', ['sensor_id'], unique=False)
    op.create_index('ix_sensor_readings_new_timestamp', 'sensor_readings_new', ['timestamp'], unique=False)
    
    # Migrate sensor readings data
    connection.execute(
        sa.text("""
            INSERT INTO sensor_readings_new (id, sensor_id, timestamp, value)
            SELECT id, sensor_id, timestamp, value FROM sensor_readings
        """)
    )
    
    # Create temporary analysis_results table
    op.create_table(
        'analysis_results_new',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('sensor_id', sa.String(50), sa.ForeignKey('sensors_new.id', ondelete='CASCADE'), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.Column('health_score', sa.Float(), nullable=True),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('metrics', sa.JSON(), nullable=True),
        sa.Column('diagnosis', sa.Text(), nullable=True),
        sa.Column('recommendation', sa.Text(), nullable=True),
    )
    op.create_index('ix_analysis_results_new_id', 'analysis_results_new', ['id'], unique=False)
    op.create_index('ix_analysis_results_new_sensor_id', 'analysis_results_new', ['sensor_id'], unique=False)
    op.create_index('ix_analysis_results_new_timestamp', 'analysis_results_new', ['timestamp'], unique=False)
    
    # Migrate analysis results data
    connection.execute(
        sa.text("""
            INSERT INTO analysis_results_new (id, sensor_id, timestamp, health_score, status, metrics, diagnosis, recommendation)
            SELECT id, sensor_id, timestamp, health_score, status, metrics, diagnosis, recommendation FROM analysis_results
        """)
    )
    
    # =========================================================================
    # STEP 9: Drop old tables and rename new tables
    # =========================================================================
    # Drop old tables (order matters due to FK constraints)
    op.drop_index('ix_sensor_readings_timestamp', table_name='sensor_readings')
    op.drop_index('ix_sensor_readings_sensor_id', table_name='sensor_readings')
    op.drop_index('ix_sensor_readings_id', table_name='sensor_readings')
    op.drop_table('sensor_readings')
    
    op.drop_index('ix_analysis_results_sensor_id', table_name='analysis_results')
    op.drop_index('ix_analysis_results_id', table_name='analysis_results')
    op.drop_table('analysis_results')
    
    op.drop_index('ix_sensors_id', table_name='sensors')
    op.drop_table('sensors')
    
    op.drop_index('ix_organizations_name', table_name='organizations')
    op.drop_index('ix_organizations_id', table_name='organizations')
    op.drop_table('organizations')
    
    # Rename new tables to original names
    op.rename_table('organizations_new', 'organizations')
    op.rename_table('sensors_new', 'sensors')
    op.rename_table('sensor_readings_new', 'sensor_readings')
    op.rename_table('analysis_results_new', 'analysis_results')
    
    # Rename indexes to match original names
    # SQLite doesn't support renaming indexes, so we'll create new ones
    # The indexes were already created with the _new suffix, 
    # but since we renamed tables, we need to drop and recreate
    
    # For organizations
    op.drop_index('ix_organizations_new_id', table_name='organizations')
    op.drop_index('ix_organizations_new_name', table_name='organizations')
    op.create_index('ix_organizations_id', 'organizations', ['id'], unique=False)
    op.create_index('ix_organizations_name', 'organizations', ['name'], unique=True)
    
    # For sensors
    op.drop_index('ix_sensors_new_id', table_name='sensors')
    op.drop_index('ix_sensors_new_organization_id', table_name='sensors')
    op.create_index('ix_sensors_id', 'sensors', ['id'], unique=False)
    op.create_index('ix_sensors_organization_id', 'sensors', ['organization_id'], unique=False)
    
    # For sensor_readings
    op.drop_index('ix_sensor_readings_new_id', table_name='sensor_readings')
    op.drop_index('ix_sensor_readings_new_sensor_id', table_name='sensor_readings')
    op.drop_index('ix_sensor_readings_new_timestamp', table_name='sensor_readings')
    op.create_index('ix_sensor_readings_id', 'sensor_readings', ['id'], unique=False)
    op.create_index('ix_sensor_readings_sensor_id', 'sensor_readings', ['sensor_id'], unique=False)
    op.create_index('ix_sensor_readings_timestamp', 'sensor_readings', ['timestamp'], unique=False)
    
    # For analysis_results
    op.drop_index('ix_analysis_results_new_id', table_name='analysis_results')
    op.drop_index('ix_analysis_results_new_sensor_id', table_name='analysis_results')
    op.drop_index('ix_analysis_results_new_timestamp', table_name='analysis_results')
    op.create_index('ix_analysis_results_id', 'analysis_results', ['id'], unique=False)
    op.create_index('ix_analysis_results_sensor_id', 'analysis_results', ['sensor_id'], unique=False)
    op.create_index('ix_analysis_results_timestamp', 'analysis_results', ['timestamp'], unique=False)


def downgrade() -> None:
    """
    Downgrade from multi-tenant architecture.
    
    WARNING: This will lose UUID-based IDs and convert back to Integer IDs.
    Some data relationships may be affected.
    """
    connection = op.get_bind()
    
    # =========================================================================
    # STEP 1: Create legacy organizations table with Integer ID
    # =========================================================================
    op.create_table(
        'organizations_legacy',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('subscription_plan', sa.String(), nullable=True),
    )
    
    # Migrate organizations (UUID to Integer sequence)
    existing_orgs = connection.execute(
        sa.text("SELECT id, name, subscription_plan FROM organizations ORDER BY created_at")
    ).fetchall()
    
    uuid_to_int_map = {}
    for i, org in enumerate(existing_orgs, start=1):
        uuid_to_int_map[org[0]] = i
        connection.execute(
            sa.text("""
                INSERT INTO organizations_legacy (id, name, subscription_plan)
                VALUES (:id, :name, :plan)
            """),
            {'id': i, 'name': org[1], 'plan': org[2]}
        )
    
    # =========================================================================
    # STEP 2: Create legacy sensors table
    # =========================================================================
    op.create_table(
        'sensors_legacy',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('organizations_legacy.id'), nullable=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('source_type', sa.Enum('CSV', 'SCADA', 'IoT', name='sourcetype'), nullable=True),
        sa.Column('config', sa.JSON(), nullable=True),
    )
    
    # Migrate sensors with mapped org_id
    existing_sensors = connection.execute(
        sa.text("SELECT id, organization_id, name, location, source_type, config FROM sensors")
    ).fetchall()
    
    for sensor in existing_sensors:
        new_org_id = uuid_to_int_map.get(sensor[1])
        connection.execute(
            sa.text("""
                INSERT INTO sensors_legacy (id, org_id, name, location, source_type, config)
                VALUES (:id, :org_id, :name, :location, :source_type, :config)
            """),
            {
                'id': sensor[0],
                'org_id': new_org_id,
                'name': sensor[2],
                'location': sensor[3],
                'source_type': sensor[4],
                'config': sensor[5]
            }
        )
    
    # =========================================================================
    # STEP 3: Create legacy reading and analysis tables
    # =========================================================================
    op.create_table(
        'sensor_readings_legacy',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('sensor_id', sa.String(), sa.ForeignKey('sensors_legacy.id'), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('value', sa.Float(), nullable=False),
    )
    
    connection.execute(
        sa.text("""
            INSERT INTO sensor_readings_legacy (id, sensor_id, timestamp, value)
            SELECT id, sensor_id, timestamp, value FROM sensor_readings
        """)
    )
    
    op.create_table(
        'analysis_results_legacy',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('sensor_id', sa.String(), sa.ForeignKey('sensors_legacy.id'), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('health_score', sa.Float(), nullable=True),
        sa.Column('metrics', sa.JSON(), nullable=True),
        sa.Column('diagnosis', sa.Text(), nullable=True),
        sa.Column('recommendation', sa.Text(), nullable=True),
    )
    
    connection.execute(
        sa.text("""
            INSERT INTO analysis_results_legacy (id, sensor_id, timestamp, health_score, metrics, diagnosis, recommendation)
            SELECT id, sensor_id, timestamp, health_score, metrics, diagnosis, recommendation FROM analysis_results
        """)
    )
    
    # =========================================================================
    # STEP 4: Drop new tables and rename legacy tables
    # =========================================================================
    op.drop_table('users')
    op.drop_table('sensor_readings')
    op.drop_table('analysis_results')
    op.drop_table('sensors')
    op.drop_table('organizations')
    
    op.rename_table('organizations_legacy', 'organizations')
    op.rename_table('sensors_legacy', 'sensors')
    op.rename_table('sensor_readings_legacy', 'sensor_readings')
    op.rename_table('analysis_results_legacy', 'analysis_results')
    
    # Recreate indexes
    op.create_index('ix_organizations_id', 'organizations', ['id'], unique=False)
    op.create_index('ix_organizations_name', 'organizations', ['name'], unique=True)
    op.create_index('ix_sensors_id', 'sensors', ['id'], unique=False)
    op.create_index('ix_sensor_readings_id', 'sensor_readings', ['id'], unique=False)
    op.create_index('ix_sensor_readings_sensor_id', 'sensor_readings', ['sensor_id'], unique=False)
    op.create_index('ix_sensor_readings_timestamp', 'sensor_readings', ['timestamp'], unique=False)
    op.create_index('ix_analysis_results_id', 'analysis_results', ['id'], unique=False)
    op.create_index('ix_analysis_results_sensor_id', 'analysis_results', ['sensor_id'], unique=False)
