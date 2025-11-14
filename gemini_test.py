import os
import requests
import json

def test_gemini():
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment variables")
        return
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    data = {
        "contents": [{
            "parts": [{
                "text": "Hello! This is a test of the Gemini API."
            }]
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        if 'candidates' in result and result['candidates']:
            reply = result['candidates'][0]['content']['parts'][0]['text']
            print(f"Gemini says: {reply}")
        else:
            print("No response from Gemini")
            print(json.dumps(result, indent=2))
            
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response content: {e.response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_gemini()