from django.db import migrations

class Migration(migrations.Migration):
    """
    This migration resets the migration state without making any actual database changes.
    """

    dependencies = [
        ('system', '0003_rename_system_metr_timesta_ef6d0f_idx_system_metr_timesta_898d1b_idx_and_more'),
    ]
    
    # This replaces all other migrations
    replaces = [
        ('system', '0003_fix_indexes'),
        ('system', '0004_auto_20250424_0939'),
        ('system', '0005_auto_20250424_0940'),
    ]

    operations = []
