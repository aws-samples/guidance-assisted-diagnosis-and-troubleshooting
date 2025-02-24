import json
import uuid
from datetime import datetime
from datetime import timezone

import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    actionGroup = event.get('actionGroup')
    apiPath = event.get('apiPath')
    httpMethod = event.get('httpMethod')

    logger.info(f"Received event: {json.dumps(event)}")
    logger.info(f"Received body: {event.get('body')}")

    try:
        if apiPath == '/submitWorkOrder' and httpMethod == 'POST':
            return handle_submit_work_order(event)
        else:
            return error_response(404, "Not Found", event)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return error_response(500, f"Unexpected error: {str(e)}", event)


def handle_submit_work_order(event):
    parameters = event.get('parameters', [])
    try:
        equipment_id = ""
        for p in parameters:
            if p["name"]  == "equipment_id":
                equipment_id = p ["value"]

        # todo request description
        request_description = event["inputText"]
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request body: {str(e)}")
        return error_response(400, f"Invalid JSON in request body: {str(e)}", event)
    except KeyError as e:
        logger.error(f"Missing required field in request body: {str(e)}")
        return error_response(400, f"Missing required field in request body: {str(e)}", event)

    work_order_number = str(uuid.uuid4().int)[:5]
    submission_datetime = datetime.now(timezone.utc).isoformat()
    message = f"Work order {work_order_number} has been submitted for equipment {equipment_id} at {submission_datetime} with the following request: {request_description}"

    response_body = {
        "workOrderNumber": work_order_number,
        "equipmentId": equipment_id,
        "requestDescription": request_description,
        "submissionDatetime": submission_datetime,
        "message": message
    }

    logger.info(f"Work order created successfully: {json.dumps(response_body)}")
    return success_response(response_body, event)


def success_response(response, event):
    actionGroup = event.get('actionGroup')
    apiPath = event.get('apiPath')
    httpMethod = event.get('httpMethod')
    messageVersion = event.get('messageVersion')

    responseBody = {
        "application/json": {
            "body": response
        }
    }

    action_response = {
        'actionGroup': actionGroup,
        'apiPath': apiPath,
        'httpMethod': httpMethod,
        'httpStatusCode': 201,
        'responseBody': responseBody
    }

    return {'response': action_response, 'messageVersion': messageVersion}


def error_response(status_code, message, event):
    actionGroup = event.get('actionGroup')
    apiPath = event.get('apiPath')
    httpMethod = event.get('httpMethod')
    messageVersion = event.get('messageVersion')

    responseBody = {
        "application/json": {
            "body": message
        }
    }

    action_response = {
        'actionGroup': actionGroup,
        'apiPath': apiPath,
        'httpMethod': httpMethod,
        'httpStatusCode': status_code,
        'responseBody': responseBody
    }

    return {'response': action_response, 'messageVersion': messageVersion}
