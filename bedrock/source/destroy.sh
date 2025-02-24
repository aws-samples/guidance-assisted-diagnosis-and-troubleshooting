#!/bin/bash

# Variables
ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
REGION="us-east-1"  # Set the desired AWS region
STACK_NAMES=("SimulatorServerStack", "SiteWiseAssetsStack")  # List of specific stacks to delete
MAX_RETRIES=3  # Number of retries for deleting stacks in case of failure
BUCKET_NAME="template-bucket-$ACCOUNT_ID" 

# Function to delete a stack
delete_stack() {
  local STACK_NAME=$1

  echo "Attempting to delete stack: $STACK_NAME"
  
  # Attempt to delete the stack
  aws cloudformation delete-stack --stack-name "$STACK_NAME" --region "$REGION"
  
  # Wait for the stack to be deleted
  aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME" --region "$REGION"
  
  if [ $? -eq 0 ]; then
    echo "Stack $STACK_NAME deleted successfully."
  else
    echo "Failed to delete stack $STACK_NAME."
    exit 1
  fi
}

# Loop through the list of stacks to delete
for STACK_NAME in "${STACK_NAMES[@]}"; do
  RETRY_COUNT=0
  SUCCESS=0

  while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    delete_stack "$STACK_NAME"
    if [ $? -eq 0 ]; then
      SUCCESS=1
      break
    else
      echo "Retrying to delete stack $STACK_NAME... ($((RETRY_COUNT + 1))/$MAX_RETRIES)"
      RETRY_COUNT=$((RETRY_COUNT + 1))
    fi
  done

  if [ $SUCCESS -eq 0 ]; then
    echo "Failed to delete stack $STACK_NAME after $MAX_RETRIES retries."
    exit 1
  fi
done

echo "Selected stacks deleted successfully."

echo "destroy cdk stack"

cdk destroy --all

echo "cdk stack destroyed"


# Confirm the bucket exists before proceeding
aws s3 ls "s3://$BUCKET_NAME" > /dev/null 2>&1

if [ $? -ne 0 ]; then
  echo "Error: Bucket $BUCKET_NAME does not exist or you do not have access."
  exit 1
fi

# Delete all objects in the bucket
echo "Deleting all objects in the bucket: $BUCKET_NAME"
aws s3 rm "s3://$BUCKET_NAME" --recursive

if [ $? -ne 0 ]; then
  echo "Error: Failed to delete objects in the bucket."
  exit 1
fi

# Delete the bucket
echo "Deleting the bucket: $BUCKET_NAME"
aws s3api delete-bucket --bucket "$BUCKET_NAME"

if [ $? -eq 0 ]; then
  echo "Bucket $BUCKET_NAME deleted successfully."
else
  echo "Error: Failed to delete the bucket $BUCKET_NAME."
  exit 1
fi