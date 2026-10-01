import ollama

# Load the untrusted document - it may contain hidden instructions
doc = open("untrusted.txt", encoding="utf-8").read()

# This is YOUR real instruction, separate from anything inside the document
prompt = f"Summarize the following document in two sentences:\n\n{doc}"

print(ollama.chat(model="llama3.1:8b", messages=[{"role": "user", "content": prompt}])["message"]["content"])