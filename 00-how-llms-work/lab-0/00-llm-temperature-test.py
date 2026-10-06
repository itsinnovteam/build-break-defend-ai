# Import the Ollama Python library
import ollama

# The same prompt is reused for every run, so the only thing that changes is temperature
prompt = 'Write one sentence describing the weather in a fictional city called Novaterra.'

# Loop over three temperature settings: none, medium, high randomness
for t in [0, 0.7, 1.4]:
    # Label the group of results so you know which temperature produced them
    print('temperature =', t)

    # Run the same prompt 3 times at this temperature
    for i in range(3):
        # Send the prompt to Llama 3.1 8B
        r = ollama.chat(
            model='llama3.1:8b',
            messages=[{'role': 'user', 'content': prompt}],
            # Set the randomness level for this call
            options={'temperature': t},
        )
        # Print just the model's text reply (not the full response object)
        print(' -', r['message']['content'])

    # Print a blank line to separate the groups
    print()