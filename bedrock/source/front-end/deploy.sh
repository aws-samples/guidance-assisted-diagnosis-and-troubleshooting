#!/bin/sh

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

AWS_DEFAULT_REGION="us-east-1"

set -e
trap 'echo "******* FAILED *******" 1>&2' ERR

# Install dependencies
npm install

# Check if running on macOS or Linux
if [[ "$OSTYPE" == "darwin"* ]]; then
  # macOS sed 
  echo "Running on macOS..."
  alias sed_cmd="sed -i ''"
else
  # Linux sed
  echo "Running on Linux..."
  alias sed_cmd="sed -i"
fi

# Retrieve outputs from the Bedrock stack
BEDROCK_STACK_OUTPUTS=$(aws cloudformation describe-stacks --stack-name "ADBStack" --output json | jq '.Stacks[0].Outputs')
COGNITO_CLIENT_ID=$(echo "$BEDROCK_STACK_OUTPUTS" | jq -r '.[] | select(.OutputKey=="UserPoolClientId").OutputValue')
COGNITO_IDEN_POOL_ID=$(echo "$BEDROCK_STACK_OUTPUTS" | jq -r '.[] | select(.OutputKey=="IdentityPoolId").OutputValue')
COGNITO_USER_POOL_ID=$(echo "$BEDROCK_STACK_OUTPUTS" | jq -r '.[] | select(.OutputKey=="UserPoolId").OutputValue')

echo "BEDROCK_STACK_OUTPUTS: $BEDROCK_STACK_OUTPUTS"

# Retrieve outputs from the Frontend stack
CFN_STACK_OUTPUTS=$(aws cloudformation describe-stacks --stack-name "FrontendStack" --output json | jq '.Stacks[0].Outputs')
FRONTEND_ASSETS_BUCKET_NAME=$(echo "$CFN_STACK_OUTPUTS" | jq -r '.[] | select(.OutputKey=="FrontEndAssetsBucket").OutputValue')
CLOUDFRONT_DIST=$(echo "$CFN_STACK_OUTPUTS" | jq -r '.[] | select(.OutputKey=="DistributionDomainName").OutputValue')

echo "FRONTEND_STACK_OUTPUTS: $CFN_STACK_OUTPUTS"

script_output=$(node ./script/getSitewiseEnv.js)

# Print the output (optional)
echo "Script Output: $script_output"


ROASTER_ID=$(echo "$script_output" | jq -r '.roasterAssetID')
HOLD_TIME_PROPERTY=$(echo "$script_output" | jq -r '.roasterProperities.holdTimeID')
TEMPERATURE_PROPERTY=$(echo "$script_output" | jq -r '.roasterProperities.temperature')
SCRAP_PROPERTY=$(echo "$script_output" | jq -r '.roasterProperities.scrap')
OEE_PROPERTY=$(echo "$script_output" | jq -r '.roasterProperities.oeePer5min')
PERFORMANCE_PROPERTY=$(echo "$script_output" | jq -r '.roasterProperities.performancePer5min')
QUALITY_PROPERTY=$(echo "$script_output" | jq -r '.roasterProperities.qualityPer5min')
UTILIZATION_PROPERTY=$(echo "$script_output" | jq -r '.roasterProperities.utilizationPer5min')
RUNTIME_PROPERTY=$(echo "$script_output" | jq -r '.roasterProperities.runtime')


# Write environment variables to .env file
cat <<EOT > .env
REACT_APP_AWS_REGION=$AWS_DEFAULT_REGION
REACT_APP_COGNITO_CLIENT_ID=$COGNITO_CLIENT_ID
REACT_APP_COGNITO_IDENTITY_POOL_ID=$COGNITO_IDEN_POOL_ID
REACT_APP_COGNITO_USER_POOL_ID=$COGNITO_USER_POOL_ID
REACT_APP_REST_API_ENDPOINT=$CLOUDFRONT_DIST/api/v1/chat
REACT_APP_ROASTER_ID=$ROASTER_ID
REACT_APP_HOLD_TIME_PROPERTY=$HOLD_TIME_PROPERTY
REACT_APP_TEMPERATURE_PROPERTY=$TEMPERATURE_PROPERTY
REACT_APP_SCRAP_PROPERTY=$SCRAP_PROPERTY
REACT_APP_OEE_PROPERTY=$OEE_PROPERTY
REACT_APP_PERFORMANCE_PROPERTY=$PERFORMANCE_PROPERTY
REACT_APP_QUALITY_PROPERTY=$QUALITY_PROPERTY
REACT_APP_UTILIZATION_PROPERTY=$UTILIZATION_PROPERTY
REACT_APP_RUNTIME_PROPERTY=$RUNTIME_PROPERTY
EOT

echo ".env file created with environment variables."

# Build the front-end
echo "Building front end..."
npm run build

# Ensure the build directory exists
if [ ! -d "./build" ]; then
  echo "Directory ./build does not exist."
  exit 1
fi

echo "FRONTEND_ASSETS_BUCKET_NAME $FRONTEND_ASSETS_BUCKET_NAME"

# Sync the build to the S3 bucket
aws s3 sync "./build" "s3://$FRONTEND_ASSETS_BUCKET_NAME/web/" --delete

echo "Application is deployed at $CLOUDFRONT_DIST"
echo "Front end app setup complete."
