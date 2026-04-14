"""Reindex all documents in the database.

This script can be called at all times. It will perform a new indexing
operation on all `.bib` files stored in the `data` directory.

After indexing, it computes similarity and co-occurrence data for
discovery features, and runs tag validation checks.
"""

import glob
import json
import os

from dotenv import load_dotenv

from donut.database import index_documents
from donut.similarity import compute_similarity
from donut.analysis import compute_tag_cooccurrence
from donut.validate_tags import (
    check_missing_categories,
    check_near_duplicates,
)

load_dotenv()


if __name__ == "__main__":
    DATA_DIR = os.getenv("DATA_DIR", "data")
    DATABASE_DIR = os.getenv("DATABASE_DIR", "database")

    assert DATA_DIR is not None
    assert DATABASE_DIR is not None

    filenames = glob.glob(os.path.join(DATA_DIR, "*.bib"))

    for filename in filenames:
        index_documents(filename, DATABASE_DIR)

    # Compute and save similarity data
    print("Computing paper similarity...")
    neighbors = compute_similarity(DATABASE_DIR)

    serializable = {
        str(k): v for k, v in neighbors.items()
    }

    similarity_path = os.path.join(
        DATABASE_DIR, "similarity.json"
    )
    with open(similarity_path, "w") as f:
        json.dump(serializable, f)

    print(f"Saved similarity data for {len(neighbors)} papers.")

    # Compute and save co-occurrence data
    print("Computing tag co-occurrence...")
    edges = compute_tag_cooccurrence(DATABASE_DIR)

    cooccurrence_path = os.path.join(
        DATABASE_DIR, "cooccurrence.json"
    )
    with open(cooccurrence_path, "w") as f:
        json.dump(edges, f)

    print(f"Saved {len(edges)} co-occurrence edges.")

    # Run tag validation
    print("\nRunning tag validation...")
    missing = check_missing_categories(DATABASE_DIR)
    if missing:
        print(
            f"WARNING: {len(missing)} papers missing "
            f"tag categories:"
        )
        for issue in missing[:5]:
            print(f"  {issue}")
        if len(missing) > 5:
            print(f"  ... and {len(missing) - 5} more")

    dupes = check_near_duplicates(DATABASE_DIR)
    if dupes:
        print(
            f"WARNING: {len(dupes)} near-duplicate "
            f"tag pairs:"
        )
        for t1, t2, score in dupes[:5]:
            print(f"  {t1} ~ {t2} ({score})")
        if len(dupes) > 5:
            print(f"  ... and {len(dupes) - 5} more")
