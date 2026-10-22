import django.db.models.deletion
from django.db import migrations, models


def criar_etapa_inicial(apps, schema_editor):
    Etapa = apps.get_model("fichas", "Etapa")

    Etapa.objects.using(schema_editor.connection.alias).create(
        id=1,
        nome="Recebidas",
        ordem=1,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("fichas", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Etapa",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("nome", models.CharField(max_length=50)),
                ("ordem", models.PositiveIntegerField(default=0)),
            ],
        ),
        migrations.RunPython(
            criar_etapa_inicial,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AddField(
            model_name="ficha",
            name="etapa",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.PROTECT,
                to="fichas.etapa",
            ),
        ),
    ]