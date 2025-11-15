import requests
import json
import base64
import time
from flask import Flask, jsonify, request
from flask_cors import CORS
from agora_token_builder import RtcTokenBuilder, RtmTokenBuilder

app = Flask(__name__)
CORS(app)

# --- Your Project Credentials ---
# (Keep these secret!)
APP_ID = "e8d59a7842684e79b7dfe59740f16f18" # Your Agora App ID
APP_CERTIFICATE = "09adb27f73b84ac39e5ef09a45a62198" # Go to Agora Console -> Project -> Primary Certificate
CUSTOMER_ID = "18bf77bfa8274fdba4b81fa63b45e0d5"
CUSTOMER_SECRET = "c137ed694bde4771b6edc64e08debe06"
PROJECT_ID = "e8d59a7842684e79b7dfe59740f16f18"
AGENT_NAME = "Dauhitri"
CHANNEL_NAME = "convai_N8kWZO"
CARTESIA_KEY = "sk_car_12cw6ifWaVHHmsPCzHhCrF"
GEMINI_API_KEY = "AIzaSyBaBMyDoy5BTHeEtcfvNXxHMXjq0dL4S4s" # (Note: Be careful exposing keys)

# Store the agent_id when it's created, so we can stop it.
# In a real app, you'd use a database for this.
current_agent_id = None

def generate_rtc_token(channel_name, uid):
    """Generates a new Agora RTC token."""
    if not APP_CERTIFICATE or APP_CERTIFICATE == "YOUR_APP_CERTIFICATE_HERE":
        print("ERROR: APP_CERTIFICATE is not set.")
        return None
        
    # Tokens expire after 1 hour (3600 seconds)
    expire_time_in_seconds = 3600
    current_timestamp = int(time.time())
    privilege_expired_ts = current_timestamp + expire_time_in_seconds

    try:
        token = RtcTokenBuilder.buildTokenWithUid(
            APP_ID,
            APP_CERTIFICATE,
            channel_name,
            uid,
            0, # 0 = User role (can be publisher or subscriber)
            privilege_expired_ts
        )
        return token
    except Exception as e:
        print(f"Error generating token: {e}")
        return None

# --- NEW ENDPOINT for your FRONTEND ---
@app.route('/api/get-token', methods=['POST'])
def get_token():
    """
    API endpoint for the frontend (index_2.html) to get a token.
    The frontend should send its UID in the request body.
    """
    data = request.get_json()
    uid = data.get('uid')

    if not uid:
        return jsonify({"error": "UID is required"}), 400

    print(f"Generating token for user UID: {uid} in channel: {CHANNEL_NAME}")
    
    # Ensure UID is an integer if it's not 0
    try:
        user_uid = int(uid)
    except ValueError:
        return jsonify({"error": "UID must be an integer"}), 400

    token = generate_rtc_token(CHANNEL_NAME, user_uid)

    if token:
        return jsonify({"token": token, "appId": APP_ID, "channel": CHANNEL_NAME})
    else:
        return jsonify({"error": "Failed to generate token"}), 500

