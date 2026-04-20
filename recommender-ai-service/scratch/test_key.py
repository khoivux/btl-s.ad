import os
import google.generativeai as genai

KEY = "AIzaSyAv1FGyRYCuvASvWurdtB_ZHsBU8MgJ4Fw"
print(f"Testing key: {KEY[:8]}...")

try:
    genai.configure(api_key=KEY)
    model = genai.GenerativeModel('gemini-flash-latest')
    print("Attempting to generate content with gemini-flash-latest...")
    response = model.generate_content("Hi", stream=False)
    print("Response:", response.text)
except Exception as e:
    print("ERROR:", e)
