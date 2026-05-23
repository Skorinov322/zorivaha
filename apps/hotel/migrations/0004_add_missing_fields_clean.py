# Generated manually to add missing database fields

from django.db import migrations, models


def add_missing_fields_safely(apps, schema_editor):
    """Add missing fields to hotel_roomcategory table safely (PostgreSQL compatible)"""
    db = schema_editor.connection

    with db.cursor() as cursor:
        # Get existing columns via information_schema (works on both PostgreSQL and SQLite)
        vendor = db.vendor  # 'postgresql' or 'sqlite'

        if vendor == 'postgresql':
            cursor.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'hotel_roomcategory'
            """)
        else:
            cursor.execute("PRAGMA table_info(hotel_roomcategory)")
            existing_columns = {row[1] for row in cursor.fetchall()}
            _add_fields_sqlite(cursor, existing_columns)
            return

        existing_columns = {row[0] for row in cursor.fetchall()}

        fields_to_add = [
            ('weekend_price_per_night', 'DECIMAL(10, 2) NULL'),
            ('thumbnail', 'VARCHAR(100) NULL'),
            ('short_description', 'VARCHAR(255) DEFAULT \'\''),
            ('area_sqm', 'INTEGER DEFAULT 25'),
            ('bed_type', 'VARCHAR(20) DEFAULT \'double\''),
            ('is_featured', 'BOOLEAN DEFAULT FALSE'),
        ]

        for field_name, field_definition in fields_to_add:
            if field_name not in existing_columns:
                try:
                    cursor.execute(
                        f'ALTER TABLE hotel_roomcategory ADD COLUMN {field_name} {field_definition}'
                    )
                    print(f"Added field: {field_name}")
                except Exception as e:
                    print(f"Failed to add field {field_name}: {e}")


def _add_fields_sqlite(cursor, existing_columns):
    fields_to_add = [
        ('weekend_price_per_night', 'DECIMAL(10, 2) NULL'),
        ('thumbnail', 'VARCHAR(100) NULL'),
        ('short_description', 'VARCHAR(255) DEFAULT ""'),
        ('area_sqm', 'INTEGER DEFAULT 25'),
        ('bed_type', 'VARCHAR(20) DEFAULT "double"'),
        ('is_featured', 'BOOLEAN DEFAULT 0'),
    ]
    for field_name, field_definition in fields_to_add:
        if field_name not in existing_columns:
            try:
                cursor.execute(
                    f'ALTER TABLE hotel_roomcategory ADD COLUMN {field_name} {field_definition}'
                )
            except Exception as e:
                print(f"Failed to add field {field_name}: {e}")


class Migration(migrations.Migration):

    dependencies = [
        ('hotel', '0003_rename_max_concurrent_bookings'),
    ]

    operations = [
        migrations.RunPython(add_missing_fields_safely, migrations.RunPython.noop),
    ]
