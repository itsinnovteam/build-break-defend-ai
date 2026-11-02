"""Similarity demo: compare one question against two sentences.

The first sentence is the question. Each of the others is embedded and
scored against it with cosine similarity (closer to 1.0 = more similar).

Run from the Module 4 lab folder (next to ollama_client.py and retriever.py):
    python3 similarity_demo.py
"""
import ollama_client, retriever

sentences = [
    "Who do I notify about a compromised admin account?",                 # question
    "Escalate to the IR Lead within 15 minutes for privileged accounts.",  # relevant
    "Employees may take 3 days of emergency leave per year.",              # off-topic
]


def main():
    vectors = ollama_client.embed(sentences)
    question_vec = vectors[0]

    print("Question: " + sentences[0] + "\n")
    for text, vec in zip(sentences[1:], vectors[1:]):
        score = retriever.cosine(question_vec, vec)
        print("{:.3f}  {}".format(score, text))


if __name__ == "__main__":
    main()