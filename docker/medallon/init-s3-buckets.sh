#!/bin/bash
awslocal s3 mb s3://agrosense-bronze
awslocal s3 mb s3://agrosense-silver
awslocal s3 mb s3://agrosense-gold
awslocal s3 mb s3://agrosense-backups
echo "Buckets de S3 creados exitosamente en LocalStack."
