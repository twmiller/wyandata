# Generated manually

from django.db import migrations, models
import uuid

class Migration(migrations.Migration):

    dependencies = [
        ('system', '0001_initial'),  # Adjust this to your actual initial migration
    ]

    operations = [
        migrations.AddField(
            model_name='host',
            name='client_id',
            field=models.UUIDField(blank=True, help_text='Client-generated persistent UUID', null=True, unique=True),
        ),
        migrations.AddField(
            model_name='host',
            name='short_name',
            field=models.CharField(blank=True, help_text='User-friendly short name for this host', max_length=100),
        ),
        migrations.AddField(
            model_name='host',
            name='description',
            field=models.TextField(blank=True, help_text="Description of this host's purpose or location"),
        ),
    ]
