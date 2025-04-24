from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('system', '0003_rename_system_metr_timesta_ef6d0f_idx_system_metr_timesta_898d1b_idx_and_more'),
    ]

    operations = [
        # Add the indexes with the proper names
        migrations.AddIndex(
            model_name='metricvalue',
            index=models.Index(fields=['timestamp'], name='system_metr_timesta_898d1b_idx'),
        ),
        migrations.AddIndex(
            model_name='metricvalue',
            index=models.Index(fields=['host', 'metric_type', 'timestamp'], name='system_metr_host_id_aa5f0f_idx'),
        ),
    ]
