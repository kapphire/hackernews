import pickle
import faiss
import numpy as np

INDEX = []

def init_data(Hackernews, db):
    print('initialize embedding....')
    e1 = []
    for news in db.query(Hackernews):
        e1.append(pickle.loads(news.embedding))
    e1 = np.concatenate(e1)
    index = faiss.IndexFlatL2(e1.shape[-1])
    index.add(e1.astype('float32'))
    INDEX.append(index)
    return True
