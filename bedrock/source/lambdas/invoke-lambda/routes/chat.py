import os
import uuid
import boto3
from datetime import datetime
from pydantic import BaseModel
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler.api_gateway import Router
import boto3
import json
import logging
from collections import OrderedDict
import re

tracer = Tracer()
router = Router()
logger = Logger()




AGENT_ID = os.environ["AGENT_ID"]
REGION_NAME = os.environ["REGION_NAME"]

logger.info(f"Agent id: {AGENT_ID}")

agent_client = boto3.client("bedrock-agent", region_name=REGION_NAME)
agent_runtime_client = boto3.client(
    "bedrock-agent-runtime", region_name=REGION_NAME)
s3_resource = boto3.resource("s3", region_name=REGION_NAME)


def get_highest_agent_version_alias_id(response):
    """
    Find newest agent alias id.

    Args:
        response (dict): Response from list_agent_aliases().

    Returns:
        str: Agent alias ID of the newest agent version.
    """
    # Initialize highest version info
    highest_version = None
    highest_version_alias_id = None

    # Iterate through the agentAliasSummaries
    for alias_summary in response.get("agentAliasSummaries", []):
        # Assuming each alias has one routingConfiguration
        if alias_summary["routingConfiguration"]:
            agent_version = alias_summary["routingConfiguration"][0]["agentVersion"]
            # Check if the version is numeric and higher than the current highest
            if agent_version.isdigit() and (
                highest_version is None or int(agent_version) > highest_version
            ):
                highest_version = int(agent_version)
                highest_version_alias_id = alias_summary["agentAliasId"]

    # Return the highest version alias ID or None if not found
    return highest_version_alias_id


def invoke_agent(user_input, session_id):
    """
    Get response from Agent
    """
    response = agent_client.list_agent_aliases(agentId=AGENT_ID)

    logger.info(f"list_agent_aliases: {response}")
    agent_alias_id = get_highest_agent_version_alias_id(response)
    if not agent_alias_id:
        return "No agent published alias found - cannot invoke agent"
    streaming_response = agent_runtime_client.invoke_agent(
        agentId=AGENT_ID,
        agentAliasId=agent_alias_id,
        sessionId=session_id,
        enableTrace=True,
        inputText=user_input,
    )

    return streaming_response


def get_agent_response(response):
    logger.info(f"Getting agent response... {response}")
    if "completion" not in response:
        return f"No completion found in response: {response}"
    trace_list = []
    for event in response["completion"]:
        logger.info(f"Event keys: {event.keys()}")
        if "trace" in event:
            logger.info(event["trace"])
            trace_list.append(event["trace"])

        # Extract the traces
        if "chunk" in event:
            # Extract the bytes from the chunk
            chunk_bytes = event["chunk"]["bytes"]

            # Convert bytes to string, assuming UTF-8 encoding
            chunk_text = chunk_bytes.decode("utf-8")

            # Print the response text
            print("Response from the agent:", chunk_text)
    else:
        try:
            source_file_list = extract_source_list_from_kb(trace_list)
        except Exception as e:
            logger.info(f"Error extracting source list from KB: {e}")
            source_file_list = ""
    return chunk_text, source_file_list


def extract_source_list_from_kb(trace_list):
    """
    Extract the knowledge base lookup output from the trace list and return the S3 bucket paths.
    """
    
    for trace in trace_list:
        if  'orchestrationTrace' in trace['trace'].keys() and 'observation' in trace['trace']['orchestrationTrace'].keys():
            if 'knowledgeBaseLookupOutput' in trace['trace']['orchestrationTrace']['observation']:
                ref_list = trace['trace']['orchestrationTrace']['observation']['knowledgeBaseLookupOutput']['retrievedReferences']
    logger.info(f"ref_list: {ref_list}")
    ref_s3_list = []
    for rl in ref_list:
        ref_s3_list.append(rl['location']['s3Location']['uri'])
    
    return ref_s3_list


def source_link(input_source_list):
    """
    Formats the source list into a visually enhanced markdown string with clickable links and S3 icons.
    """
    source_dict_list = []
    for i, input_source in enumerate(input_source_list):
        string = input_source.split("//")[1]
        bucket = string.partition("/")[0]
        obj = string.partition("/")[2]
        file = s3_resource.Object(bucket, obj)
        body = file.get()["Body"].read()

        try:
            # Try parsing as JSON for richer metadata
            res = json.loads(body.decode('utf-8'))  # Ensure UTF-8 decoding
            source_link_url = res.get("Url", "")
            source_title = res.get("Topic", f"Document {i+1}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            # Fallback for non-JSON documents (like docx, PDFs)
            source_link_url = f"s3://{bucket}/{obj}"
            source_title = f"{os.path.basename(obj)}"

        source_dict = (source_title, source_link_url)
        source_dict_list.append(source_dict)

    # Get unique sources
    unique_sources = list(OrderedDict.fromkeys(source_dict_list))

    # Build the markdown-formatted string
    refs_str = "### **Relevant Documents:**\n\n"
    for i, (title, link) in enumerate(unique_sources, start=1):
        icon = "📁" if link.startswith("s3://") else "📄"  # Choose an icon based on content type
        refs_str += f"{i}. {icon} **[{title}]({link})**\n"

    return refs_str


   
@router.post("/chat")
@tracer.capture_method
def chat():
    data: dict = router.current_event.json_body

    logger.info(data)

    streaming_response = invoke_agent(data["query"], data["session_id"])
    response, source_file_list = get_agent_response(streaming_response)
    if isinstance(source_file_list, list):
        reference_str = source_link(source_file_list)
    else:
        reference_str = source_file_list

    response_body = {"answer": response, "source": reference_str}


    return {"ok": True, "response":response_body}