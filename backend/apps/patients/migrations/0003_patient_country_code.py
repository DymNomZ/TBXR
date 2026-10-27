from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0002_alter_patient_contact_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='patient',
            name='country_code',
            field=models.CharField(default='PH', max_length=2),
        ),
    ]
