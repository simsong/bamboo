```
From GPT-4

pip install google-auth google-auth-oauthlib requests
```
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import requests

# Define the scopes
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Load credentials from the file
flow = InstalledAppFlow.from_client_secrets_file( 'path_to_your_credentials_file.json', SCOPES)
creds = flow.run_local_server(port=0)

# Now creds has the access token
access_token = creds.token

import requests

# Get the URL of the file
file_id = 'your_file_id'
url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"

# Use the access token in the header
headers = {
    'Authorization': f'Bearer {access_token}'
}

response = requests.get(url, headers=headers)

if response.status_code == 200:
    file_contents = response.content  # or response.text for text files
    print("File content received:")
    print(file_contents)
else:
    print(f"Failed to fetch file: {response.status_code} - {response.reason}")
