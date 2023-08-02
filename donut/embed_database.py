"""Embed database via UMAP and store it."""

import os
import sys

import pandas as pd

from dotenv import load_dotenv

from donut.database import get_documents

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.manifold import TSNE

# Make sure that we have access to the database directory and other
# information that we require.
load_dotenv()
DATABASE_DIR = os.getenv("DATABASE_DIR", "data")


def get_text(document):
    """Return text of document."""
    text = document["title"]
    if "abstract" in document:
        text += "\n" + document["abstract"]

    return text


if __name__ == "__main__":
    matches = get_documents(DATABASE_DIR)

    vectorizer = TfidfVectorizer(min_df=5, stop_words="english")

    raw_documents = [get_text(match["document"]) for match in matches]

    X = vectorizer.fit_transform(raw_documents)
    embedder = TSNE(init="random", random_state=42)
    X_emb = embedder.fit_transform(X)
    X_emb = (X_emb - X_emb.min()) / (X_emb.max() - X_emb.min())

    df = pd.DataFrame.from_dict({"x": X_emb[:, 0], "y": X_emb[:, 1]})

    df["id"] = [match["id"] for match in matches]
    df["title"] = [match["document"]["title"] for match in matches]
    df["abstract"] = [
        match["document"].get("abstract", "") for match in matches
    ]

    df.set_index("id", inplace=True)

    # Do not use `print` because it adds a newline to the file, which
    # may be interpreted incorrectly upon reading.
    sys.stdout.write(df.to_csv(sep="\t"))
