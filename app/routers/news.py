from typing import Union
from sqlalchemy.orm import Session
from fastapi import Depends, APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi_cache import caches
from fastapi_cache.backends.memory import CACHE_KEY
from app.models import Hackernews, Embedding
from app.dependencies import (
    get_db,
    get_templates,
)

router = APIRouter()


def memory_cache():
    return caches.get(CACHE_KEY)


@router.get("/")
async def home(
    request: Request,
    db: Session = Depends(get_db),
    templates: Jinja2Templates = Depends(get_templates),
    q: Union[str, None] = None,
) -> dict:
    """
    Root GET
    """
    hackernews = []
    if q:
        try:
            hackernews = Hackernews.filter_by_query(db, q)
            # hackernews = Hackernews.filter_by_ids(db, filtered)
        except Exception as e:
            print(e)
            pass
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "hackernews": hackernews,
            "query": q,}
    )


@router.get("/embedding/")
async def update_embedding(db: Session = Depends(get_db)):
    try:
        return {"message": "success"}
    except Exception as e:
        return {"message": str(e)}


@router.get("/upload/news/")
async def update_news(db: Session = Depends(get_db)):
    try:
        Hackernews.import_csv(db)
    except Exception as e:
        return {"message": str(e)}
    return {"message": "success"}


@router.get("/test")
async def check_news(db: Session = Depends(get_db)):
    try:
        import pickle
        import numpy as np
        # print(db.query(Hackernews).filter(Hackernews.embedding != None).count())
        # instance = db.query(Hackernews).first()
        # print(pickle.loads(instance.embedding))


        # e1 = []
        # for news in db.query(Hackernews):
        #     e1.append(pickle.loads(news.embedding))
        # e1 = np.concatenate(e1)
        # try:
        #     instance = Embedding(data=pickle.dumps(e1))
        #     db.add(instance)
        #     db.commit()
        #     db.refresh(instance)
        # except Exception as e:
        #     print(e)
        #     db.rollback()

    except Exception as e:
        return {"message": str(e)}
    return {"message": "success"}
