from fastembed import TextEmbedding

_model = None

def _get_model() -> TextEmbedding:
    global _model 
    if _model is None:
        _model = TextEmbedding("BAAT/bge-small-en-v1.5")
    return _model

def embed(texts: list[str]) -> list[list[float]]:
    return [vec.tolist() for vec in _get_model().embed(texts)]
