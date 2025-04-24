from django.db import migrations

class Migration(migrations.Migration):
    """
    This migration fixes the issue with missing indexes.
    Instead of renaming indexes that don't exist, we'll skip this migration.
    The indexes will be created properly when we run the initial migration.
    """
    dependencies = [
        ('system', '0002_add_client_id_short_name_description'),
    ]

    operations = [
        # Empty operations list - we're essentially creating a no-op migration
        # to bridge the gap between 0002 and any future migrations
    ]
