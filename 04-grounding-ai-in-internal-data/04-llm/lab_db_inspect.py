"""Lab DB1 - Look inside the vector database.

A vector database stores each embedding together with its text and labels
(metadata), all under one ID. This lab opens the Chroma collection and shows
what one record looks like.

Run:
    python3 lab_db1_inspect.py              # overview + first 3 records
    python3 lab_db1_inspect.py phishing#1   # look up one record by its ID
"""
import sys

import lab_common


def describe(record_id, text, meta, vec):
    print("\nID:        " + record_id)
    print("Metadata:  {}".format(meta))
    print("Text:      " + " ".join(text.split())[:110] + " ...")
    print("Vector:    {} numbers, starting {}".format(
        len(vec), [round(float(x), 4) for x in vec[:5]]))


def main():
    col = lab_common.collection()

    print("Collection: '{}'".format(col.name))
    print("Records:    {}".format(col.count()))
    print("Settings:   {}".format(col.metadata))

    if len(sys.argv) > 1:
        rec = col.get(ids=[sys.argv[1]], include=["documents", "metadatas", "embeddings"])
        if not rec["ids"]:
            sys.exit("No record with ID '{}'.".format(sys.argv[1]))
        print("\nLooked up by ID:")
    else:
        rec = col.peek(limit=3)
        print("\nFirst 3 records:")

    for i, record_id in enumerate(rec["ids"]):
        describe(record_id, rec["documents"][i], rec["metadatas"][i], rec["embeddings"][i])

    print("\nEach record = ID + vector + original text + metadata, stored together.")


if __name__ == "__main__":
    main()
