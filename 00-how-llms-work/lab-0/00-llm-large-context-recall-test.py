# Import the Ollama Python library
import ollama

# Open book.txt and read only the first 20,000 characters.
# This is roughly 4,000-5,000 tokens, depending on the text.
book = open("book.txt", encoding="utf-8").read()[:200000]

# {book} must stay in this f-string - dropping it breaks the test
prompt = f"The secret code word for this test is BANANA-77.\n\n{book}\n\nWhat was the secret code word at the start of this message?"


# Send the prompt to the Llama 3.1 8B model
response = ollama.chat(
    model="llama3.1:8b",

    # Send the complete prompt as a user message
    messages=[{"role": "user", "content": prompt}],

    # Set the model's runtime context window to 8,192 tokens
    options={"num_ctx": 8192}
)

# Print the model's answer
print(response["message"]["content"])