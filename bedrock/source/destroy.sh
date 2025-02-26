#!/bin/bash

# Variables
ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
REGION="us-east-1"  # Set the desired AWS region
STACK_NAMES=("SimulatorServerStack" "SiteWiseAssetsStack")  # Fixed: No comma
MAX_RETRIES=3  # Number of retries for deleting stacks in case of failure
BUCKET_NAME="template-bucket-$ACCOUNT_ID"
VENV_PATH=".venv/bin/activate"  # Virtual environment path

# Function to check if a stack exists
stack_exists() {
  local STACK_NAME=$1
  aws cloudformation describe-stacks --region "$REGION" --stack-name "$STACK_NAME" --query "Stacks[0].StackId" --output text 2>/dev/null
}

# Function to delete a stack
delete_stack() {
  local STACK_NAME=$1

  # Check if stack exists before attempting deletion
  if ! stack_exists "$STACK_NAME"; then
    echo "Stack $STACK_NAME does not exist. Skipping deletion."
    return 0
  fi

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

# Activate virtual environment before destroying CDK stack
if [ -f "$VENV_PATH" ]; then
  echo "Activating virtual environment..."
  source "$VENV_PATH"
else
  echo "Error: Virtual environment not found at $VENV_PATH"
  exit 1
fi

# Destroy CDK stack
echo "Destroying CDK stack..."
cdk destroy --all -f  # Added `-f` to force confirmation
if [ $? -eq 0 ]; then
  echo "CDK stack destroyed."
else
  echo "Error: CDK stack destruction failed."
  exit 1
fi

# Confirm the bucket exists before proceeding
if ! aws s3api head-bucket --bucket "$BUCKET_NAME" --region "$REGION" 2>/dev/null; then
  echo "Bucket $BUCKET_NAME does not exist. Skipping deletion."
else
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
fi
