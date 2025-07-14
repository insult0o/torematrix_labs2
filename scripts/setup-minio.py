#!/usr/bin/env python3
"""
Setup MinIO bucket for testing.

Creates the required S3 bucket and sets up proper permissions
for the TORE Matrix ingestion system testing.
"""

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import os
import time
import sys


def setup_minio():
    """Setup MinIO bucket for testing."""
    # MinIO connection settings
    endpoint_url = os.getenv('S3_ENDPOINT', 'http://minio:9000')
    access_key = os.getenv('S3_ACCESS_KEY', 'minioadmin')
    secret_key = os.getenv('S3_SECRET_KEY', 'minioadmin123')
    bucket_name = os.getenv('S3_BUCKET', 'test-documents')
    region = os.getenv('S3_REGION', 'us-east-1')
    
    print(f"Setting up MinIO bucket: {bucket_name}")
    print(f"Endpoint: {endpoint_url}")
    
    # Configure S3 client for MinIO
    config = Config(
        region_name=region,
        signature_version='s3v4',
        s3={
            'addressing_style': 'path'
        }
    )
    
    s3_client = boto3.client(
        's3',
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=config
    )
    
    # Wait for MinIO to be ready
    max_retries = 30
    for attempt in range(max_retries):
        try:
            s3_client.list_buckets()
            print("MinIO is ready!")
            break
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Waiting for MinIO... (attempt {attempt + 1}/{max_retries})")
                time.sleep(2)
            else:
                print(f"Failed to connect to MinIO after {max_retries} attempts: {e}")
                sys.exit(1)
    
    # Create bucket if it doesn't exist
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"Bucket '{bucket_name}' already exists")
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            try:
                s3_client.create_bucket(Bucket=bucket_name)
                print(f"Created bucket '{bucket_name}'")
            except ClientError as create_error:
                print(f"Failed to create bucket: {create_error}")
                sys.exit(1)
        else:
            print(f"Error checking bucket: {e}")
            sys.exit(1)
    
    # Set bucket policy for testing (allow public read for test files)
    bucket_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket_name}/test/*"
            }
        ]
    }
    
    try:
        import json
        s3_client.put_bucket_policy(
            Bucket=bucket_name,
            Policy=json.dumps(bucket_policy)
        )
        print(f"Set bucket policy for '{bucket_name}'")
    except ClientError as e:
        print(f"Warning: Could not set bucket policy: {e}")
    
    # Create test folder structure
    test_folders = [
        'test/',
        'uploads/',
        'processed/',
        'failed/'
    ]
    
    for folder in test_folders:
        try:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=folder,
                Body=b''
            )
            print(f"Created folder: {folder}")
        except ClientError as e:
            print(f"Warning: Could not create folder {folder}: {e}")
    
    print("MinIO setup completed successfully!")


if __name__ == '__main__':
    setup_minio()