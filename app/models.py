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

    @staticmethod
    def score_distrib(qs):
        scores = [r.score for r in qs if isinstance(r.score,int)]
        res = Hackernews.distrib(scores)
        return res

    @staticmethod
    def text_distrib(qs):
        texts = [len(r.text) for r in qs]
        res = Hackernews.distrib(texts)
        return res

    @staticmethod
    def distrib(vals):
        min_val = min(vals)
        max_val = max(vals)
        avg_val = sum(vals) / len(vals)
        return {"min": min_val, "max": max_val, "avg": avg_val}

    @classmethod
    def filter_by_query(cls, db, query):
        D_I = dict()

        embed_search = np.array(Embedding.call_embed([query]))
        index = INDEX[0]

        D, I=index.search(embed_search.astype('float32'), 200)

        results = []
        dists = []
        hackernews = db.query(cls).filter(cls.id.in_((I[0] + 1).tolist()))

        for i in range(0, len(I[0])):
            D_I[I[0][i] + 1] = D[0][i]
            dists.append(D[0][i])


        score_dict = cls.score_distrib(hackernews)
        text_dict = cls.text_distrib(hackernews)
        dist_dict = cls.distrib(dists)
        print(dist_dict)

        # for news in hackernews:
        #     descendants = 0 if news.descendants else 0
        #     if news.score and isinstance(news.score,int):                
        #         fn_score = 0.2 * ((D_I[news.id] - dist_dict['avg']) / (dist_dict['max'] - dist_dict['min'])) + 0.2 * ((len(news.text) - text_dict['avg']) / (text_dict['max'] - text_dict['min'])) + 0.5 * ((news.score - score_dict['avg']) / (score_dict['max'] - score_dict['min'])) + 0.1 * descendants
        #     else:
        #         fn_score = 0.2 * ((D_I[news.id] - dist_dict['avg']) / (dist_dict['max'] - dist_dict['min'])) + 0.2 * ((len(news.text) - text_dict['avg']) / (text_dict['max'] - text_dict['min'])) + 0.1 * descendants

        #     results.append({
        #         'title': news.title,
        #         'hackernews_id': news.hackernews_id,
        #         'by': news.by,
        #         'fn_score': fn_score,
        #         'text': news.text,
        #         'score': news.score,
        #     })
        for news in hackernews:
            results.append({
                'title': news.title,
                'hackernews_id': news.hackernews_id,
                'by': news.by,
                'text': news.text,
                'score': D_I[news.id],
            })
        results = sorted(results, key=lambda k: k['score'], reverse=False)
        # results = sorted(results, key=lambda k: k['fn_score'], reverse=True)
        return results[:50]

    @classmethod
    def filter_by_ids(cls, db, hackernews):
        ids = [news.get('hackernews_id') for news in hackernews]
        qs = db.query(cls).filter(cls.hackernews_id.in_(ids)).all()
        return qs
