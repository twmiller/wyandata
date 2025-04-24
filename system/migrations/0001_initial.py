# Generated manually

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Host',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('hostname', models.CharField(max_length=255)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('system_type', models.CharField(choices=[('LINUX', 'Linux'), ('MACOS', 'macOS'), ('RASPBERRY', 'Raspberry Pi')], max_length=50)),
                ('cpu_model', models.CharField(blank=True, max_length=255)),
                ('cpu_cores', models.IntegerField(default=0)),
                ('ram_total', models.BigIntegerField(default=0)),
                ('gpu_model', models.CharField(blank=True, max_length=255)),
                ('os_version', models.CharField(blank=True, max_length=255)),
                ('last_seen', models.DateTimeField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='MetricType',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('unit', models.CharField(blank=True, max_length=50)),
                ('data_type', models.CharField(choices=[('FLOAT', 'Float'), ('INT', 'Integer'), ('STR', 'String'), ('BOOL', 'Boolean')], default='FLOAT', max_length=20)),
                ('category', models.CharField(choices=[('CPU', 'CPU'), ('MEMORY', 'Memory'), ('STORAGE', 'Storage'), ('NETWORK', 'Network'), ('SYSTEM', 'System'), ('TEMPERATURE', 'Temperature'), ('OTHER', 'Other')], default='OTHER', max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='StorageDevice',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('device_type', models.CharField(choices=[('SSD', 'SSD'), ('HDD', 'HDD'), ('NVME', 'NVMe'), ('OTHER', 'Other')], default='OTHER', max_length=50)),
                ('total_bytes', models.BigIntegerField(default=0)),
                ('host', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='storage_devices', to='system.host')),
            ],
        ),
        migrations.CreateModel(
            name='NetworkInterface',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('mac_address', models.CharField(blank=True, max_length=17)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('is_up', models.BooleanField(default=True)),
                ('host', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='network_interfaces', to='system.host')),
            ],
        ),
        migrations.CreateModel(
            name='MetricValue',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('float_value', models.FloatField(blank=True, null=True)),
                ('int_value', models.BigIntegerField(blank=True, null=True)),
                ('str_value', models.TextField(blank=True, null=True)),
                ('bool_value', models.BooleanField(blank=True, null=True)),
                ('host', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='metrics', to='system.host')),
                ('metric_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='values', to='system.metrictype')),
                ('network_interface', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='metrics', to='system.networkinterface')),
                ('storage_device', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='metrics', to='system.storagedevice')),
            ],
            options={
                'indexes': [models.Index(fields=['timestamp'], name='system_metr_timesta_ef6d0f_idx'), models.Index(fields=['host', 'metric_type', 'timestamp'], name='system_metr_host_id_c60192_idx')],
            },
        ),
    ]
