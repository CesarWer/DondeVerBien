# DondeVer (demo)

Pequeña demo en Django para listar series y películas por plataforma en la región de Argentina.

Características:
- Página principal con plataformas (imágenes)
- Al seleccionar una plataforma se accede a la biblioteca de títulos disponibles en Argentina
- Filtrado por género y tipo (película/serie)
- Orden por popularidad ascendente/descendente
- Búsqueda sobre los títulos filtrados

Requisitos
- Python 3.8+
- Instalar dependencias: pip install -r requirements.txt

Instrucciones rápidas (Windows PowerShell):

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata
# (Alternatively) load sample data via management command:
python manage.py loadsample
python manage.py runserver
```

Luego abrir http://127.0.0.1:8000/
