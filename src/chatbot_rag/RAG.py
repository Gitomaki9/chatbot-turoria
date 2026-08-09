import os
from glob import glob
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import pickle

try:
    from .preprocessing import BasePreprocessing
except ImportError:
    from preprocessing import BasePreprocessing



class RAG:
    def __init__(
        self,
        path: str,
        base_persist_path: str = "./info/",
        base_persist_name: str = "all_info",
        preprocessing=None,
        *args,
        **kwargs,
    ):

        self.path = path
        self.base_persist_path = os.path.join(base_persist_path, base_persist_name)
        self.preprocessing = (
            preprocessing(path=path, *args, **kwargs)
            if preprocessing
            else BasePreprocessing(path=path)
        )
        self.debug = kwargs.get("debug", False)
        self.name_embeddings_model = kwargs.get(
            "name_model", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )

        self.model = self._get_embedding_model(model_name=self.name_embeddings_model)

    def __call__(self):
        return self._generate_db(
            base_persist_path=self.base_persist_path,
            force_update=False,
        )

    @property
    def get_embedding_model_name(self):
        return self.name_embeddings_model

    def _get_embedding_model(self, model_name: str):
        try:
            embedding_model = HuggingFaceEmbeddings(
                model_name=model_name,
            )
            return embedding_model
        except Exception as e:
            print(f"[ERROR] No se pudo cargar el modelo de embeddings: {e}")
            return None

    def _db_processing(self, document, persist_path="./all_info", exist=False):
        if exist:
            if self.debug:
                print(f"[DEBUG] Cargando base de datos existente en '{persist_path}'")
            with open(persist_path, "rb") as f:
                db = pickle.load(f)
            return db
        else:
            if self.debug:
                print(f"[DEBUG] Creando nueva base de datos en '{persist_path}'")
            db = FAISS.from_documents(document, self.model)
            os.makedirs(os.path.dirname(persist_path), exist_ok=True)
            with open(persist_path, "wb") as f:
                pickle.dump(db, f)
        return db

    def _generate_db(
        self,
        base_persist_path="./all_info",
        force_update=False,
        return_db=False,
    ):

        index_exists = os.path.exists(base_persist_path)

        if index_exists and not force_update:
            if self.debug:
                print(
                    f"[DEBUG] Cargando índice unificado existente en '{base_persist_path}'"
                )

            db = self._db_processing(
                exist=True, document=None, persist_path=base_persist_path
            )
        else:
            # Reconstruir el índice unificado
            if self.debug:
                print(
                    f"[DEBUG] Creando un nuevo índice unificado en '{base_persist_path}'"
                )

            db = self._db_processing(
                exist=False,
                document=self.preprocessing(),
                persist_path=base_persist_path,
            )

        self.db = db
        if return_db:
            return db

    def _search_context(self, query, k=3):
        results = self.db.similarity_search(query, k=k)
        return "\n\n".join([doc.page_content for doc in results])


if __name__ == "__main__":
    from preprocessing import BasePreprocessing
else:
    from .preprocessing import BasePreprocessing
