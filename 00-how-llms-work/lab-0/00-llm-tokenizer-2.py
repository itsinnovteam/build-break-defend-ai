# Load the same tokenizer Llama 3.1 8B uses
from tokenizers import Tokenizer
tok = Tokenizer.from_pretrained("NousResearch/Meta-Llama-3.1-8B")

# Compare token counts across different kinds of text
for text in [
    "Hello, world!",                  # short English word
    "antidisestablishmentarianism",   # long English word
    "こんにちは、元気ですか？",            # non-English sentence
]:
    ids = tok.encode(text).ids
    print(text, "->", len(ids), "tokens")