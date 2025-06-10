import google.generativeai as genai
import os
from dotenv import load_dotenv
load_dotenv()


try:
    api_key = os.environ['GOOGLE_API_KEY']
    genai.configure(api_key=api_key)
except KeyError:
    print("🔴 ERROR: GOOGLE_API_KEY environment variable not set.")
    print("Please set this environment variable with your Gemini API key.")
    exit()
except Exception as e:
    print(f"🔴 ERROR: Could not configure Gemini API: {e}")
    exit()

try:
    model = genai.GenerativeModel('gemini-1.5-flash-latest') # Or 'gemini-1.5-pro-latest'
except Exception as e:
    print(f"🔴 ERROR: Could not initialize the model: {e}")
    exit()

# --- Define a Research-Oriented Prompt ---
meta_prompt = (
"""
Please research the following item metadata for a sports player:
Name: "Lionel Messi"

Please provide exact metadata object with year, reference URL to wikipedia page, and image URL from wikipedia page if available.:
{
    "status": "success",
    "item_year_from": "1997", # Start of the player's professional career
    "item_year_to": "2025", # Assuming current year for ongoing career
    "reference_url": "https://en.wikipedia.org/wiki/Lionel_Messi",
    "image_url": "https://upload.wikimedia.org/wikipedia/commons/9/9b/Lionel_Messi_20180626.jpg",
}

If no information can be found, return an empty object with the following structure:
{
    "status": "failed"
}
"""
)


print(f"🔍 Sending prompt to Gemini: \"{meta_prompt[:100]}...\"") # Print a snippet of the prompt

# --- Generate Content ---
try:
    # For simple text-in, text-out, use generate_content
    response = model.generate_content(meta_prompt)

    # --- Process and Display the Response ---
    if response and response.text:
        print("\n✅ Gemini's Response:")
        print("--------------------------------------------------")
        print(response.text)
        print("--------------------------------------------------")
    else:
        # Handle cases where the response might be blocked or empty
        print("\n⚠️ Gemini's Response was empty or blocked.")
        if response:
            print(f"Prompt Feedback: {response.prompt_feedback}")
            if response.candidates and response.candidates[0].finish_reason:
                 print(f"Finish Reason: {response.candidates[0].finish_reason.name}")
            if response.candidates and response.candidates[0].safety_ratings:
                print("Safety Ratings:")
                for rating in response.candidates[0].safety_ratings:
                    print(f"  - Category: {rating.category.name}, Probability: {rating.probability.name}")


except Exception as e:
    print(f"\n🔴 ERROR: An error occurred during content generation: {e}")

print("\n✨ Snippet execution complete.")

