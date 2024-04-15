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

DEFAULT_PAGE_SIZE = 50

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

# predefined google drive searches (name,args,query) triplets
# See https://developers.google.com/drive/api/v3/reference/files
# Note that spaces seem to matter
GFILE_QUERIES = [ ('all reachable images',
                   {'corpus':'user', 'includeItemsFromAllDrives':True , 'supportsAllDrives':True, 'supportsTeamDrives':True},
                   "(mimeType='image/jpeg') or (mimeType='image/png') or (mimeType='image/tiff') or (mimeType='image/webp')"),
                  ('all reachable movies',
                   {'corpus':'user', 'includeItemsFromAllDrives':True , 'supportsAllDrives':True, 'supportsTeamDrives':True},
                   "(mimeType='image/jpeg') or (mimeType='image/png') or (mimeType='image/tiff') or (mimeType='image/webp')"),
                 ]

FOLDER_MIME_TYPE      = "application/vnd.google-apps.folder"
IS_FOLDER             = f"(mimeType  = '{FOLDER_MIME_TYPE}')"
IS_NOT_FOLDER         = f"(mimeType  != '{FOLDER_MIME_TYPE}')"
FOLDERS_SHARED_WITH_ME=f"(sharedWithMe = true) and {IS_FOLDER}"
FILES_SHARED_WITH_ME  =f"(sharedWithMe = true) and {IS_NOT_FOLDER}"

# Default fields for each search
DEFAULT_FILE_FIELDS   = ['id','name','mimeType']

import json
import os
import os.path
import sys
import functools

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import googleapiclient.errors

from google_auth_oauthlib.flow import InstalledAppFlow

################################################################
## Authorization

def get_app_credentials(*,client_secret,oauth_token_filename):
    creds = None
    # The file OAUTH_TOKEN_FILENAME stores the user's access and
    # refresh tokens, and is created automatically when the
    # authorization flow completes for the first time.
    if os.path.exists(oauth_token_filename):
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
##

known_drives = {}
def list_drives(creds):
    """Return a generator that of all the drives, each as a dictionary that contains ['name'] and ['id'], that the user can reach"""
    drive = build('drive', 'v3', credentials=creds)
    drives = drive.drives()
    pageToken = None
    while True:
        results = drives.list(pageSize=DEFAULT_PAGE_SIZE,
                              pageToken=pageToken).execute()
        if 'drives' not in results or len(results['drives'])==0:
            return
        for drive in results['drives']:
            yield drive
        if 'nextPageToken' not in results:
            return
        pageToken = results['nextPageToken']

def cache_all_drives(creds):
    for drive in list_drives(creds):
        known_drives[drive['id']] = drive

# Some useful queries
@functools.lru_cache(maxsize=128)
def get_obj(creds, fileId):
    """Just return the name of a Id"""
    f = build('drive', 'v3', credentials=creds).files().get(fileId=fileId, fields=",".join(DEFAULT_FILE_FIELDS+['parents']), supportsAllDrives=True, supportsTeamDrives=True).execute()
    return f

def name(creds, fileId):
    """Just return the name of a Id"""
    if fileId in known_drives:
        return "<<"+known_drives[fileId]['name']+">>"
    return get_obj(creds,fileId)['name']

def parent_id(creds, fileId):
    """Return the fileId of the file's parent"""
    try:
        parentId = get_obj(creds,fileId)['parents'][0]
        return parentId if parentId != fileId else None
    except KeyError:
        return None

@functools.lru_cache(maxsize=128)
def full_path(creds, fileId):
    parentId = parent_id(creds, fileId)
    if parentId is None:
        # Get the drive name if we can find it
        try:
            return "[" + known_drives[fileId]['name'] + "]"
        except KeyError:
            return "[unknown]"
    return full_path(creds, parentId) + "/" + name(creds, fileId)

