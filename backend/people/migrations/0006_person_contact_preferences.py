from django.db import migrations, models


def populate_normalized_wechat(apps, schema_editor):
    Person = apps.get_model("people", "Person")
    for person in Person.objects.exclude(wechat_id__isnull=True).iterator():
        normalized = (person.wechat_id or "").strip().casefold() or None
        Person.objects.filter(pk=person.pk).update(normalized_wechat_id=normalized)


def reset_implicit_whatsapp_opt_ins(apps, schema_editor):
    """Require a fresh, explicit WhatsApp opt-in after this migration.

    The historical field defaulted to true, so stored true values cannot be
    distinguished from an intentional choice. Resetting every row is the
    privacy-safe upgrade path; people can explicitly opt in again later.
    """
    Person = apps.get_model("people", "Person")
    Person.objects.filter(has_whatsapp=True).update(has_whatsapp=False)


class Migration(migrations.Migration):
    dependencies = [
        ("people", "0005_person_normalized_email_person_normalized_phone_and_more")
    ]

    operations = [
        migrations.AddField(
            model_name="person",
            name="normalized_wechat_id",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="person",
            name="preferred_contact",
            field=models.CharField(
                blank=True,
                choices=[
                    ("phone", "Phone"),
                    ("whatsapp", "WhatsApp"),
                    ("wechat", "WeChat"),
                    ("email", "Email"),
                ],
                max_length=20,
                null=True,
            ),
        ),
        migrations.RunPython(
            reset_implicit_whatsapp_opt_ins,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="person",
            name="has_whatsapp",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(populate_normalized_wechat, migrations.RunPython.noop),
    ]
