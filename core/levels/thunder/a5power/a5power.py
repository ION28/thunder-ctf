import random
import os

import google.auth
from googleapiclient import discovery
from google.cloud import storage

from core.framework import levels
from core.framework.cloudhelpers import deployments, iam, cloudfunctions

LEVEL_PATH = 'thunder/a5power'
RESOURCE_PREFIX = 'a5'
FUNCTION_LOCATION = 'us-central1'


def create(second_deploy=True):
    # Create randomized bucket name to avoid namespace conflict
    nonce = str(random.randint(100000000000, 999999999999))
    bucket_name = f'{RESOURCE_PREFIX}-bucket-{nonce}'

    # Set role of default cloud function account
    credentials, project_id = google.auth.default()
    
    func_upload_url = cloudfunctions.upload_cloud_function(
        f'core/levels/{LEVEL_PATH}/function', FUNCTION_LOCATION)
    print("Level initialization finished for: " + LEVEL_PATH)
    # Insert deployment
    config_template_args = {'nonce': nonce,
                            'func_upload_url': func_upload_url}
    template_files = [
        'core/framework/templates/service_account.jinja',
        'core/framework/templates/cloud_function.jinja',
        'core/framework/templates/iam_policy.jinja',
        'core/framework/templates/bucket_acl.jinja']
   
    if second_deploy:
        deployments.insert(LEVEL_PATH, template_files=template_files, config_template_args=config_template_args, second_deploy=True)
    else:
        deployments.insert(LEVEL_PATH, template_files=template_files,
                       config_template_args=config_template_args)
    try:

        print("Level setup started for: " + LEVEL_PATH)
        # Allow player to use cloud function's service account
        iam_api = discovery.build('iam', 'v1', credentials=credentials)
        policy_body = {"policy": {
            "bindings": [{
                "members": [f"serviceAccount:a5-access@{project_id}.iam.gserviceaccount.com"],
                "role": "roles/iam.serviceAccountUser"}]}}
        iam_api.projects().serviceAccounts().setIamPolicy(
            resource=f'projects/{project_id}/serviceAccounts/a5-func-{nonce}-sa@{project_id}.iam.gserviceaccount.com', body=policy_body).execute()

        # Insert secret into bucket
        storage_client = storage.Client()
        bucket = storage_client.get_bucket(bucket_name)
        secret_blob = storage.Blob('secret.txt', bucket)
        secret = levels.make_secret(LEVEL_PATH)
        secret_blob.upload_from_string(secret)

        # Create service account key file
        sa_key = iam.generate_service_account_key(f'{RESOURCE_PREFIX}-access')
        print(f'Level creation complete for: {LEVEL_PATH}')
        start_message = (
            f'Use the compromised service account credentials stored in {RESOURCE_PREFIX}-access.json to find the secret, '
            'which is located in a file called secret.txt in a private bucket on the project.')
        levels.write_start_info(
            LEVEL_PATH, start_message, file_name=f'{RESOURCE_PREFIX}-access.json', file_content=sa_key)
        print(
            f'Instruction for the level can be accessed at thunder-ctf.cloud/thunder/{LEVEL_PATH}.html')
    except Exception as e: 
        exit()

def destroy():
    # Delete starting files
    levels.delete_start_files()
    # Delete deployment
    deployments.delete()
