import os
import json

from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend as crypto_default_backend

import google.auth
import googleapiclient.discovery


def generate_ssh_key():
    # Generate private key
    key = rsa.generate_private_key(
        backend=crypto_default_backend(),
        public_exponent=65537,
        key_size=2048
    )
    # Export private and public key as strings
    private_key = key.private_bytes(
        crypto_serialization.Encoding.PEM,
        crypto_serialization.PrivateFormat.PKCS8,
        crypto_serialization.NoEncryption()).decode('utf-8')
    public_key = key.public_key().public_bytes(
        crypto_serialization.Encoding.OpenSSH,
        crypto_serialization.PublicFormat.OpenSSH)
    # Add username to public key
    public_key = public_key.decode('utf-8')

    return private_key, public_key


def generate_service_account_key(service_account_email):
    # Get current credentials from environment variables and build deployment API object
    credentials, project_id = google.auth.default()
    iam_api = googleapiclient.discovery.build(
        'iam', 'v1', credentials=credentials)
    # Create new key
    key = iam_api.projects().serviceAccounts().keys().create(
        name=f'projects/{project_id}/serviceAccounts/{service_account_email}', body={}).execute()
    # Get service account ID
    account_ID = iam_api.projects().serviceAccounts().get(
        name=f'projects/{project_id}/serviceAccounts/{service_account_email}')['uniqueID']
    # Assemble object in key file format
    key_file = {
        "type": "service_account",
        "project_id": project_id,
        "private_key_id": os.path.basename(key['name']),
        "private_key": key['privateKeyData'],
        "client_email": service_account_email,
        "client_id": account_ID,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://accounts.google.com/o/oauth2/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url":
        f"https://www.googleapis.com/robot/v1/metadata/x509/{service_account_email}"
    }
    # Return json string
    return json.dumps(key_file)