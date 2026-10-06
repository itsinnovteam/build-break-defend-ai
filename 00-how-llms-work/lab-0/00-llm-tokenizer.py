# requirements: pip install transformers sentencepiece
##### Created: 2026-10-01
##### Objective : To create a tokenizer that demonstrate how the input text is first converted into tokens, 
# which are then mapped to unique token IDs that the model uses during training and inference.


from transformers import AutoTokenizer



tokenizer = AutoTokenizer.from_pretrained("NousResearch/Meta-Llama-3-8B")
text = "I am excited to demonstrate how text is transformed into tokens and token IDs within an LLM."
tokens = tokenizer.tokenize(text)
token_ids = tokenizer.encode(text)  #.encode turns the text into token ID in META


character_count = len(text)
word_count = len(text.split())
token_count = len(tokens)
print(f"There are {character_count} characters, {word_count} words and {token_count} tokens")


tokens = tokenizer.tokenize(text)
token_ids = tokenizer.convert_tokens_to_ids(tokens)

print("Using Llama 3.2 3B, the input text is tokenized and mapped to the following token IDs:\n")

for token, token_id in zip(tokens, token_ids):
    print(f"{token:<15} -> {token_id}")






# # Alternative inspection to get the padding applied

# encoded = tokenizer(text)
# print(encoded)

# print("Input IDs:", encoded["input_ids"])
# print("Attention Mask:", encoded["attention_mask"])