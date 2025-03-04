from aws_cdk import (
    Stack,
    Aws,
    Duration,
    RemovalPolicy,
    aws_cognito as cognito,
    aws_iam as iam,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    CfnOutput
)
from constructs import Construct
from cdk_nag import NagSuppressions

from stacks.cognito_auth_role import CognitoAuthRole


class FrontendStack(Stack):
    def __init__(
            self, 
            scope: Construct,
            construct_id: str,
            x_origin_verify_secret,
            api_gateway,
            identity_pool,
            **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        prefix = "ADB"

        # Create the S3 bucket to store static assets for the frontend
        frontend_bucket = s3.Bucket(
            self,
            f"{prefix}FrontendBucket",
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True
        )

        CfnOutput(
            self,
            "FrontEndAssetsBucket",
            value=frontend_bucket.bucket_name
        )

        # Enforce SSL for S3 Bucket Policy
        frontend_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                actions=["s3:*"],
                resources=[frontend_bucket.bucket_arn, f"{frontend_bucket.bucket_arn}/*"],
                conditions={"Bool": {"aws:SecureTransport": "false"}},
                effect=iam.Effect.DENY,
                principals=[iam.AnyPrincipal()],
            )
        )


        # Create the Authenticated Role
        authenticated_role = CognitoAuthRole(
            self,
            "CognitoAuthRole",
            identity_pool=identity_pool,
            region=self.region,
            account=self.account
        ).get_role 

        authenticated_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "iotsitewise:*",
                ],
                effect=iam.Effect.ALLOW,
                resources=[
                    "*"
                ]
            )
        )

        authenticated_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:GetObject"
                ],
                effect= iam.Effect.ALLOW,
                resources= [
                    f"arn:aws:s3:::{frontend_bucket.bucket_name}/*"
                ],
            )
        )

        # Origin Access Identity for CloudFront to access the S3 bucket
        origin_access_identity = cloudfront.OriginAccessIdentity(self, f"{prefix}OAI")
        frontend_bucket.grant_read(origin_access_identity)

        # Create Origin for S3
        s3_origin = origins.S3Origin(
            frontend_bucket,
            origin_access_identity=origin_access_identity,
            origin_id="/web",
            origin_path="/web"
        )

        api_cache_policy = cloudfront.CachePolicy(
            self,
            "ApiCachePolicy",
            cache_policy_name="ApiCachePolicy",
            comment="Cache policy for API with Authorization header forwarding",
            default_ttl=Duration.seconds(0),  # Adjust TTL to enable caching but keep it short
            min_ttl=Duration.seconds(0),
            max_ttl=Duration.seconds(1),
            header_behavior=cloudfront.CacheHeaderBehavior.allow_list(
                "Authorization",
                "Referer",
                "Origin",
                "Content-Type",
                "x-forwarded-user",
                "Access-Control-Request-Headers",
                "Access-Control-Request-Method",
            ),
            query_string_behavior=cloudfront.CacheQueryStringBehavior.all(),
            enable_accept_encoding_brotli=True,
            enable_accept_encoding_gzip=True
        )

        # Create CloudFront Distribution
        distribution = cloudfront.Distribution(
            self,
            f"{prefix}FrontEndDistribution",
            default_behavior={
                "origin": s3_origin, 
                "viewer_protocol_policy": cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            },
            additional_behaviors={
                "/api/*": cloudfront.BehaviorOptions(
                    origin=origins.HttpOrigin(
                        domain_name=f"{api_gateway.rest_api_id}.execute-api.{Aws.REGION}.{Aws.URL_SUFFIX}",
                        custom_headers={
                            "X-Origin-Verify": x_origin_verify_secret.secret_value_from_json("headerValue").unsafe_unwrap(),
                        }
                    ),
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=api_cache_policy,
                )
            },
            minimum_protocol_version=cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
            default_root_object='index.html',
        )

        # Output the CloudFront distribution URL
        CfnOutput(
            self,
            "DistributionDomainName",
            value=f"https://{distribution.distribution_domain_name}"
        )

        # Apply stack-level Nag suppressions
        NagSuppressions.add_stack_suppressions(
            self,
            suppressions=[
                {"id": "AwsSolutions-S1", "reason": "Server access logs are not required for this bucket in this use case."},
                {"id": "AwsSolutions-S10", "reason": "SSL enforcement is handled in the bucket policy for secure access."},
                {"id": "AwsSolutions-COG2", "reason": "MFA is not required for this internal user pool."},
                {"id": "AwsSolutions-COG3", "reason": "AdvancedSecurityMode is not enforced for cost-saving purposes."},
                {"id": "AwsSolutions-IAM4", "reason": "Using AWS-managed policies for simplified permissions in this application."},
                {"id": "AwsSolutions-IAM5", "reason": "Wildcard permissions are required to support general IoT SiteWise access."},
                {"id": "AwsSolutions-CFR1", "reason": "Geo restrictions are not required for this application."},
                {"id": "AwsSolutions-CFR2", "reason": "WAF is not integrated due to low-risk profile of this app."},
                {"id": "AwsSolutions-CFR3", "reason": "Access logs are not needed for development/testing environment."},
                {"id": "AwsSolutions-CFR4", "reason": "SSL/TLS settings are compliant for intended use case."},
            ]
        )
