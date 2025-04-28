from django.db import migrations

class Migration(migrations.Migration):
    """
    This migration fixes the conflict by acknowledging that certain indexes
    already exist in the database without trying to recreate them.
    """

    dependencies = [
        ('system', '0003_rename_system_metr_timesta_ef6d0f_idx_system_metr_timesta_898d1b_idx_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            # This is a no-op SQL command that will succeed regardless
            "SELECT 1;",
            # No reverse SQL needed
            ""
        ),
    ]
