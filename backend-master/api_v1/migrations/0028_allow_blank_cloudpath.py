from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('api_v1', '0027_add_sales_to_monthlyloss'),
    ]

    operations = [
        migrations.AlterField(
            model_name='imageupload',
            name='cloud_path',
            field=models.CharField(max_length=500, verbose_name='Cloud 路径', blank=True, null=True),
        ),
    ]