def gfiles_list(creds, q, *, extra_args={}, file_fields_add=[]):
    """Return a generator that of all items that match a query. A list of queries is above in GFILES_QUERIES, or you can make your own!
    https://developers.google.com/drive/api/reference/rest/v2/files

    :param: extra_args is extra arguments for the files.list() API call
    :param: file_fields_add is fields to add beyond those in DEFAULT_FILE_FIELDS (id, name, mimeType)
    """
    drive = build('drive', 'v3', credentials=creds)
    drives = drive.drives()
    files  = drive.files()
    file_fields = ",".join(set(DEFAULT_FILE_FIELDS + file_fields_add))
    pageToken = None
    while True:
        default_args = {'pageSize':DEFAULT_PAGE_SIZE,
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


################################################################
## Drive and shared file listing
def list_folders(creds):
    """Generator that returns all folders shared with the user, each as a dictionary that contains
    ['name'] and ['id']"""
    yield from gfiles_list(creds, q=FOLDERS_SHARED_WITH_ME)


################################################################
###

def gdrive_walk(creds, dirId, path='', file_fields_add=[]):
    """Similar to os.path.walk(), except returns (root, files, dirs) for a google directory, recursively down."""
    if path=='':
        path = name(creds, dirId)
    all     = list( gfiles_list(creds, q=f"('{dirId}' in parents)", file_fields_add=file_fields_add))
    folders = [ item for item in all if item.get('mimeType',None)==FOLDER_MIME_TYPE]
    files   = [ item for item in all if item.get('mimeType',None)!=FOLDER_MIME_TYPE]

    yield (path, folders, files)
    for folder in folders:
        yield from gdrive_walk(creds, folder['id'], path+"/"+folder['name'], file_fields_add=file_fields_add)


def GoogleDriveFrameStream():
    pass

def print_obj(creds, obj, print_path=False):
    if print_path:
        print( full_path(creds, obj['id']))
    print(obj)
    print("")

def print_objs(objs, print_path=False):
    for obj in objs:
        print_obj(obj, print_path=print_path)


if __name__=="__main__":
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """

    import argparse
    parser = argparse.ArgumentParser(description="Obtain OAuth2 credentials and list available Google Drives.",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument( '--listdrives', help='List drives', action='store_true')
    parser.add_argument( '--listfolder', help='List contents of a folder Id')
    parser.add_argument( '--client_secret', default=APP_CREDENTIALS_FILENAME)
    parser.add_argument( '--oauth', default=OAUTH_TOKEN_FILENAME)
    parser.add_argument( '--shared', help='List folders shared with you', action='store_true')
    parser.add_argument( '--limit', help='Limit to this many outputs', type=int)
    parser.add_argument( '--walk', help='walk the provided Id recursively')
    parser.add_argument( '--query', help='Run one of the numbered queries. Specify 0 to list all the queries',type=int)
    parser.add_argument( '--path', help='When printing an object, display its full path', action='store_true')
    parser.add_argument( '--q', help='Specify a query')
    parser.add_argument( 'Ids', help='Ids that you want to list', nargs='*')

    args = parser.parse_args()
    creds = get_app_credentials(client_secret=args.client_secret, oauth_token_filename=args.oauth)

    if args.path:
        cache_all_drives(creds)


    if args.listdrives:
        print_objs( sorted(list_drives(creds), key=lambda k:k['name']) )

    if args.shared:
        for obj in list_folders(creds):
            print_obj(creds, obj, print_path=args.path)

    if args.listfolder:
        for obj in gfiles_list(creds, q = f"'{args.listfolder}' in parents "):
            print_obj(creds, obj, print_path=args.path)

    if args.q:
        for obj in gfiles_list(creds, q=args.q):
            print_obj(creds, obj, print_path=args.path)

    if args.query is not None:
        if args.query==0:
            print("Queries:")
            for (ct,(n,args,q)) in enumerate(GFILE_QUERIES,1):
                print(ct,n,q)
        else:
            (n,a,q) = GFILE_QUERIES[args.query-1]
            print(n,"---",q)
            for obj in gfiles_list(creds, q=q, extra_args=a):
                print_obj(creds, obj, print_path=args.path)

    if args.walk:
        for (path, folder_objs, file_objs) in gdrive_walk(creds, args.walk):
            print("Path:",path)
            for file_obj in file_objs:
                print("   ",path,file_obj)
