from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("people", "0006_person_contact_preferences")]

    operations = [
        migrations.SeparateDatabaseAndState(
            # Keep index creation in a separate transaction from the 0006 data
            # updates. IF NOT EXISTS also supports databases where the earlier,
            # published form of 0006 already created this exact index.
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "CREATE INDEX IF NOT EXISTS "
                        '"person_church__9b7c6c_idx" ON "person" '
                        '("church_id", "normalized_wechat_id")'
                    ),
                    reverse_sql=('DROP INDEX IF EXISTS "person_church__9b7c6c_idx"'),
                )
            ],
            state_operations=[
                migrations.AddIndex(
                    model_name="person",
                    index=models.Index(
                        fields=["church", "normalized_wechat_id"],
                        name="person_church__9b7c6c_idx",
                    ),
                )
            ],
        ),
    ]
