from django.db import migrations


def require_transport_review(apps, schema_editor):
    EventRegistration = apps.get_model("events", "EventRegistration")
    if EventRegistration.objects.filter(needs_transport=True).exists():
        raise RuntimeError(
            "Event registrations with transport requests require manual review "
            "and explicit confirmation before removing needs_transport. Resolve "
            "those records, then rerun this migration."
        )


class Migration(migrations.Migration):
    dependencies = [("events", "0005_publicregistrationidentitylock")]

    operations = [
        migrations.RunPython(require_transport_review, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="eventregistration",
            name="needs_transport",
        ),
    ]
