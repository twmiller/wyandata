from django.db import migrations

class Migration(migrations.Migration):
    """
    This migration merges the two migration branches:
    - The branch with 0004_auto_20250424_0939 and 0005_auto_20250424_0940
    - The branch with 0006_handle_index_conflict
    """

    dependencies = [
        ('system', '0005_auto_20250424_0940'),
        ('system', '0006_handle_index_conflict'),
    ]

    operations = [
        # No operations needed, this migration just merges the branches
    ]
