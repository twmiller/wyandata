# Delete this file and replace it with an empty file that just ensures compatibility
# with systems that might have already applied this migration

from django.db import migrations

class Migration(migrations.Migration):
    """
    This migration is now a no-op since we've incorporated these changes
    into the initial migration. We're keeping this file to maintain compatibility.
    """
    dependencies = [
        ('system', '0001_initial'),
    ]

    operations = [
        # Empty operations - these fields are already in the initial migration
    ]
