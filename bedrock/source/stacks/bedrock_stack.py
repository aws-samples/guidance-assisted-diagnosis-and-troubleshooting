import os
import json
import os.path as path
import platform

from aws_cdk import (
    Duration,
    Aws,
    Stack,
    RemovalPolicy,
    CfnOutput,
    CfnResource,
    CustomResource,
    custom_resources as cr,
    aws_bedrock as bedrock,
    aws_secretsmanager as secretsmanager,
    aws_s3_deployment as s3deploy,
    aws_cognito as cognito,
    aws_lambda as lambda_,
    aws_s3 as s3,
    aws_opensearchserverless as opensearchserverless,
    aws_iam as iam,
)
from aws_cdk.aws_apigateway import (
    RestApi,
    EndpointType,
    Cors,
    MethodLoggingLevel,
    CfnMethod,
    MethodResponse,
    IntegrationResponse,
    CognitoUserPoolsAuthorizer,
    LambdaIntegration,
    AuthorizationType
)
from aws_cdk.aws_lambda_python_alpha import PythonLayerVersion
from constructs import Construct
from aws_cdk.aws_ecr_assets import Platform
from cdk_nag import NagSuppressions, NagPackSuppression

class BedrockStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.lambda_runtime = lambda_.Runtime.PYTHON_3_12

        ostype = platform.system().lower()

        if "darwin" in ostype:
            # macOS - use ARM64 as it aligns with Apple Silicon (M1/M2)
            self.lambda_architecture = lambda_.Architecture.ARM_64
        elif "linux" in ostype:
            # Linux - use ARM64 for efficiency on most AWS environments
            self.lambda_architecture = lambda_.Architecture.ARM_64
        elif "win32" in ostype or "cygwin" in ostype or "msys" in ostype:
            # Windows - default to AMD64 (x86_64) for compatibility
            self.lambda_architecture = lambda_.Architecture.X86_64
        else:
            # Default to ARM64 for environments where OSTYPE is not set or unknown
            self.lambda_architecture = lambda_.Architecture.ARM_64

        print(f"OSTYPE detected as: {ostype}.")

        prefix = "AssistedDiagnoses"

        agent_assets_bucket = self.create_data_source_bucket()
        self.upload_files_to_s3(agent_assets_bucket)

        agent_sitewise_executor_lambda = self.create_agent_sitewise_executor_lambda()
        agent_workorder_executor_lambda = self.create_agent_workorder_executor_lambda()

        agent_resource_role = self.create_agent_execution_role(agent_assets_bucket)

        opensearch_layer = self.create_lambda_layer("opensearch_layer")

        (
            cfn_collection,
            vector_field_name,
            vector_index_name,
            lambda_cr,
        ) = self.create_opensearch_index(agent_resource_role, opensearch_layer)

        knowledge_base, agent_resource_role_arn = self.create_knowledgebase(
            vector_field_name,
            vector_index_name,
            cfn_collection,
            agent_resource_role,
            lambda_cr,
        )

        cfn_data_source = self.create_agent_data_source(
            knowledge_base, agent_assets_bucket
        )

        agent = self.create_bedrock_agent(
            agent_sitewise_executor_lambda,
            agent_workorder_executor_lambda,
            agent_assets_bucket,
            agent_resource_role,
            knowledge_base,
        )

        boto3_layer = self.create_lambda_layer("boto3_layer")

        # Define the Powertools layer version
        power_tools_layer_version = "68"

        # Determine the appropriate Lambda layer ARN based on architecture
        power_tools_layer = lambda_.LayerVersion.from_layer_version_arn(
            self,
            "PowertoolsLayer",
            f"arn:{Aws.PARTITION}:lambda:{Aws.REGION}:017000801446:layer:AWSLambdaPowertoolsPythonV2{'-Arm64' if self.lambda_architecture == lambda_.Architecture.ARM_64 else ''}:{power_tools_layer_version}"
        )

        self.x_origin_verify_secret = secretsmanager.Secret(
            self,
            "X-Origin-Verify-Secret",
            removal_policy=RemovalPolicy.DESTROY,
            generate_secret_string=secretsmanager.SecretStringGenerator(
                exclude_punctuation=True,
                generate_string_key="headerValue",
                secret_string_template="{}",
            ),
        )

        invoke_lambda = self.create_bedrock_agent_invoke_lambda(
            agent, agent_assets_bucket, boto3_layer, 
            power_tools_layer, self.x_origin_verify_secret 
        )

        _ = self.create_update_lambda(
            knowledge_base,
            cfn_data_source,
            agent,
            agent_resource_role_arn,
            boto3_layer,
        )

         # Create the User Pool
        user_pool = cognito.UserPool(
            self, 
            f"{prefix}UserPool",
            user_pool_name=f"{prefix}UserPool",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            custom_attributes={
                "title": cognito.StringAttribute(min_len=0, max_len=50, mutable=True)
            },
            email=cognito.UserPoolEmail.with_cognito(),
            mfa=cognito.Mfa.OFF,
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True,
                temp_password_validity=Duration.days(7)
            ),
            deletion_protection=False,
            removal_policy=RemovalPolicy.DESTROY,
        )
        
        self.api_gateway = self.create_api_gateway(invoke_lambda, user_pool)

        # Create the User Pool Client
        user_pool_client = cognito.UserPoolClient(
            self,
            f"{prefix}AppClient",
            user_pool_client_name=f"{prefix}AppClient",
            user_pool=user_pool,
            access_token_validity=Duration.minutes(60),
            id_token_validity=Duration.minutes(60),
            auth_flows=cognito.AuthFlow(
                user_srp=True,
                user_password=True
            ),
            prevent_user_existence_errors=True,
        )

        # Create the Identity Pool
        self.identity_pool = cognito.CfnIdentityPool(
            self,
            f"{prefix}IdentityPool",
            identity_pool_name=f"{prefix}IdentityPool",
            allow_unauthenticated_identities=False,
            allow_classic_flow=False,
            cognito_identity_providers=[
                cognito.CfnIdentityPool.CognitoIdentityProviderProperty(
                    client_id=user_pool_client.user_pool_client_id,
                    provider_name=user_pool.user_pool_provider_name,
                    server_side_token_check=False
                )
            ],
        )

        CfnOutput(
            self,
            "IdentityPoolId",
            value=self.identity_pool.ref
        )

        CfnOutput(
            self, 
            "UserPoolClientId",
            value=user_pool_client.user_pool_client_id,
        )

        CfnOutput(
            self, 
            "UserPoolId",
            value=user_pool.user_pool_id,
        )


    def create_bedrock_agent(
        self,
        agent_sitewise_executor_lambda,
        agent_workorder_executor_lambda,
        agent_assets_bucket,
        agent_resource_role,
        cfn_knowledge_base,
    ):
        agent_resource_role_arn = agent_resource_role.role_arn
        s3_bucket_name = agent_assets_bucket.bucket_name
        sitwise_openapi_s3_object_key = "openapi_schema/openapi_sitewise.yaml"
        workorder_openapi_s3_object_key = "openapi_schema/openapi_workorder.yaml"

        cfn_agent = bedrock.CfnAgent(
            self,
            "ChatbotBedrockAgent",
            agent_name="assisted-diagnoses-agent",
            # the properties below are optional
            action_groups=[
                bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="SitewiseBedrockAgentActionGroup",
                    # the properties below are optional
                    action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=agent_sitewise_executor_lambda.function_arn
                    ),
                    ## action_group_state="actionGroupState",
                    api_schema=bedrock.CfnAgent.APISchemaProperty(
                        # payload="payload",
                        s3=bedrock.CfnAgent.S3IdentifierProperty(
                            s3_bucket_name=s3_bucket_name, s3_object_key=sitwise_openapi_s3_object_key
                        ),
                    ),
                    description="You are an asset information agent, assisting operators by retrieving asset details, property values, and historical or aggregated data about their assets in the factory.",
                    ## parent_action_group_signature="parentActionGroupSignature",
                    ## skip_resource_in_use_check_on_delete=False,
                ),
                bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="WorkorderBedrockAgentActionGroup",
                    # the properties below are optional
                    action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=agent_workorder_executor_lambda.function_arn
                    ),
                    ## action_group_state="actionGroupState",
                    api_schema=bedrock.CfnAgent.APISchemaProperty(
                        # payload="payload",
                        s3=bedrock.CfnAgent.S3IdentifierProperty(
                            s3_bucket_name=s3_bucket_name, s3_object_key=workorder_openapi_s3_object_key
                        ),
                    ),
                    description="You are an workorder agent that helps operators submit workorders.",
                    ## parent_action_group_signature="parentActionGroupSignature",
                    ## skip_resource_in_use_check_on_delete=False,
                ),
            ],
            agent_resource_role_arn=agent_resource_role_arn,
            description="You are agent that helps factory works get information about assets on their factory shopfloor from ioT Sitewise",
            foundation_model="anthropic.claude-3-haiku-20240307-v1:0",
            idle_session_ttl_in_seconds=3600,
            instruction="You are an asset information agent, assisting operators by retrieving asset details, property values, and historical or aggregated data about their assets in the factory.",
            knowledge_bases=[
                bedrock.CfnAgent.AgentKnowledgeBaseProperty(
                    description=cfn_knowledge_base.description,
                    knowledge_base_id=cfn_knowledge_base.attr_knowledge_base_id,
                )
            ],
        )

        return cfn_agent

    def create_data_source_bucket(self):
    
        agent_assets_bucket = s3.Bucket(
            self,
            "AgentAssetsSourceBaseBucket",
            bucket_name=f"{self.stack_name.lower()}-agent-assets-bucket-{Aws.ACCOUNT_ID}",
            versioned=True,
            auto_delete_objects=True,
            removal_policy=RemovalPolicy.DESTROY,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
        )
        
        CfnOutput(self, "AssetsBucket", value=agent_assets_bucket.bucket_name)

        return agent_assets_bucket

    def upload_files_to_s3(self, agent_assets_bucket):
        local_files_dir = os.path.join(os.getcwd(), "files")

        # Uploading files to S3 bucket
        s3deploy.BucketDeployment(
            self,
            "KnowledgeBaseDocumentDeployment",
            sources=[s3deploy.Source.asset(local_files_dir)],
            destination_bucket=agent_assets_bucket,
            retain_on_delete=False,
        )

        return
    

    def create_agent_sitewise_executor_lambda(
        self,
    ):

        # Create IAM role for Lambda function
        lambda_role = iam.Role(
            self,
            "LambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
                # Add a managed policy for Amazon Sitewise AmazonBedrockFullAccess
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AWSIoTSiteWiseFullAccess"
                ),
                # Add a managed policy for AmazonBedrockFullAccess
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonBedrockFullAccess"
                ),
            ],
        )
        lambda_function = lambda_.Function(
            self,
            "AgentActionLambdaFunction",
            function_name=f"{self.stack_name.lower()}-agent-action-sitewise-lambda-{Aws.ACCOUNT_ID}-{Aws.REGION}",
            description="Lambda code for GenAI Chatbot",
            runtime=self.lambda_runtime,
            timeout=Duration.seconds(900),
            code=lambda_.Code.from_asset("lambdas/sitewise-lambda"),
            handler="index.lambda_handler",
            environment={},
            role=lambda_role,
        )

        lambda_function.add_permission(
            "BedrockLambdaInvokePermission",
            principal=iam.ServicePrincipal("bedrock.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_account=Aws.ACCOUNT_ID,
            source_arn=f"arn:aws:bedrock:{Aws.REGION}:{Aws.ACCOUNT_ID}:agent/*",
        )

        return lambda_function
    
    
    
    def create_agent_workorder_executor_lambda(
        self,
    ):

        # Create IAM role for Lambda function
        lambda_role = iam.Role(
            self,
            "WorkorderLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
                # Add a managed policy for AmazonBedrockFullAccess
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonBedrockFullAccess"
                ),
            ],
        )
        lambda_function = lambda_.Function(
            self,
            "AgentWorkoederActionLambdaFunction",
            function_name=f"{self.stack_name.lower()}-action-workorder-lambda-{Aws.ACCOUNT_ID}-{Aws.REGION}",
            description="Lambda code for GenAI Chatbot",
            runtime=self.lambda_runtime,
            timeout=Duration.seconds(900),
            code=lambda_.Code.from_asset("lambdas/workorder-lambda"),
            handler="index.lambda_handler",
            environment={},
            role=lambda_role,
        )

        lambda_function.add_permission(
            "BedrockWorkorderLambdaInvokePermission",
            principal=iam.ServicePrincipal("bedrock.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_account=Aws.ACCOUNT_ID,
            source_arn=f"arn:aws:bedrock:{Aws.REGION}:{Aws.ACCOUNT_ID}:agent/*",
        )

        return lambda_function
    
    
    
    def create_agent_execution_role(self, agent_assets_bucket):
        agent_resource_role = iam.Role(
            self,
            "ChatBotBedrockAgentRole",
            # must be AmazonBedrockExecutionRoleForAgents_string
            role_name="AmazonBedrockExecutionRoleForAgents_chatbot",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
        )
        policy_statements = [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["bedrock:InvokeModel"],
                resources=[f"arn:aws:bedrock:{Aws.REGION}::foundation-model/*"],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject", "s3:ListBucket"],
                resources=[
                    f"arn:aws:s3:::{agent_assets_bucket.bucket_name}",
                    f"arn:aws:s3:::{agent_assets_bucket.bucket_name}/*",
                ],
                conditions={
                    "StringEquals": {
                        "aws:ResourceAccount": f"{Aws.ACCOUNT_ID}",
                    },
                },
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["bedrock:Retrieve", "bedrock:RetrieveAndGenerate"],
                resources=[
                    f"arn:aws:bedrock:{Aws.REGION}:{Aws.ACCOUNT_ID}:knowledge-base/*"
                ],
                conditions={
                    "StringEquals": {
                        "aws:ResourceAccount": f"{Aws.ACCOUNT_ID}",
                    },
                },
            ),
        ]

        for statement in policy_statements:
            agent_resource_role.add_to_policy(statement)

        return agent_resource_role
    

    def create_lambda_layer(self, layer_name):
        """
        create a Lambda layer with necessary dependencies.
        """
        # Create the Lambda layer
        layer = PythonLayerVersion(
            self,
            layer_name,
            entry=path.join(os.getcwd(), "layers", layer_name),
            compatible_runtimes=[self.lambda_runtime],
            compatible_architectures=[self.lambda_architecture],
            description="A layer new version of boto3",
            layer_version_name=layer_name,
        )

        return layer


    
    def create_opensearch_index(self, agent_resource_role, opensearch_layer):

        vector_index_name = "bedrock-knowledgebase-index"
        vector_field_name = "bedrock-knowledge-base-default-vector"

        agent_resource_role_arn = agent_resource_role.role_arn

        create_index_lambda_execution_role = iam.Role(
            self,
            "CreateIndexExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Role for OpenSearch access",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )

        cfn_collection = opensearchserverless.CfnCollection(
            self,
            "ChatBotAgentCollection",
            name=f"chatbot-oscollect-{Aws.ACCOUNT_ID}",
            description="ChatBot Agent Collection",
            type="VECTORSEARCH",
        )

        cfn_collection_name = cfn_collection.name

        opensearch_policy_statement = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["aoss:APIAccessAll"],
            resources=[
                f"arn:aws:aoss:{Aws.REGION}:{Aws.ACCOUNT_ID}:collection/{cfn_collection.attr_id}"
            ],
        )

        # Attach the custom policy to the role
        create_index_lambda_execution_role.add_to_policy(opensearch_policy_statement)

        # get the role arn
        create_index_lambda_execution_role_arn = (
            create_index_lambda_execution_role.role_arn
        )

        agent_resource_role.add_to_policy(opensearch_policy_statement)

        policy_json = {
            "Rules": [
                {
                    "ResourceType": "collection",
                    "Resource": [f"collection/{cfn_collection_name}"],
                }
            ],
            "AWSOwnedKey": True,
        }

        json_dump = json.dumps(policy_json)

        encryption_policy = CfnResource(
            self,
            "EncryptionPolicy",
            type="AWS::OpenSearchServerless::SecurityPolicy",
            properties={
                "Name": "chatbot-index-encryption-policy",
                "Type": "encryption",
                "Description": "Encryption policy for Bedrock collection.",
                "Policy": json_dump,
            },
        )

        policy_json = [
            {
                "Rules": [
                    {
                        "ResourceType": "collection",
                        "Resource": [f"collection/{cfn_collection_name}"],
                    },
                    {
                        "ResourceType": "dashboard",
                        "Resource": [f"collection/{cfn_collection_name}"],
                    },
                ],
                "AllowFromPublic": True,
            }
        ]
        json_dump = json.dumps(policy_json)

        network_policy = CfnResource(
            self,
            "NetworkPolicy",
            type="AWS::OpenSearchServerless::SecurityPolicy",
            properties={
                "Name": "chatbot-index-network-policy",
                "Type": "network",
                "Description": "Network policy for Bedrock collection",
                "Policy": json_dump,
            },
        )

        policy_json = [
            {
                "Description": "Access for cfn user",
                "Rules": [
                    {
                        "ResourceType": "index",
                        "Resource": ["index/*/*"],
                        "Permission": ["aoss:*"],
                    },
                    {
                        "ResourceType": "collection",
                        "Resource": [f"collection/{cfn_collection_name}"],
                        "Permission": ["aoss:*"],
                    },
                ],
                "Principal": [
                    agent_resource_role_arn,
                    create_index_lambda_execution_role_arn,
                ],
            }
        ]

        json_dump = json.dumps(policy_json)

        data_policy = CfnResource(
            self,
            "DataPolicy",
            type="AWS::OpenSearchServerless::AccessPolicy",
            properties={
                "Name": "chatbot-index-data-policy",
                "Type": "data",
                "Description": "Data policy for Bedrock collection.",
                "Policy": json_dump,
            },
        )

        cfn_collection.add_dependency(network_policy)
        cfn_collection.add_dependency(encryption_policy)
        cfn_collection.add_dependency(data_policy)

        self.create_index_lambda = lambda_.Function(
            self,
            "CreateIndexLambda",
            function_name=f"{Aws.STACK_NAME}-create-index-lambda-{Aws.ACCOUNT_ID}-{Aws.REGION}",
            runtime=self.lambda_runtime,
            handler="index.lambda_handler",
            code=lambda_.Code.from_asset(
                path.join(
                    os.getcwd(), "lambdas", "create-index-lambda"
                )
            ),
            # architecture=lambda_.Architecture.ARM_64,
            layers=[opensearch_layer],
            environment={
                "REGION_NAME": Aws.REGION,
                "COLLECTION_HOST": cfn_collection.attr_collection_endpoint,
                "VECTOR_INDEX_NAME": vector_index_name,
                "VECTOR_FIELD_NAME": vector_field_name,
            },
            role=create_index_lambda_execution_role,
            timeout=Duration.minutes(15),
            tracing=lambda_.Tracing.ACTIVE,
        )

        lambda_provider = cr.Provider(
            self,
            "LambdaCreateIndexCustomProvider",
            on_event_handler=self.create_index_lambda,
        )

        lambda_cr = CustomResource(
            self,
            "LambdaCreateIndexCustomResource",
            service_token=lambda_provider.service_token,
        )

        return (
            cfn_collection,
            vector_field_name,
            vector_index_name,
            lambda_cr,
        )
    
    def create_knowledgebase(
        self,
        vector_field_name,
        vector_index_name,
        cfn_collection,
        agent_resource_role,
        lambda_cr,
    ):

        kb_name = "BedrockKnowledgeBase"
        text_field = "AMAZON_BEDROCK_TEXT_CHUNK"
        metadata_field = "AMAZON_BEDROCK_METADATA"

        agent_resource_role_arn = agent_resource_role.role_arn

        embed_moodel = bedrock.FoundationModel.from_foundation_model_id(
            self,
            "embedding_model",
            bedrock.FoundationModelIdentifier.AMAZON_TITAN_EMBED_G1_TEXT_02,
        )
        
        cfn_knowledge_base = bedrock.CfnKnowledgeBase(
            self,
            "BedrockOpenSearchKnowledgeBase",
            knowledge_base_configuration=bedrock.CfnKnowledgeBase.KnowledgeBaseConfigurationProperty(
                type="VECTOR",
                vector_knowledge_base_configuration=bedrock.CfnKnowledgeBase.VectorKnowledgeBaseConfigurationProperty(
                    embedding_model_arn=embed_moodel.model_arn
                ),
            ),
            name=kb_name,
            role_arn=agent_resource_role_arn,
            storage_configuration=bedrock.CfnKnowledgeBase.StorageConfigurationProperty(
                type="OPENSEARCH_SERVERLESS",
                # the properties below are optional
                opensearch_serverless_configuration=bedrock.CfnKnowledgeBase.OpenSearchServerlessConfigurationProperty(
                    collection_arn=cfn_collection.attr_arn,
                    field_mapping=bedrock.CfnKnowledgeBase.OpenSearchServerlessFieldMappingProperty(
                        metadata_field=metadata_field,
                        text_field=text_field,
                        vector_field=vector_field_name,
                    ),
                    vector_index_name=vector_index_name,
                ),
            ),
            description="Use this for returning detailed descriptive answers and step-by-step instructions directly from Standard Operating Procedures (SOPs) and Recipes to ensure consistency, accuracy, and compliance.",
        )

        for child in lambda_cr.node.children:
            if isinstance(child, CustomResource):
                break

        cfn_knowledge_base.add_dependency(child)
        cfn_knowledge_base.add_dependency(cfn_collection)

        
        return cfn_knowledge_base, agent_resource_role_arn


    
    def create_agent_data_source(self, knowledge_base, agent_assets_bucket):
        data_source_bucket_arn = f"arn:aws:s3:::{agent_assets_bucket.bucket_name}"

        cfn_data_source = bedrock.CfnDataSource(
            self,
            "BedrockKnowledgeBaseSource",
            data_source_configuration=bedrock.CfnDataSource.DataSourceConfigurationProperty(
                s3_configuration=bedrock.CfnDataSource.S3DataSourceConfigurationProperty(
                    bucket_arn=data_source_bucket_arn,
                    # the properties below are optional
                    bucket_owner_account_id=Aws.ACCOUNT_ID,
                    inclusion_prefixes=[f"data/"],
                ),
                type="S3",
            ),
            knowledge_base_id=knowledge_base.attr_knowledge_base_id,
            name="BedrockKnowledgeBaseSource",
            # the properties below are optional
            data_deletion_policy="RETAIN",
            description="description",
        )

        return cfn_data_source



    def create_bedrock_agent_invoke_lambda(
        self, agent, agent_assets_bucket, boto3_layer,
        power_tools_layer, x_origin_verify_secret
    ):

        invoke_lambda_role = iam.Role(
            self,
            "InvokeLambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Role for Lambda to access Bedrock agents and S3",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )

        # Bedrock agent permissions
        invoke_lambda_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:ListAgents",
                    "bedrock:ListAgentAliases",
                    "bedrock:InvokeAgent",
                ],
                resources=[
                    f"arn:aws:bedrock:{Aws.REGION}:{Aws.ACCOUNT_ID}:agent/{agent.attr_agent_id}",
                    f"arn:aws:bedrock:{Aws.REGION}:{Aws.ACCOUNT_ID}:agent-alias/{agent.attr_agent_id}/*",
                ],
            )
        )

        # S3 permissions
        invoke_lambda_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject", "s3:ListBucket"],
                resources=[
                    f"arn:aws:s3:::{agent_assets_bucket.bucket_name}",
                    f"arn:aws:s3:::{agent_assets_bucket.bucket_name}/*",
                ],
            )
        )

        self.invoke_lambda = lambda_.Function(
            self,
            "StreamlitLambdaInvoke",
            function_name=f"{Aws.STACK_NAME}-StreamlitLambdaInvoke-{Aws.ACCOUNT_ID}-{Aws.REGION}",
            runtime=self.lambda_runtime,
            handler="index.handler",
            code=lambda_.Code.from_asset(
                path.join(os.getcwd(), "lambdas", "invoke-lambda")
            ),
            layers=[boto3_layer, power_tools_layer],
            environment={
                "AGENT_ID": agent.attr_agent_id, 
                "REGION_NAME": Aws.REGION,
                "X_ORIGIN_VERIFY_SECRET_ARN": x_origin_verify_secret.secret_arn,
            },
            role=invoke_lambda_role,
            timeout=Duration.minutes(15),
            tracing=lambda_.Tracing.ACTIVE,
        )

        x_origin_verify_secret.grant_read(self.invoke_lambda)

        CfnOutput(
            self,
            "StreamlitInvokeLambdaFunction",
            value=self.invoke_lambda.function_name,
        )

        return self.invoke_lambda

    def create_update_lambda(
        self,
        knowledge_base,
        cfn_data_source,
        bedrock_agent,
        agent_resource_role_arn,
        boto3_layer,
    ):

        # Create IAM role for the update lambda
        lambda_role = iam.Role(
            self,
            "LambdaRole_update_resources",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
        )


        # Define the policy statement
        bedrock_policy_statement = iam.PolicyStatement(
            actions=[
                "bedrock:StartIngestionJob",
                "bedrock:UpdateAgentKnowledgeBase",
                "bedrock:GetAgentAlias",
                "bedrock:UpdateKnowledgeBase",
                "bedrock:UpdateAgent",
                "bedrock:GetIngestionJob",
                "bedrock:CreateAgentAlias",
                "bedrock:UpdateAgentAlias",
                "bedrock:GetAgent",
                "bedrock:PrepareAgent",
                "bedrock:DeleteAgentAlias",
                "bedrock:DeleteAgent",
                "bedrock:ListAgentAliases",
            ],
            resources=[
                f"arn:aws:bedrock:{Aws.REGION}:{Aws.ACCOUNT_ID}:agent/*",
                f"arn:aws:bedrock:{Aws.REGION}:{Aws.ACCOUNT_ID}:agent-alias/*",
                f"arn:aws:bedrock:{Aws.REGION}:{Aws.ACCOUNT_ID}:knowledge-base/*",
            ],
            effect=iam.Effect.ALLOW,
        )

        # Create the policy
        update_agent_kb_policy = iam.Policy(
            self,
            "BedrockAgent_KB_Update_Policy",
            policy_name="allow_update_bedrock_agent_kb_policy",
            statements=[bedrock_policy_statement],
        )

        lambda_role.attach_inline_policy(update_agent_kb_policy)

        # create lambda function to trigger crawler, create bedrock agent alias, knowledgebase data sync
        lambda_function_update = lambda_.Function(
            self,
            "LambdaFunction_update_resources",
            function_name=f"{Aws.STACK_NAME}-update-lambda-{Aws.ACCOUNT_ID}-{Aws.REGION}",
            description="Lambda code to create bedrock agent alias, knowledgebase data sync",
            architecture=self.lambda_architecture,
            handler="lambda_handler.lambda_handler",
            runtime=self.lambda_runtime,
            code=lambda_.Code.from_asset(
                path.join(os.getcwd(), "lambdas", "update-lambda")
            ),
            environment={
                "KNOWLEDGEBASE_ID": knowledge_base.attr_knowledge_base_id,
                "KNOWLEDGEBASE_DATASOURCE_ID": cfn_data_source.attr_data_source_id,
                "BEDROCK_AGENT_ID": bedrock_agent.attr_agent_id,
                "BEDROCK_AGENT_NAME": "assisted-diagnoses-agent",
                "BEDROCK_AGENT_ALIAS": "assisted-diagnoses-agent-dev",
                "BEDROCK_AGENT_RESOURCE_ROLE_ARN": agent_resource_role_arn,
                "LOG_LEVEL": "info",
            },
            role=lambda_role,
            timeout=Duration.minutes(15),
            memory_size=1024,
            layers=[boto3_layer],
        )

        lambda_provider = cr.Provider(
            self,
            "LambdaUpdateResourcesCustomProvider",
            on_event_handler=lambda_function_update,
        )

        _ = CustomResource(
            self,
            "LambdaUpdateResourcesCustomResource",
            service_token=lambda_provider.service_token,
        )

        return lambda_function_update
    

    def create_api_gateway(self, invoke_lambda, user_pool):
    
        rest_api = RestApi(
            self,
            "AssistedDiagnosesRestApi",
            endpoint_types=[EndpointType.REGIONAL],
            cloud_watch_role=True,
            default_cors_preflight_options={
                "allow_origins": Cors.ALL_ORIGINS,
                "allow_methods": Cors.ALL_METHODS,
                "allow_headers": [
                    "Content-Type",
                    "Authorization",
                    "X-Amz-Date",
                    "X-Amz-Security-Token",
                ],
                "max_age": Duration.minutes(15),
            },
            deploy=True,
            deploy_options={
                "stage_name": "api",
                "logging_level": MethodLoggingLevel.INFO,
                "tracing_enabled": True,
                "metrics_enabled": True,
                "throttling_rate_limit": 2500,
            },
        )

        cognito_authorizer = CognitoUserPoolsAuthorizer(self, "CognitoAuthorizer",
            cognito_user_pools=[user_pool]
        )

        v1_resource = rest_api.root.add_resource("v1",                                       )
        v1_proxy_resource = v1_resource.add_resource("{proxy+}")

        api_lambda_integration = LambdaIntegration(
            invoke_lambda,
            proxy=True,
            integration_responses=[
                IntegrationResponse(
                    status_code="200",
                    response_parameters={
                        'method.response.header.Access-Control-Allow-Origin': "'*'"
                    }
                )
            ]
        )

        v1_proxy_resource.add_method(
            "ANY",
            api_lambda_integration,
            method_responses=[
                MethodResponse(
                    status_code="200",
                    response_parameters={
                        'method.response.header.Access-Control-Allow-Origin': True
                    }
                )
            ],
            authorizer=cognito_authorizer,
            authorization_type=AuthorizationType.COGNITO
        )

        invoke_lambda.add_permission(
            "ApiGatewayInvokePermission",
            principal=iam.ServicePrincipal("apigateway.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=f"arn:aws:execute-api:{Aws.REGION}:{Aws.ACCOUNT_ID}:{rest_api.rest_api_id}/*"
        )


        NagSuppressions.add_resource_suppressions(
            rest_api,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-APIG2",
                    reason="Request validation is managed by specific application logic."
                ),
                NagPackSuppression(
                    id="AwsSolutions-APIG1",
                    reason="Access logging is disabled intentionally for simplicity in a development environment."
                ),
                NagPackSuppression(
                    id="AwsSolutions-APIG3",
                    reason="WAFv2 web ACL is not required for this API."
                ),
                NagPackSuppression(
                    id="AwsSolutions-APIG4",
                    reason="OPTIONS methods do not require authorization."
                ),
                NagPackSuppression(
                    id="AwsSolutions-COG4",
                    reason="OPTIONS methods do not require a Cognito authorizer."
                ),
            ],
            apply_to_children=True
        )
        # Return the created API Gateway
        return rest_api
