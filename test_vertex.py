import os
from dotenv import load_dotenv
from google.cloud import aiplatform

# Load the variables from the .env file we just edited
load_dotenv()

project = os.getenv("GOOGLE_CLOUD_PROJECT")
location = os.getenv("GCP_REGION", "us-central1")

print(f"--- Vertex AI Handshake ---")
print(f"Project: {project}")
print(f"Region:  {location}")

try:
    aiplatform.init(project=project, location=location)
    # This list call confirms you have the right permissions
    models = aiplatform.Model.list()
    print("✅ Connection Successful!")
except Exception as e:
    print(f"❌ Connection Failed: {e}")
