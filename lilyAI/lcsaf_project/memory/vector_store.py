import chromadb


class VectorStore:
    def __init__(self):
        self.client = chromadb.Client()
        self.collection = self.client.create_collection("lily_memory")

    def add(self, text, embedding):
        self.collection.add(documents=[text], embeddings=[embedding])

    def retrieve_relevant(self, query):
        # Placeholder: return most relevant memory
        results = self.collection.query(query_texts=[query], n_results=3)
        return results["documents"]
