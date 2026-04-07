# Generated manually
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone

class Migration(migrations.Migration):

    dependencies = [
        ('api_v1', '0022_imageupload'), # Use the actual last migration
        migrations.swappable_dependency('auth.User'),
    ]

    operations = [
        migrations.AddField(
            model_name='notice',
            name='level',
            field=models.CharField(default='L', max_length=20),
        ),
        migrations.AddField(
            model_name='notice',
            name='target_type',
            field=models.IntegerField(default=1),
        ),
        migrations.CreateModel(
            name='NoticeTarget',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('notice', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='targets', to='api_v1.notice')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notice_targets', to='auth.user')),
            ],
            options={
                'verbose_name': '通知目标',
                'verbose_name_plural': '通知目标',
                'unique_together': {('notice', 'user')},
            },
        ),
    ]