# --- UPDATED ENDPOINT for starting the AI Agent ---
@app.route('/api/join-agora', methods=['POST'])
def join_agora_session():
    """
    API endpoint to start the Agora AI agent.
    This now generates a fresh token for the agent *every time*.
    """
    global current_agent_id
    print("Received request to join Agora session...")

    # 1. Generate a fresh token for the AI Agent
    # The agent will join with UID 0
    agent_uid = 0 
    print(f"Generating token for AI Agent (UID: {agent_uid})...")
    agent_token = generate_rtc_token(CHANNEL_NAME, agent_uid)
    
    if not agent_token:
        print("ERROR: Could not generate token for agent.")
        return jsonify({"error": "Failed to generate agent token"}), 500

    # 2. Encode credentials
    auth_str = f"{CUSTOMER_ID}:{CUSTOMER_SECRET}"
    encoded_credentials = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
    
    # 3. Set up Agora API URL and Headers
    url = f"https://api.agora.io/api/conversational-ai-agent/v2/projects/{PROJECT_ID}/join"
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/json"
    }
    
    # 4. Define the session data payload
    data = {
        "name": AGENT_NAME,
        "properties": {
            "channel": CHANNEL_NAME,
            "token": agent_token, # <-- USE THE NEW, FRESH TOKEN
            "agent_rtc_uid": str(agent_uid), # Use the same UID
            "remote_rtc_uids": ["*"],
            "enable_string_uid": False,
            "idle_timeout": 120,
            "llm": {
                "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:streamGenerateContent?alt=sse&key=AIzaSyBaBMyDoy5BTHeEtcfvNXxHMXjq0dL4S4s",
                "system_messages": [
                    {"role": "system", "content": "You are a helpful chatbot."}
                ],
                "greeting_message": "hello",
                "failure_message": "oops",
                "max_history": 10,
                "params": {
                    "model": "gemini-2.0-flash"
                }
            },
            "asr": {"language": "en-US"},
            "tts": {
                "vendor": "cartesia",
                "params": {
                    "api_key": CARTESIA_KEY,
                    "model_id": "sonic-2",
                    "voice": {
                        "mode": "id",
                        "id": "6ccbfb76-1fc6-48f7-b71d-91ac6298247b"
                    }
                }
            }
        }
    }
    
    # 5. Make the request to Agora
    print(f"Sending request to Agora API: {url}")
    response = requests.post(url, headers=headers, data=json.dumps(data))
    
    # 6. Check response and return to frontend
    if response.status_code == 200:
        print("Successfully started Agora AI agent.")
        response_data = response.json()
        current_agent_id = response_data.get('agent_id') # Save the agent_id
        print(f"Agent started with ID: {current_agent_id}")
        return jsonify(response_data)
    else:
        print(f"Error from Agora API: {response.status_code}")
        print(f"Response body: {response.text}")
        
        # If it's a 409, it means the agent is already running.
        # We should try to stop it.
        if response.status_code == 409:
            print("Conflict: Agent may already be running. Try calling /api/leave-agora first.")
            return jsonify({
                "error": "Agent conflict. Already running?", 
                "details": response.text
            }), 409
            
        return jsonify({
            "error": "Failed to join Agora session", 
            "details": response.text
        }), response.status_code

# --- NEW ENDPOINT to STOP the agent ---
@app.route('/api/leave-agora', methods=['POST'])
def leave_agora_session():
    """
    API endpoint to stop the running AI agent.
    """
    global current_agent_id
    if not current_agent_id:
        print("No agent ID stored. Cannot stop agent.")
        return jsonify({"error": "No agent is currently running or ID is unknown."}), 400

    print(f"Received request to stop agent: {current_agent_id}")

    # 1. Encode credentials
    auth_str = f"{CUSTOMER_ID}:{CUSTOMER_SECRET}"
    encoded_credentials = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")

    # 2. Set up Agora API URL and Headers
    url = f"https://api.agora.io/api/conversational-ai-agent/v2/projects/{PROJECT_ID}/agents/{current_agent_id}/leave"
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/json"
    }

    # 3. Make the request to Agora
    print(f"Sending 'leave' request to: {url}")
    response = requests.post(url, headers=headers)

    if response.status_code == 200:
        print(f"Successfully stopped agent: {current_agent_id}")
        current_agent_id = None # Clear the stored ID
        return jsonify({"message": "Agent stopped successfully."})
    else:
        print(f"Error stopping agent: {response.status_code}")
        print(f"Response body: {response.text}")
        return jsonify({"error": "Failed to stop agent", "details": response.text}), response.status_code

if __name__ == '__main__':
    # You MUST set your App Certificate in your environment variables
    # or replace "YOUR_APP_CERTIFICATE_HERE" above.
    if not APP_CERTIFICATE or APP_CERTIFICATE == "YOUR_APP_CERTIFICATE_HERE":
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!! ERROR: APP_CERTIFICATE is not set.               !!!")
        print("!!! Go to Agora Console -> Project -> Primary Certificate !!!")
        print("!!! and set it in the script or as an env variable.    !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    
    app.run(debug=True, port=5000)