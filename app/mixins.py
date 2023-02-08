import numpy as np
import tritonclient.grpc as grpcclient


def convert_strings_to_inputs(strings):
    inputs = [
        grpcclient.InferInput("inputs", (len(strings),), "BYTES"),
    ]

    inputs[0].set_data_from_numpy(np.array(strings, dtype=np.object_))
    return inputs


class BaseMixin:

    @classmethod
    def create(cls, db, obj):
        try:
            instance = cls(**obj)
            db.add(instance)
            db.commit()
            db.refresh(instance)
            return instance
        except Exception as e:
            print(e)
            db.rollback()
            return False

    def update(self, db, data):
        try:
            for key, value in data.items():
                setattr(self, key, value)

            db.add(self)
            db.commit()
            db.refresh(self)
            print('updated!!!')
            return self
        except Exception as e:
            db.rollback()
            return False

    @classmethod
    def bulk_update(cls, db, objects):
        try:
            db.bulk_save_objects(objects)
            db.commit()
        except Exception as e:
            db.rollback()

    def to_dict(self):
        d = {}
        for column in self.__table__.columns:
            d[column.name] = getattr(self, column.name)
        return d


class SearchMixin:

    @staticmethod
    def call_embed(data):
        host = '216.18.205.234'
        port = '8531'
        triton_client = grpcclient.InferenceServerClient(
            url=f"{host}:{port}", verbose=False
        )
        res = []
        try:
            inputs = convert_strings_to_inputs(data)
            res = triton_client.infer(
                model_name="universal-sentence-encoder-large", inputs=inputs
            )
            res = res.as_numpy("outputs").tolist()
        except Exception as e:
            print(e)
        return res
