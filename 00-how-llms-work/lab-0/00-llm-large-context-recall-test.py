# Variant test file - same logic as isolate-context-recall-test.py
import ollama

# Small book slice so the full prompt stays within the context window
book = open("book.txt", encoding="utf-8").read()[:20000]

# {book} must stay in this f-string - dropping it breaks the test
prompt = f"The secret code word for this test is BANANA-77.\n\n{book}\n\nWhat was the secret code word at the start of this message?"

response = ollama.chat(
    model="llama3.1:8b",
    messages=[{"role": "user", "content": prompt}],
    options={"num_ctx": 8192}
)
print(response["message"]["content"])