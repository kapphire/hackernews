from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from pathlib import Path

from app.routers import news
from app import models
from app.database import engine, SessionLocal
from app.env import init_data

BASE_PATH = Path(__file__).resolve().parent
models.Base.metadata.create_all(bind=engine)

db = SessionLocal()

# init_data(models.Embedding.index_flat_l2(db))
init_data(models.Embedding, db)


app = FastAPI()

app.mount("/static", StaticFiles(directory=str(BASE_PATH / "static")), name="static")

app.include_router(news.router)        
