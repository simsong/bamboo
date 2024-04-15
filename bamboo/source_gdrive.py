"""source iterator for Google Drive.
Accessing Google Drive requires using OAuth.

This uses the following libraries:

Google Auth Libraries:
   `pip install google-auth google-auth-oauthlib google-auth-httplib2`

Google API Client Libraries:
    `pip install google-api-python-client`

Notes that this code could be reworked to a different set of OAuth libraries, including:
  OAuthLib - pip install oauthlib requests
  Authlib - pip install authlib
  Flask-Dance - pip install Flask-Dance

Accessing Google Drive with OAuth requires registering your
application with Google and then getting OAuth credentials from Google
for your app (this is automatic) and from the user for their Google
drive. This file can be run as a standalone program to the second
part. If you do that, it creates a file called
`gdrive_credentials.json` This must be either be in a file or in an
environment variable GDRIVE_CREDENTIALS when the program is run. If
the variable GDRIVE_CREDENTIALS is an AWS ARN for the AWS Secrets
Manager, then we go to AWS Secrets Manager to get the credentials.

All Google drives and files within the drive are accessed by an
identifier (Id). The Id does not change even if the file is drive or
file is renamed or given to another user.

To create an Google application credentials for the OAuth2 client ID
and client secret, follow these steps:

1. Go to the Google Cloud Platform Console. (https://console.cloud.google.com/)
2. Create a new project if you do not have one already
3. Click on the "APIs & Services" tab.
4. Click on the "Credentials" link.
5. Click on the "Create Credentials" button.
6. Select "OAuth 2.0 Client ID" from the drop-down menu.
7. Enter a name for your client ID.
8. Select the application type that will be using the client ID and client secret.
9. Click on the "Create" button.
10. Your client ID and client secret will be displayed on the screen.

"""

DRIVE_LIST = 'drive_list.json'
DRIVE_LIST_PAGE_SIZE = 5

# Application credentials must be obtained from Google.
# They contain security-sensitive information, so they should not be
# added to the git repo.
#
APP_CREDENTIALS_FILENAME = 'client_secret.json'

# This is the OAuth token. It is created by this program.
#
OAUTH_TOKEN_FILENAME='token.json'

# Scopes specifies the specific permissions requested for the user's
# Google drive. They boundinto the OAUTH_TOKEN_FILENAME, so delete the
# token if you change this list.
SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly',
          'https://www.googleapis.com/auth/drive.activity.readonly',
          'https://www.googleapis.com/auth/drive.readonly']

# Map the google types
GOOGLE_TYPES = {"application/vnd.google-apps.document":"gdoc",
                "application/vnd.google-apps.spreadsheet":"gsheet",
                "application/octet-stream":"data",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":"xlsx",
                "application/vnd.google-apps.folder":"dir"
                }



import json
import os
import os.path
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import googleapiclient.errors

from google_auth_oauthlib.flow import InstalledAppFlow

################################################################
## Authorization

