import pickle
import faiss

INDEX = []

def init_data(Embedding, db):
    print('initialize embedding....')
    instance = db.query(Embedding).first()
    e1 = pickle.loads(instance.data)
    index = faiss.IndexFlatL2(e1.shape[-1])
    index.add(e1.astype('float32'))
    INDEX.append(index)
    return True
