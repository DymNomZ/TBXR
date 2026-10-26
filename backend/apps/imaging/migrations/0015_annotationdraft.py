from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('imaging', '0014_xrayrecord_status_before_review'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AnnotationDraft',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bounding_boxes', models.JSONField(default=list)),
                ('notes', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('radiologist', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='annotation_drafts', to=settings.AUTH_USER_MODEL)),
                ('xray_record', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='annotation_drafts', to='imaging.xrayrecord')),
            ],
            options={
                'ordering': ['-updated_at'],
                'unique_together': {('xray_record', 'radiologist')},
            },
        ),
    ]
