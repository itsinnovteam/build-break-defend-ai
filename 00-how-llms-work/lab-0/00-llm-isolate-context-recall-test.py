# Right-sized version: book slice + context window actually match
import ollama

# ~4-5k tokens, deliberately smaller than the oversized 200,000-char test
book = open("book.txt", encoding="utf-8").read()[:20000]

# Secret word at the start, book in the middle, question at the end
prompt = f"The secret code word for this test is BANANA-77.\n\n{book}\n\nWhat was the secret code word at the start of this message?"

# Explicitly widen the context window so the whole prompt fits
response = ollama.chat(
    model="llama3.1:8b",
    messages=[{"role": "user", "content": prompt}],
    options={"num_ctx": 8192}
)
print(response["message"]["content"])