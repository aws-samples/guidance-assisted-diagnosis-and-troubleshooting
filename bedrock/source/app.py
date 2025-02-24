#!/usr/bin/env python3
import os

import aws_cdk as cdk

from stacks.bedrock_stack import BedrockStack
from stacks.frontend_stack import FrontendStack
from cdk_nag import AwsSolutionsChecks, NagSuppressions, NagPack


app = cdk.App()


bedrock_stack = BedrockStack(app, "ADBStack")

frontend_stack = FrontendStack(
    app, 
    "FrontendStack", 
    bedrock_stack.x_origin_verify_secret,
    bedrock_stack.api_gateway,
    bedrock_stack.identity_pool
)

cdk.Aspects.of(app).add(AwsSolutionsChecks())

NagSuppressions.add_stack_suppressions(
    bedrock_stack,
    suppressions=[
        {"id": "AwsSolutions-S1", "reason": "Server access logs are not needed for this bucket in this use case."},
        {"id": "AwsSolutions-IAM4", "reason": "AWS managed policies are used for simplicity and maintained by AWS."},
        {"id": "AwsSolutions-IAM5", "reason": "Wildcards are required for broad access in this specific role."},
        {"id": "AwsSolutions-L1", "reason": "Non-container Lambda function will be upgraded in the future."},
        {"id": "AwsSolutions-COG1", "reason": "Cognito user pool password policy is customized for internal users."},
        {"id": "AwsSolutions-COG2", "reason": "MFA is not required for this application due to its user base."},
        {"id": "AwsSolutions-COG3", "reason": "AdvancedSecurityMode is not enforced for cost-saving purposes."},
        {"id": "AwsSolutions-SMG4", "reason": "Automatic rotation of secrets is not needed at this time."},
        {"id": "AwsSolutions-IAM4", "reason": "Using AWS-managed policies for Lambda roles for simplified permissions."},
        {"id": "AwsSolutions-IAM5", "reason": "Wildcard permissions are required for S3 bucket access in this scenario."}
    ]
)



app.synth()
