#!/bin/sh

# Variables for both stacks
ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
REGION="us-east-1"  # AWS region
BUCKET_NAME="template-bucket-$ACCOUNT_ID"  # New S3 bucket name, you can also use a custom name
VENV_PATH=".venv/bin/activate"  # Virtual environment path

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
  fi
}

# Function to deploy or update a stack
deploy_stack() {
  local STACK_NAME=$1
  local TEMPLATE_URL=$2
  local PARAMETERS=$3

  echo "Checking if stack $STACK_NAME exists..."
  STACK_EXISTS=$(aws cloudformation describe-stacks --region "$REGION" --stack-name "$STACK_NAME" --query "Stacks[0].StackId" --output text 2>/dev/null || echo "DOES_NOT_EXIST")

  if [ "$STACK_EXISTS" == "DOES_NOT_EXIST" ]; then
    echo "Stack $STACK_NAME does not exist. Creating a new stack..."

    aws cloudformation validate-template --template-url "$TEMPLATE_URL" --region "$REGION" > /dev/null
    if [ $? -ne 0 ]; then
      echo "Error: CloudFormation template validation failed for $TEMPLATE_URL."
      exit 1
    fi

    # Create new stack
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

    echo "Waiting for stack creation to complete..."
    aws cloudformation wait stack-create-complete --stack-name "$STACK_NAME" --region "$REGION"

    echo "Stack creation completed for $STACK_NAME."

  else
    echo "Stack $STACK_NAME exists. Updating the stack..."

    if [ -z "$PARAMETERS" ]; then
      UPDATE_OUTPUT=$(aws cloudformation update-stack \
        --stack-name "$STACK_NAME" \
        --template-url "$TEMPLATE_URL" \
        --region "$REGION" \
        --capabilities CAPABILITY_NAMED_IAM 2>&1)
    else
      UPDATE_OUTPUT=$(aws cloudformation update-stack \
        --stack-name "$STACK_NAME" \
        --template-url "$TEMPLATE_URL" \
        --region "$REGION" \
        --parameters "$PARAMETERS" \
        --capabilities CAPABILITY_NAMED_IAM 2>&1)
    fi

    if echo "$UPDATE_OUTPUT" | grep -q "No updates are to be performed"; then
      echo "No updates detected. Stack $STACK_NAME is already up to date."
      return 0
    fi

    echo "Waiting for stack update to complete..."
    aws cloudformation wait stack-update-complete --stack-name "$STACK_NAME" --region "$REGION"

    echo "Stack update completed for $STACK_NAME."
  fi

  # Output stack status
  STACK_STATUS=$(aws cloudformation describe-stacks --region "$REGION" --stack-name "$STACK_NAME" --query "Stacks[0].StackStatus" --output text 2>/dev/null || echo "DOES_NOT_EXIST")

  if [ "$STACK_STATUS" == "DOES_NOT_EXIST" ]; then
    echo "Error: Stack $STACK_NAME does not exist after deployment."
    exit 1
  fi

  echo "CloudFormation Stack Status for $STACK_NAME: $STACK_STATUS"

  if [[ "$STACK_STATUS" == "CREATE_COMPLETE" || "$STACK_STATUS" == "UPDATE_COMPLETE" ]]; then
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

# AWS ECR Public Login
echo "Logging into AWS ECR Public..."
aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws
if [ $? -eq 0 ]; then
  echo "Docker login successful."
else
  echo "Error: Docker login failed."
  exit 1
fi

# Activate virtual environment before CDK deploy
if [ -f "$VENV_PATH" ]; then
  echo "Activating virtual environment..."
  source "$VENV_PATH"
else
  echo "Error: Virtual environment not found at $VENV_PATH"
  exit 1
fi

# CDK Deploy
echo "Deploying CDK stacks..."
cdk deploy --all
if [ $? -eq 0 ]; then
  echo "CDK stacks deployed successfully."
else
  echo "Error: CDK deployment failed."
  exit 1
fi
