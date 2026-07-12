import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
application = get_wsgi_application()
app = application

if "VERCEL" in os.environ:
    from django.core.management import call_command
    import pathlib
    
    db_file = pathlib.Path("/tmp/db.sqlite3")
    # If the database is missing or brand new (0 bytes), run migrate and seed
    if not db_file.exists() or db_file.stat().st_size == 0:
        try:
            print("Vercel cold start: migrating database...")
            call_command("migrate")
            print("Vercel cold start: seeding demo data...")
            call_command("seed_demo")
        except Exception as e:
            print("Vercel cold start database initialization failed:", e)


