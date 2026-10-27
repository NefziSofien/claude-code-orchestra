"""A tiny in-memory inverted index."""
import re


def _normalize(word):
    return word.lower()


def tokenize(text):
    """Split text into lowercase alphanumeric words."""
    return [_normalize(w) for w in re.findall(r"[A-Za-z0-9]+", text)]


def build_index(documents):
    """Map each word to {doc_id: count} for a {doc_id: text} mapping."""
    index = {}
    for doc_id, text in documents.items():
        for word in tokenize(text):
            counts = index.setdefault(word, {})
            counts[doc_id] = counts.get(doc_id, 0) + 1
    return index


def query(index, text):
    """Return {doc_id: score} for documents containing every word of the query."""
    words = tokenize(text)
    if not words:
        return {}
    matches = None
    for word in words:
        docs = set(index.get(word, {}))
        matches = docs if matches is None else matches & docs
    return {doc: sum(index[w][doc] for w in words) for doc in matches}


def rank(scores):
    """Doc ids ordered by score descending, ties broken by id."""
    return [doc for doc, _ in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))]
