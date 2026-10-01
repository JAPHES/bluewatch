from django.db import migrations


TAITA_TAVETA_WARDS = (
    "Wundanyi/Mbale",
    "Werugha",
    "Wumingu/Kishushe",
    "Mwanda/Mghange",
    "Ronge",
    "Mwatate",
    "Bura",
    "Chawia",
    "Wusi/Kishamba",
    "Mbololo",
    "Saghala",
    "Kaloleni",
    "Marungu",
    "Kasigau",
    "Ngolia",
    "Challa",
    "Mahoo",
    "Bomani",
    "Mboghoni",
    "Mata",
)


def add_taita_taveta(apps, schema_editor):
    County = apps.get_model("locations", "County")
    Ward = apps.get_model("locations", "Ward")
    county, _ = County.objects.update_or_create(
        name="Taita Taveta",
        defaults={"code": "006", "is_coastal": False, "is_active": True},
    )
    for name in TAITA_TAVETA_WARDS:
        Ward.objects.get_or_create(county=county, name=name)


class Migration(migrations.Migration):
    dependencies = [("locations", "0001_initial")]
    # Administrative reference data is intentionally retained on reversal so
    # reports and other protected operational records never become orphaned.
    operations = [migrations.RunPython(add_taita_taveta, migrations.RunPython.noop)]
