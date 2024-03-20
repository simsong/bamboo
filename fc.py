#!/usr/bin/env python3

"""FoggyCam captures Nest camera images and generates a video."""

import os
from collections import defaultdict
import traceback
from subprocess import Popen, PIPE, call
from shlex import split as shsplit
import uuid
import threading
import time
from datetime import datetime
#from azurestorageprovider import AzureStorageProvider
import shutil
import requests
import json
from re import search as re_search


class FoggyCam(object):
  """FoggyCam client class that performs capture operations."""

  nest_user_id = ''
  nest_access_token = ''
  # nest_access_token_expiration = ''

  nest_user_url = 'https://home.nest.com/api/0.1/user/#USERID#/app_launch'
  nest_image_url = 'https://nexusapi-#REGION#.camera.home.nest.com/get_image?uuid=#CAMERAID#&width=#WIDTH#&cachebuster=#CBUSTER#'
  nest_auth_url = 'https://nestauthproxyservice-pa.googleapis.com/v1/issue_jwt'
  user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36'

  nest_user_request_payload = {
    "known_bucket_types": ["quartz"],
    "known_bucket_versions": []
  }

  nest_camera_array = []
  nest_camera_buffer_threshold = 50

  is_capturing = False
  cam_retry_wait = 60
  temp_dir_path = ''
  local_path = ''

  def __init__(self, config):
    self.config = config
    self.nest_access_token = None

    if not os.path.exists('_temp'):
      os.makedirs('_temp')

    self.cam_retry_wait = config.cam_retry_wait or self.cam_retry_wait

    self.local_path = os.path.dirname(os.path.abspath(__file__))
    self.temp_dir_path = os.path.join(self.local_path, '_temp')
    self.nest_camera_buffer_threshold = self.config.threshold or self.nest_camera_buffer_threshold

    self.ffmpeg_path = False

    self.time_stamp = self.config.time_stamp or False
    self.convert_path = False

    self.check_tools()
    self.get_authorisation()
    self.initialize_user()
    self.capture_images()

  def check_tools(self):
    imagemagic_path = shutil.which("convert")
    if not imagemagic_path:
      raise FileNotFound("convert --- install ImageMagick")

    ffmpeg_path     = shutil.which("ffmpeg")
    if not ffmpeg_path:
      raise FileNotFound("ffmpeg - install ffmpeg")

  @staticmethod
  def run_requests(url, method, headers=None, params=None, payload=None):
    method = method.lower()
    try:
      with requests.Session() as s:
        if method == 'get':
          r = s.get(url=url, headers=headers)
        elif method == 'post':
          r = s.post(url=url, headers=headers, params=params, json=payload)
        else:
          class X: reason = f"Failed: un-managed method: {method}"
          return False, X
        return True, r
    except Exception as all_error:
      print("<> ERROR: failed to perform request using: \n"
            f"<> URL: {url}\n"
            f"<> HEADERS: {headers}\n"
            f"<> PARAMS: {params}\n"
            f"<> RECEIVED ERROR: \n{all_error}")
      return False, all_error

  @staticmethod
  def now_time(form='%Y-%m-%d %H:%M:%S'):
    return datetime.now().strftime(form)

  def get_authorisation(self):
    """
    Step 1: Get Bearer token with cookies and issue_token
    Step 2: Use Bearer token to get an JWT access token, nestID
    """
    print("<> Getting Bearer token ...")
    headers = {
      'Sec-Fetch-Mode': 'cors',
      'User-Agent': self.user_agent,
      'X-Requested-With': 'XmlHttpRequest',
      'Referer': 'https://accounts.google.com/o/oauth2/iframe',
      'Cookie': self.config.cookies
    }

    status, resp = self.run_requests(self.config.issueToken, 'GET', headers=headers)
    access_token = ''

    print("status:",status)
    r = resp.json()
    print("resp:",r)

    if 'error' in r:
      raise RuntimeError(r['detail'])
    if status:
      try:
        access_token = resp.json().get('access_token')
      except Exception as no_token_error:
        print(f"ERROR: failed to get access_token with error: \n{no_token_error}")
        exit(1)
      print(f"<> Status: {resp.reason}")
    else:
      print(f"<> FAILED: unable to get Bearer token.")
      exit(1)

    if not access_token:
      raise RuntimeError("No access token")


    print("<> Getting Google JWT authorisation token ...")
    headers = {
      'Referer': 'https://home.nest.com/',
      'Authorization': 'Bearer ' + access_token,
      'X-Goog-API-Key': self.config.apiKey,  # Nest public APIkey 'AIzaSyAdkSIMNc51XGNEAYWasX9UOWkS5P6sZE4'
      'User-Agent': self.user_agent,
    }
    params = {
      'embed_google_oauth_access_token': True,
      'expire_after': '3600s',
      'google_oauth_access_token': access_token,
      'policy_id': 'authproxy-oauth-policy'
    }

    status, resp = self.run_requests(self.nest_auth_url, method='POST', headers=headers, params=params)
    if status:
      try:
        self.nest_access_token = resp.json().get('jwt')
        # self.nest_access_token_expiration = resp.json().get('claims').get('expirationTime')
        self.nest_user_id = resp.json().get('claims').get('subject').get('nestId').get('id')
      except Exception as jwt_error:
        print(f"ERROR: failed to get JWT access token with error: \n{jwt_error}")
        exit(1)
      print(f"<> Status: {resp.reason}")
    else:
      print(f"<> FAILED: unable to get JWT authorisation token.")
      exit(1)

  def initialize_user(self):
    """Gets the assets belonging to Nest user."""

    user_url = self.nest_user_url.replace('#USERID#', self.nest_user_id)

    print("<> Getting user's nest cameras assets ...")

    headers = {
      'Authorization': f"Basic {self.nest_access_token}",
      'Content-Type': 'application/json'
    }

    user_object = None

    payload = self.nest_user_request_payload
    status, resp = self.run_requests(user_url, method='POST', headers=headers, payload=payload)
    if status:
      try:
        user_object = resp.json()
      except Exception as assets_error:
        print(f"ERROR: failed to get user's assets error: \n{assets_error}")
        exit(1)
      print(f"<> Status: {resp.reason}")

      # user_object = resp.json()
      for bucket in user_object['updated_buckets']:
        bucket_id = bucket['object_key']
        if bucket_id.startswith('quartz.'):
          print("<> INFO: Detected camera configuration.")

          # Attempt to get cameras API region
          try:
            nexus_api_http_server_url = bucket['value']['nexus_api_http_server_url']
            region = re_search('https://nexusapi-(.+?).dropcam.com', nexus_api_http_server_url).group(1)
          except AttributeError:
            # Failed to find region - default back to us1
            region = 'us1'

          camera = {
            'name': bucket['value']['description'].replace(' ', '_'),
            'uuid': bucket_id.replace('quartz.', ''),
            'streaming_state': bucket['value']['streaming_state'],
            'region': region
          }
          # print(f"<> DEBUG: {bucket}")
          print(f"<> INFO: Camera Name: '{camera['name']}' UUID: '{camera['uuid']}' "
                f"STATE: '{camera['streaming_state']}'")
          self.nest_camera_array.append(camera)

  def capture_images(self, capture=True):
    """Starts the multi-threaded image capture process."""

    print(f"<> INFO: {self.now_time()} Capturing images ...")

    self.is_capturing = capture

    if not os.path.exists('capture'):
      os.makedirs('capture')

    for camera in self.nest_camera_array:
      camera_name = camera['name'] or camera['uuid']

      # Determine whether the entries should be copied to a custom path
      # or not.
      if not self.config.path:
        camera_path = os.path.join(self.local_path, 'capture', camera_name, 'images')
        video_path = os.path.join(self.local_path, 'capture', camera_name, 'video')
      else:
        camera_path = os.path.join(self.config.path, 'capture', camera_name, 'images')
        video_path = os.path.join(self.config.path, 'capture', camera_name, 'video')

      # Provision the necessary folders for images and videos.
      if not os.path.exists(camera_path):
        os.makedirs(camera_path)

      if not os.path.exists(video_path):
        os.makedirs(video_path)

      if camera['uuid'] not in self.config.exclude_ids:
        image_thread = threading.Thread(target=self.perform_capture,
                                        args=(camera, camera_name, camera_path, video_path))
        image_thread.start()
      else:
        print(f"<> INFO: '{camera_name}': Skipping recording for this camera.")

  def perform_capture(self, camera, camera_name, camera_path='', video_path=''):
    """Captures images and generates the video from them."""

    camera_buffer = defaultdict(list)
    image_url = self.nest_image_url.replace('#CAMERAID#', camera['uuid']
                                            ).replace('#WIDTH#', str(self.config.width)
                                                      ).replace('#REGION#', camera['region'])

    while self.is_capturing:
      file_id = datetime.now().isoformat() + ".jpg"
      image_path = f"{camera_path}/{file_id}"
      utc_date = datetime.utcnow()
      utc_millis_str = str(int(utc_date.timestamp())*1000)

      print(f"<> INFO: {self.now_time()} Applied cache buster: {utc_millis_str}")

      image_url = image_url.replace('#CBUSTER#', utc_millis_str)
      # print(f"<> DEBUG: image URL: {image_url}")

      headers = {
        'Origin': 'https://home.nest.com',
        'Referer': 'https://home.nest.com/',
        'Authorization': 'Basic ' + self.nest_access_token,
        'accept': 'image/webp,image/apng,image/*,*/*;q=0.9',
        'accept-encoding': 'gzip, deflate, br',
        'user-agent': self.user_agent,
      }

      status, resp = self.run_requests(image_url, method='GET', headers=headers)

      if status:
        # Check if the camera live feed is available
        if resp.status_code == 200:
          try:
            # time.sleep(self.config.frame_rate/60)
            time.sleep(0.1)

            with open(image_path, 'wb') as image_file:
              image_file.write(resp.content)

            # Add timestamp into jpg
            if self.convert_path:
              overlay_text = shsplit(f"{self.convert_path} {image_path} -pointsize 36 -fill white "
                                     f"-stroke black -annotate +40+40 '{self.now_time('%Y-%m-%d %H:%M:%S')}' "
                                     f"{image_path}")
              call(overlay_text)

            # Compile video
            if self.ffmpeg_path:
              camera_buffer_size = len(camera_buffer[camera['uuid']])
              print(
                f"<> INFO: {self.now_time()} [ {threading.current_thread().name} ] "
                f"Camera buffer size for {camera_name}: {camera_buffer_size}"
              )

              if camera_buffer_size < self.nest_camera_buffer_threshold:
                camera_buffer[camera['uuid']].append(file_id)

              else:
                camera_buffer[camera['uuid']].append(file_id)
                camera_image_folder = os.path.join(self.local_path, camera_path)

                # Add the batch of .jpg files that need to be made into a video.
                file_declaration = ''
                for buffer_entry in camera_buffer[camera['uuid']]:
                  file_declaration = f"{file_declaration}file '{camera_image_folder}/{buffer_entry}'\n"
                concat_file_name = os.path.join(self.temp_dir_path, camera['uuid'] + '.txt')

                # Write to file image list to be compressed into video
                with open(concat_file_name, 'w') as declaration_file:
                  declaration_file.write(file_declaration)

                print(f"<> INFO: {self.now_time()} {camera_name}: Processing video!")
                video_file_name = f"{self.now_time('%Y-%m-%d_%H-%M-%S')}.mp4"
                target_video_path = os.path.join(video_path, video_file_name)

                process = Popen(
                  [self.ffmpeg_path, '-r', str(self.config.frame_rate), '-f', 'concat', '-safe', '0', '-i',
                   concat_file_name, '-vcodec', 'libx264', '-crf', '25', '-pix_fmt', 'yuv420p',
                   target_video_path],
                  close_fds=False, start_new_session=True, stdout=PIPE, stderr=PIPE
                )

                process.communicate()
                os.remove(concat_file_name)
                print(f"<> INFO: {self.now_time()} {camera_name}: Video processing is complete!")

                # Upload the video
                print("won't upload video")
                """
                storage_provider = AzureStorageProvider()
                if self.config.upload_to_azure:
                  print('<> INFO: Uploading to Azure Storage...')
                  target_blob = f"foggycam/{camera_name}/{video_file_name}"

                  storage_provider.upload_video(
                    account_name=self.config.az_account_name,
                    sas_token=self.config.az_sas_token,
                    container='foggycam',
                    blob=target_blob,
                    path=target_video_path
                  )
                """
                print('<> INFO: Upload complete.')

                # If the user specified the need to remove images post-processing
                # then clear the image folder from images in the buffer.
                if self.config.clear_images:
                  clean_files = []
                  for buffer_entry in camera_buffer[camera['uuid']]:
                    clean_files.append(os.path.join(camera_path, buffer_entry))

                  print(f"<> INFO: Deleting compiled images {clean_files}")
                  call(shsplit('rm -f') + shsplit(' '.join(clean_files)))

                # Empty buffer, since we no longer need the file records that we're planning
                # to compile in a video.
                camera_buffer[camera['uuid']] = []
          except Exception as img_error:
            print(f"<> ERROR: {self.now_time()} {camera_name}: while getting image ... \n {img_error} \n")
            print(f"<> DEBUG: image URL {image_url}")
            traceback.print_exc()

        else:
          # camera is offline
          if resp.status_code == 404:
            print(f"<> WARNING: {self.now_time()} {camera_name}: recording not available.")
            time.sleep(self.cam_retry_wait)

          # Renew auth token
          elif resp.status_code == 403:
            print(f"<> DEBUG: {self.now_time()} {camera_name}: status '{resp.reason}' token expired renewing ...")
            self.get_authorisation()

          elif resp.status_code == 500:
            sleep_time = 30
            print(f"<> DEBUG: {self.now_time()} {camera_name}: '{resp.reason}' ... failure received sleeping for "
                  f"{sleep_time} seconds.")
            time.sleep(sleep_time)

          else:
            print(f"<> DEBUG: {self.now_time()} {camera_name}: Ignoring status code '{resp.status_code}'")
      else:
        print(f"<> ERROR: {camera_name}: failed to capture images")
        exit(1)


if __name__ == '__main__':
  try:
    import json
    from collections import namedtuple
    print("Welcome to FoggyCam2 2.0 - Nest video/image capture tool")

    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'config.json'))
    print(f"reading config from {config_path}")

    config = json.load(open(config_path), object_hook=lambda d: namedtuple('X', d.keys())(*d.values()))

    print("CONFIG:",config)

    cam = FoggyCam(config=config)
  except KeyboardInterrupt:
    print("FoggyCam2 2.0 - Nest video/image capture tool ended.")