def get_app_credentials(*,client_secret):
    creds = None
    # The file OAUTH_TOKEN_FILENAME stores the user's access and
    # refresh tokens, and is created automatically when the
    # authorization flow completes for the first time.
    if os.path.exists(OAUTH_TOKEN_FILENAME):
        creds = Credentials.from_authorized_user_file(OAUTH_TOKEN_FILENAME, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file( client_secret, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(OAUTH_TOKEN_FILENAME, 'w') as token:
            token.write(creds.to_json())
    return creds

################################################################
## Drive and shared file listing

def list_drives(creds):
    """Generator that returns all the drives, each as a dictionary that contains
    ['name'] and ['id']"""
    drive = build('drive', 'v3', credentials=creds)
    drives = drive.drives()
    pageToken = None
    while True:
        results = drives.list(pageSize=DRIVE_LIST_PAGE_SIZE,
                              pageToken=pageToken).execute()
        if 'drives' not in results or len(results['drives'])==0:
            return
        for drive in results['drives']:
            yield drive
        if 'nextPageToken' not in results:
            return
        pageToken = results['nextPageToken']

def gfiles_list(creds, q, *, extra_args={}, file_fields_add=[]):
    """Generator that returns all files or folders that match a query"""
    drive = build('drive', 'v3', credentials=creds)
    drives = drive.drives()
    files  = drive.files()
    file_fields = ",".join(set(DEFAULT_FILE_FIELDS + file_fields_add))
    pageToken = None
    while True:
        default_args = {'pageSize':DRIVE_LIST_PAGE_SIZE,
                        'pageToken':pageToken,
                        'q':q,
                        'fields':f'nextPageToken, files({file_fields})'}
        try:
            results = files.list(**{**default_args,**extra_args}).execute()
        except googleapiclient.errors.HttpError as e:
            raise
        for res in results['files']:
            yield res
        if 'nextPageToken' not in results:
            return
        pageToken = results['nextPageToken']

FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
IS_FOLDER        = f"(mimeType  = '{FOLDER_MIME_TYPE}')"
IS_NOT_FOLDER    = f"(mimeType  != '{FOLDER_MIME_TYPE}')"
FOLDERS_SHARED_WITH_ME=f"(sharedWithMe = true) and {IS_FOLDER}"
FILES_SHARED_WITH_ME  =f"(sharedWithMe = true) and {IS_NOT_FOLDER}"
DEFAULT_FILE_FIELDS = ['id','name','owners','mimeType']

################################################################
## Drive and shared file listing
def list_folders(creds):
    """Generator that returns all folders shared with the user, each as a dictionary that contains
    ['name'] and ['id']"""
    for obj in gfiles_list(creds, q=FOLDERS_SHARED_WITH_ME):
        yield obj

def print_objs(objs):
    for obj in objs:
        print(obj)

def save_drives(creds, path):
    """Save a list of all Google drives as a JSON file in DRIVE_LIST"""
    drives = sorted(list_drives(creds), key=lambda k:k['name'])
    print_objs(drives)
    with open(DRIVE_LIST,"w") as f:
        f.write(json.dumps(drives))

################################################################
###

# Simple generator to run a query and return the result
# https://developers.google.com/drive/api/reference/rest/v2/files
# Some useful queries
def name(creds, fileId):
    """Just return the name of a Id"""
    file = build('drive', 'v3', credentials=creds).files().get(fileId=fileId).execute()
    return file['name']

def walk(creds, dirId, path='', file_fields_add=[]):
    """Similar to os.path.walk(), except returns (root, files, dirs) for a google directory."""
    if path=='':
        path = name(creds, dirId)
    all     = list( gfiles_list(creds, q=f"('{dirId}' in parents)", file_fields_add=file_fields_add))
    folders = [ item for item in all if item.get('mimeType',None)==FOLDER_MIME_TYPE]
    files   = [ item for item in all if item.get('mimeType',None)!=FOLDER_MIME_TYPE]

    yield (path, folders, files)
    for folder in folders:
        yield from walk(creds, folder['id'], path+"/"+folder['name'], file_fields_add=file_fields_add)


def GoogleDriveFrameStream():
    pass

if __name__=="__main__":
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """

    import argparse
    parser = argparse.ArgumentParser(description="Obtain OAuth2 credentials and list available Google Drives.",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument( '--drives', help='List drives', action='store_true')
    parser.add_argument( '--listfolder', help='List files in a folder Id')
    parser.add_argument( '--client_secret', default=APP_CREDENTIALS_FILENAME)
    parser.add_argument( '--shared', help='List folders shared with you', action='store_true')
    parser.add_argument( '--limit', help='Limit to this many outputs', type=int)
    parser.add_argument( '--walk', help='walk the provided Id recursively')
    parser.add_argument( 'Ids', help='Ids that you want to list', nargs='*')

    args = parser.parse_args()
    creds = get_app_credentials(client_secret=args.client_secret)

    if args.drives:
        save_drives(creds, DRIVE_LIST)
    if args.shared:
        for obj in list_folders(creds):
            print(obj)
    if args.listfolder:
        for obj in gfiles_list(creds, q = f"'{args.listfolder}' in parents "):
            print(obj)


    if args.walk:
        for (path, folders, files) in walk(creds, args.walk):
            print("Path:",path)
            for fname in files:
                print("   ",os.path.join(path,fname))
