#!/bin/sh

# Variables for both stacks
ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
REGION="us-east-1"  # AWS region
BUCKET_NAME="template-bucket-$ACCOUNT_ID"  # New S3 bucket name, you can also use a custom name

# Stack 1: SiteWise Assets Stack
STACK_NAME_1="SiteWiseAssetsStack"
TEMPLATE_FILE_1="sitewise-assets-reduced.json"
TEMPLATE_PATH_1="cfn/${TEMPLATE_FILE_1}"
S3_TEMPLATE_URL_1="https://$BUCKET_NAME.s3.$REGION.amazonaws.com/${TEMPLATE_FILE_1}"

# Stack 2: Simulator Server Stack
STACK_NAME_2="SimulatorServerStack"
TEMPLATE_FILE_2="simulator-server.json"
TEMPLATE_PATH_2="cfn/${TEMPLATE_FILE_2}"
S3_TEMPLATE_URL_2="https://$BUCKET_NAME.s3.$REGION.amazonaws.com/${TEMPLATE_FILE_2}"

# InstanceType Parameter for Simulator Server
INSTANCE_TYPE="t2.micro"  # Set your desired instance type here

# Function to create S3 bucket
create_s3_bucket() {
  local BUCKET_NAME=$1
  echo "Creating S3 bucket: $BUCKET_NAME..."

  aws s3api create-bucket --bucket "$BUCKET_NAME" --region "$REGION"

  if [ $? -eq 0 ]; then
    echo "S3 bucket $BUCKET_NAME created successfully."
  else
    echo "Failed to create S3 bucket $BUCKET_NAME."
    exit 1
  fi
}

# Function to upload template to S3
upload_template_to_s3() {
  local TEMPLATE_FILE=$1

  echo "Uploading $TEMPLATE_FILE to S3 bucket $BUCKET_NAME..."
  aws s3 cp "$TEMPLATE_FILE" "s3://$BUCKET_NAME/" --region "$REGION"

  if [ $? -eq 0 ]; then
    echo "Template $TEMPLATE_FILE uploaded successfully."
  else
    echo "Failed to upload template $TEMPLATE_FILE."
    exit 1
  fi
}

# Function to deploy or update a stack
deploy_stack() {
  local STACK_NAME=$1
  local TEMPLATE_URL=$2
  local PARAMETERS=$3

  # Check if the stack already exists
  STACK_EXISTS=$(aws cloudformation describe-stacks --region "$REGION" --stack-name "$STACK_NAME" --query "Stacks[0].StackId" --output text 2>/dev/null)

  if [ "$STACK_EXISTS" != "" ]; then
    echo "Updating existing stack: $STACK_NAME"

    # Update the existing stack
    if [ -z "$PARAMETERS" ]; then
      aws cloudformation update-stack \
        --stack-name "$STACK_NAME" \
        --template-url "$TEMPLATE_URL" \
        --region "$REGION" \
        --capabilities CAPABILITY_NAMED_IAM
    else
      aws cloudformation update-stack \
        --stack-name "$STACK_NAME" \
        --template-url "$TEMPLATE_URL" \
        --region "$REGION" \
        --parameters "$PARAMETERS" \
        --capabilities CAPABILITY_NAMED_IAM
    fi

    # Wait for the update to complete
    aws cloudformation wait stack-update-complete --stack-name "$STACK_NAME" --region "$REGION"

    echo "Stack update completed for $STACK_NAME."
  else
    echo "Creating new stack: $STACK_NAME"

    # Create a new stack
    if [ -z "$PARAMETERS" ]; then
      aws cloudformation create-stack \
        --stack-name "$STACK_NAME" \
        --template-url "$TEMPLATE_URL" \
        --region "$REGION" \
        --capabilities CAPABILITY_NAMED_IAM
    else
      aws cloudformation create-stack \
        --stack-name "$STACK_NAME" \
        --template-url "$TEMPLATE_URL" \
        --region "$REGION" \
        --parameters "$PARAMETERS" \
        --capabilities CAPABILITY_NAMED_IAM
    fi

    # Wait for the stack creation to complete
    aws cloudformation wait stack-create-complete --stack-name "$STACK_NAME" --region "$REGION"

    echo "Stack creation completed for $STACK_NAME."
  fi

  # Output stack status
  STACK_STATUS=$(aws cloudformation describe-stacks --region "$REGION" --stack-name "$STACK_NAME" --query "Stacks[0].StackStatus" --output text)

  echo "CloudFormation Stack Status for $STACK_NAME: $STACK_STATUS"

  if [ "$STACK_STATUS" == "CREATE_COMPLETE" ] || [ "$STACK_STATUS" == "UPDATE_COMPLETE" ]; then
    echo "Stack $STACK_NAME deployed successfully."
  else
    echo "Stack $STACK_NAME deployment failed with status: $STACK_STATUS"
    exit 1
  fi
}

# Create new S3 bucket
create_s3_bucket "$BUCKET_NAME"

# Upload templates to S3
upload_template_to_s3 "$TEMPLATE_PATH_1"
upload_template_to_s3 "$TEMPLATE_PATH_2"

# Deploy the first stack (SiteWise Assets) without parameters
deploy_stack "$STACK_NAME_1" "$S3_TEMPLATE_URL_1"

# Deploy the second stack (Simulator Server) with the InstanceType parameter
PARAMETERS_SIMULATOR="ParameterKey=InstanceType,ParameterValue=$INSTANCE_TYPE"
deploy_stack "$STACK_NAME_2" "$S3_TEMPLATE_URL_2" "$PARAMETERS_SIMULATOR"


aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws


cdk deploy --all
