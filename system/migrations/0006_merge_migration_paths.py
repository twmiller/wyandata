from django.db import migrations

class Migration(migrations.Migration):
    """
    This migration merges conflicting migration paths.
    """

    dependencies = [
        ('system', '0003_rename_system_metr_timesta_ef6d0f_idx_system_metr_timesta_898d1b_idx_and_more'),
        ('system', '0005_auto_20250424_0940'),
    ]

    operations = []
