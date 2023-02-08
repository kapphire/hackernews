import math
import faiss
import pickle
import mpu.io
import numpy as np
import time

from datetime import datetime
from sqlalchemy import (
    Column, Integer, BINARY, String, DATETIME, Boolean, TEXT)

from app import env
from app.database import Base
from app.mixins import BaseMixin, SearchMixin
from app.env import INDEX


class Embedding(Base, BaseMixin, SearchMixin):
    __tablename__ = "embeddings"

    id = Column(Integer, primary_key=True, index=True)
    data = Column(BINARY)

    def __repr__(self):
        return f"<{pickle.loads(self.data)}>"

    @classmethod
    def get_data(cls, db):
        qs = db.query(cls)
        if qs.count():
            return pickle.loads(qs.first().data)
        return []

    @classmethod
    def get_embedding_str(cls, db):
        e1 = []
        step = 5
        qs_news = db.query(Hackernews).all()

        for i in range (0, int(len(qs_news) / step) + 1):
            print(i)
            to_embed = [news.text for news in qs_news[i * step : i * step + step]]

            if to_embed:
                e = cls.call_embed(to_embed)
                if not e:
                    print(to_embed, '=')
                    time.sleep(10)
                    e = cls.call_embed(to_embed)
                e1.append(e)
        e1=np.concatenate(e1)

        try:
            instance = cls(data=pickle.dumps(e1))
            db.add(instance)
            db.commit()
            db.refresh(instance)
        except Exception as e:
            print(e)
            db.rollback()
        return e1

    @classmethod
    def index_flat_l2(cls, db):
        try:
            e1 = cls.get_data(db)
            index = faiss.IndexFlatL2(e1.shape[-1])
            index.add(e1.astype('float32'))
            return index
        except Exception as e:
            return []


class Hackernews(Base, BaseMixin):
    __tablename__ = "hackernews"
    id = Column(Integer, primary_key=True, index=True)
    hackernews_id = Column(String, index=True, unique=True)

    by = Column(String)
    score = Column(Integer)
    time = Column(String)
    time_ts = Column(DATETIME)
    title = Column(TEXT)
    url = Column(TEXT)
    text = Column(TEXT)
    deleted = Column(Boolean)
    dead = Column(Boolean)
    descendants = Column(String)
    author = Column(String)

    @classmethod
    def import_csv(cls, db):
        hackernews = mpu.io.read('hackernews.csv')
        cnt = 0
        try:
            for i in range(1, len(hackernews)):
                if cnt == 10000:
                    break
                obj = cls.reform_csv_record(hackernews[i])
                if obj['deleted'] or obj['dead'] or len(obj['text']) < 80:
                    continue
                cls.create(db, obj)
                cnt += 1

            return True
        except Exception as e:
            return e

    @staticmethod
    def reform_csv_record(data):
        return {
            "hackernews_id": data[0],
            "by": data[1],
            "score": data[2],
            "time": data[3],
            "time_ts": Hackernews.str_to_date(data[4]),
            "title": data[5],
            "url": data[6],
            "text": data[7],
            "deleted": Hackernews.str_to_boolean(data[8]),
            "dead": Hackernews.str_to_boolean(data[9]),
            "descendants": data[10],
            "author": data[11],}

    @staticmethod
    def str_to_date(date):
        try:
            return datetime.strptime(date, "%Y-%m-%d %H:%M:%S %Z")
        except Exception as e:
            return None

    @staticmethod
    def str_to_boolean(str):
        if str == 'true':
            return True
        return False

    @classmethod
    def filter_by_query(cls, db, query):
        D_I = dict()

        embed_search = np.array(Embedding.call_embed([query]))
        index = INDEX[0]

        D, I=index.search(embed_search.astype('float32'), 50)

        results = []
        hackernews = db.query(cls).filter(cls.id.in_((I[0] + 1).tolist()))

        for i in range(0, len(I[0])):
            D_I[I[0][i] + 1] = D[0][i]

        for news in hackernews:
            results.append({
                'title': news.title,
                'score': news.score,
                'hackernews_id': news.hackernews_id,
                'by': news.by,
                'dist': D_I[news.id]
            })
        results = sorted(results, key=lambda k: k['score'], reverse=True)
        return results

    @classmethod
    def filter_by_ids(cls, db, hackernews):
        ids = [news.get('hackernews_id') for news in hackernews]
        qs = db.query(cls).filter(cls.hackernews_id.in_(ids)).all()
        return qs
