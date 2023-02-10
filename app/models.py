import math
import faiss
import pickle
import mpu.io
import numpy as np
import time

from datetime import datetime
from sqlalchemy import (
    Column, Integer, BINARY, String, DATETIME, Boolean, TEXT, ARRAY)

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
    def index_flat_l2(cls, db):
        try:
            e1 = cls.get_data(db)
            index = faiss.IndexFlatL2(e1.shape[-1])
            index.add(e1.astype('float32'))
            return index
        except Exception as e:
            return []


class Hackernews(Base, BaseMixin, SearchMixin):
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
    embedding = Column(BINARY)

    @classmethod
    def import_csv(cls, db):
        hackernews = mpu.io.read('hackernews.csv')
        try:
            for i in range(1, len(hackernews)):
                print(i)
                obj = cls.reform_csv_record(hackernews[i])
                if obj['deleted']:
                    continue
                if obj['dead']:
                    continue
                if not obj['score']:
                    continue
                if int(obj['score']) < 2:
                    continue
                if len(obj['text']) < 200:
                    continue
                e = cls.call_embed([obj['text']])
                if e:
                    obj['embedding'] = pickle.dumps(e)
                else:
                    obj['embedding'] = None
                cls.create(db, obj)
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
        scores = [r['score'] for r in qs]
        res = Hackernews.distrib(scores)
        return res

    @staticmethod
    def descendants_distrib(qs):
        descendants = [int(r['descendants']) for r in qs]
        res = Hackernews.distrib(descendants)
        return res

    @staticmethod
    def text_distrib(qs):
        texts = [len(r['text']) for r in qs]
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

        D, I=index.search(embed_search.astype('float32'), 50)
        
        dists = []
        results = []
        qs_filtered = []
        qs_all = db.query(cls).order_by(cls.id.asc())

        # for i in range(0, len(I[0])):
        #     D_I[I[0][i] + 1] = D[0][i]
        #     dists.append(D[0][i])
        for i in range(0, len(I[0])):
            D_I[I[0][i]] = D[0][i]
            dists.append(D[0][i])

        for id in I[0].tolist():
            news = qs_all[id]
            qs_filtered.append({
                'title': news.title,
                'hackernews_id': news.hackernews_id,
                'by': news.by,
                'text': news.text,
                'score': news.score if news.score else 0,
                'descendants': int(news.descendants) if news.descendants else 0,
                'dist': D_I[id],
                'url': news.url,
                'time': news.time_ts,
            })
        # hackernews = db.query(cls).filter(cls.id.in_((I[0] + 1).tolist()))

        # score_dict = cls.score_distrib(qs_filtered)
        # text_dict = cls.text_distrib(qs_filtered)
        # dist_dict = cls.distrib(dists)
        # descendants_dict = cls.descendants_distrib(qs_filtered)

        # for news in qs_filtered:
        #     fn_score = - 0.5 * ((news['dist'] - dist_dict['avg']) / (dist_dict['max'] - dist_dict['min'])) + 0.2 * ((len(news['text']) - text_dict['avg']) / (text_dict['max'] - text_dict['min'])) + 0.3 * ((news['score'] - score_dict['avg']) / (score_dict['max'] - score_dict['min'])) + 0.1 * ((news['descendants'] - descendants_dict['avg']) / (descendants_dict['max'] - descendants_dict['min']))

        #     news['fn_score'] = fn_score
        #     results.append(news)

        # results = sorted(results, key=lambda k: k['fn_score'], reverse=True)

        results = sorted(qs_filtered, key=lambda k: k['dist'], reverse=False)
        return results[:50]

    @classmethod
    def filter_by_ids(cls, db, hackernews):
        ids = [news.get('hackernews_id') for news in hackernews]
        qs = db.query(cls).filter(cls.hackernews_id.in_(ids)).all()
        return qs
