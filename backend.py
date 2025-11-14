import requests
import json
import base64
from flask import Flask, jsonify, request
from flask_cors import CORS

# --- Your Agora Credentials & Config ---
# I have removed a hidden whitespace from the start of the secret
CUSTOMER_ID = "18bf77bfa8274fdba4b81fa63b45e0d5"
CUSTOMER_SECRET = "c137ed694bde4771b6edc64e08debe06" 
PROJECT_ID = "e8d59a7842684e79b7dfe59740f16f18"
AGENT_NAME = "Dauhitri"
CHANNEL_NAME = "convai_lVxlVE"
# I have removed the extra '#' from the end of the token
AGORA_TOKEN = "007eJxTYLj6eKP5iW/t08Uni03OT3J02M/52o9lY7xnp2we4+0ntr4KDKkWKaaWieYWJkZmFiap5pZJ5ilpqaaW5iYGaYZmaYYWJjPFMxsCGRlOlW9hZmSAQBCflyE5P68sMTPeMD4+yqucgQEAPFEhig="
GEMINI_API_KEY = "AIzaSyB0Rx3lBpWOwEsRhFlJdcf077jMjtHK7H8"
# Switched to Cartesia Key
CARTESIA_KEY = "sk_car_12cw6ifWaVHHmsPCzHhCrF"
# --- End of Credentials ---

# Initialize the Flask app
app = Flask(__name__)
# Enable CORS
CORS(app)

@app.route('/api/join-agora', methods=['POST'])
def join_agora_session():
    """
    API endpoint that the frontend will call.
    This function runs the server-side logic to start the Agora AI agent.
    """
    
    print("Received request to join Agora session...")
    
    try:
        # 1. Encode credentials
        auth_str = f"{CUSTOMER_ID}:{CUSTOMER_SECRET}"
        encoded_credentials = base64.b64encode(auth_str.encode()).decode("utf-8")
        
        # 2. Set up Agora API URL and Headers
        url = f"https://api.agora.io/api/conversational-ai-agent/v2/projects/{PROJECT_ID}/join"
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json"
        }
        
        # 3. Define the session data payload
        data = {
            "name": AGENT_NAME,
            "properties": {
                "channel": CHANNEL_NAME,
                "token": AGORA_TOKEN,
                "agent_rtc_uid": "0",
                "remote_rtc_uids": ["*"],
                "enable_string_uid": False,
                "idle_timeout": 120,
                "llm": {
                    "url": "https://generativelanguage.googleapis.com/v1beta",
                    "api_key": GEMINI_API_KEY,
                    "system_messages": [
                        {
                            "role": "system",
                            "content": "You are a helpful chatbot."
                        }
                    ],
                    "greeting_message": "hello", # Your new greeting
                    "failure_message": "oops",  # Your new failure message
                    "max_history": 10,
                    "params": {
                        "model": "gemini-1.5-flash-latest" # Kept the working model name
                    }
                },
                "asr": {
                    "language": "en-US"
                },
                "tts": {
                    "vendor": "cartesia", # Switched to Cartesia
                    "params": {
                        "key": CARTESIA_KEY,
                        "voice_id": "6ccbfb76-1fc6-48f7-b71d-91ac6298247b"
                    }
                }
            }
        }
        
        # 4. Make the request to Agora
        print(f"Sending request to Agora API: {url}")
        response = requests.post(url, headers=headers, data=json.dumps(data))
        
        # 5. Check response and return to frontend
        if response.status_code == 200:
            print("Successfully joined Agora session.")
            return jsonify(response.json())
        else:
            print(f"Error from Agora API: {response.status_code}")
            print(f"Response body: {response.text}")
            return jsonify({"error": "Failed to join Agora session", "details": response.text}), response.status_code

    except Exception as e:
        print(f"An internal server error occurred: {str(e)}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)