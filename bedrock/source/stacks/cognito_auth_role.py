from aws_cdk import (
    aws_iam as iam,
    aws_cognito as cognito,
    Stack
)
from constructs import Construct

class CognitoAuthRole(Construct):

    def __init__(self, scope: Construct, id: str, identity_pool: cognito.CfnIdentityPool, region: str, account: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # IAM role for authenticated users
        self.role = iam.Role(
            self,
            "CognitoAuthenticatedRole",
            assumed_by=iam.FederatedPrincipal(
                "cognito-identity.amazonaws.com",
                {
                    "StringEquals": {
                        "cognito-identity.amazonaws.com:aud": identity_pool.ref
                    },
                    "ForAnyValue:StringLike": {
                        "cognito-identity.amazonaws.com:amr": "authenticated"
                    }
                },
                "sts:AssumeRoleWithWebIdentity"
            )
        )

        # Attach a policy to allow specific Cognito identity actions
        self.role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "cognito-identity:GetId",
                    "cognito-identity:GetCredentialsForIdentity",
                    "cognito-identity:DescribeIdentity"
                ],
                resources=[
                    f"arn:aws:cognito-identity:{region}:{account}:identitypool/{identity_pool.ref}"
                ]
            )
        )

        # Attach the role to the Cognito Identity Pool
        cognito.CfnIdentityPoolRoleAttachment(
            self,
            "IdentityPoolRoleAttachment",
            identity_pool_id=identity_pool.ref,
            roles={"authenticated": self.role.role_arn}
        )
    
    @property
    def get_role(self):
        return self.role    
        
