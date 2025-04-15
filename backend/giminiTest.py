import google.generativeai as genai

# Your Gemini API key
api_key = 'AIzaSyCFYLMVf5BsVlwZCUE1e8TzRmfllaCD6zw' #AIzaSyDid8rjeYlZl5C72XIgDiNsnO_ap1tPx9o

# Configure the Gemini API
genai.configure(api_key=api_key)

# Create the model with full model name
model = genai.GenerativeModel(model_name="gemini-2.0-flash")

# Prompt
prompt = "Write a poetic paragraph about a lonely robot dreaming of stars."

# Generate and print output
response = model.generate_content(prompt)
# print(response.text)


# import os
# import requests
# from dotenv import load_dotenv

# # Load .env file if available
# load_dotenv()

# # Get API key from environment variable or paste directly
# api_key = os.getenv("GROQ_API_KEY", "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")

# if not api_key:
#     raise EnvironmentError("API key not found. Set it in the 'GROQ_API_KEY' env variable or paste it in the script.")

# # Define Groq API URL
# url = "https://api.groq.com/openai/v1/chat/completions"

# # Set headers
# headers = {
#     "Authorization": f"Bearer {api_key}",
#     "Content-Type": "application/json"
# }

# # Define prompt and model
# data = {
#     "model": "llama-3.3-70b-versatile",
#     "messages": [
#         {"role": "user", "content": "Test: Say a poetic line about stars and loneliness."}
#     ]
# }

# # Make the API request
# response = requests.post(url, headers=headers, json=data)

# # Print the response
# try:
#     output = response.json()["choices"][0]["message"]["content"]
#     print("Groq API Response:\n", output)
# except Exception as e:
#     print(" Error:", e)
#     print("Full response:", response.text)
