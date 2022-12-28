"""Analyse existing tags."""

import os
import itertools

from dotenv import load_dotenv

from donut.database import get_tags

from nltk.metrics.distance import jaro_winkler_similarity

load_dotenv()
DATABASE_DIR = os.getenv("DATABASE_DIR")


if __name__ == "__main__":
    tags = get_tags(DATABASE_DIR)

    for category in sorted(tags.keys()):
        tags_per_category = sorted(tags[category].keys())

        print("Category:", category)

        for t1, t2 in itertools.combinations(tags_per_category, 2):
            dist = jaro_winkler_similarity(t1, t2)
            if dist >= 0.9:
                print("  ", t1, "~", t2)
