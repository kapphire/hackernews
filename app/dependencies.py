from pathlib import Path
from fastapi.templating import Jinja2Templates

from app.database import SessionLocal
from app.filters import tolist


BASE_PATH = Path(__file__).resolve().parent


def get_templates():
    templates = Jinja2Templates(directory=str(BASE_PATH / "templates"), autoescape=False, auto_reload=True)

    templates.env.filters["tolist"] = tolist
    return templates


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
