# Generated manually to add missing database fields

from django.db import migrations


def add_missing_fields_safely(apps, schema_editor):
    """Add missing fields to hotel_roomcategory table safely"""
    db_alias = schema_editor.connection.alias
    
    # List of fields to add with their SQL definitions
    fields_to_add = [
        ('weekend_price_per_night', 'DECIMAL(10, 2) NULL'),
        ('thumbnail', 'VARCHAR(100) NULL'),
        ('short_description', 'VARCHAR(255) DEFAULT ""'),
        ('area_sqm', 'INTEGER DEFAULT 25'),
        ('bed_type', 'VARCHAR(20) DEFAULT "double"'),
        ('is_featured', 'BOOLEAN DEFAULT 0'),
    ]
    
    with schema_editor.connection.cursor() as cursor:
        # Get existing columns
        cursor.execute("PRAGMA table_info(hotel_roomcategory)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        
        # Add missing fields
        for field_name, field_definition in fields_to_add:
            if field_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE hotel_roomcategory ADD COLUMN {field_name} {field_definition}")
                    print(f"Added field: {field_name}")
                except Exception as e:
                    print(f"Failed to add field {field_name}: {e}")


class Migration(migrations.Migration):

    dependencies = [
        ('hotel', '0003_rename_max_concurrent_bookings'),
    ]

    operations = [
        migrations.RunPython(add_missing_fields_safely, migrations.RunPython.noop),
    ]