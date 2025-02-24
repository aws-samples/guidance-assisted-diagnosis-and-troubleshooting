import json
import boto3
import re
from datetime import datetime, timedelta, timezone
from botocore.exceptions import ClientError

sitewise = boto3.client('iotsitewise')

def lambda_handler(event, context):
    agent = event['agent']
    actionGroup = event['actionGroup']
    apiPath = event['apiPath']
    httpMethod =  event['httpMethod']
    parameters = event.get('parameters', [])
    requestBody = event.get('requestBody', {})

    try:
        if apiPath == '/assets' and httpMethod == 'GET':
            return list_all_assets(sitewise, event)
        elif apiPath == '/asset' and httpMethod == 'GET':
            asset_id = parameters[0].get('value')
            if not asset_id:
                return error_response(400, "Asset ID is required", event)
            return get_asset_overview(sitewise, asset_id, event)
        elif apiPath == '/property' and httpMethod == 'GET':
            asset_id = ""
            property_id = ""
            for p in parameters:
                if p["name"]  == "asset_id":
                    asset_id = p ["value"]
                elif p["name"] == "property_id":
                    property_id = p ["value"]
            if not asset_id or not property_id:
                return error_response(400, "Asset ID and Property ID are required", event)
            return get_property_value(sitewise, asset_id, property_id, parameters, event)
        else:
            return error_response(404, "Not Found", event)
    except ClientError as e:
        return error_response(500, f"AWS Error: {str(e)}", event)
    except Exception as e:
        return error_response(500, f"Unexpected error: {str(e)}", event)


def list_all_assets(sitewise, event):
    """List all assets across all models."""
    all_assets = []
    paginator = sitewise.get_paginator('list_asset_models')
    for page in paginator.paginate():
        for model in page['assetModelSummaries']:
            asset_paginator = sitewise.get_paginator('list_assets')
            for asset_page in asset_paginator.paginate(assetModelId=model['id']):
                all_assets.extend([
                    {
                        "assetName": asset['name'],
                        "assetId": asset['id'],
                        "modelName": model['name']
                    }
                    for asset in asset_page['assetSummaries']
                ])

    return success_response({"assets": all_assets}, event)

def get_asset_overview(sitewise, asset_id, event):
    """Get a comprehensive overview of an asset, including current property values."""
    asset = sitewise.describe_asset(assetId=asset_id)
    properties = get_asset_properties_with_values(sitewise, asset_id)

    overview = {
        "assetName": asset['assetName'],
        "assetId": asset['assetId'],
        "assetArn": asset['assetArn'],
        "assetModelId": asset['assetModelId'],
        "externalId": asset.get('assetExternalId', 'N/A'),
        "description": asset.get('assetDescription', 'No description available'),
        "creationDate": asset['assetCreationDate'].isoformat(),
        "lastUpdateDate": asset['assetLastUpdateDate'].isoformat(),
        "status": asset['assetStatus']['state'],
        "properties": properties
    }

    if asset.get('assetHierarchies'):
        overview["hierarchies"] = [
            {"id": hierarchy['id'], "name": hierarchy['name']}
            for hierarchy in asset['assetHierarchies']
        ]

    if asset.get('assetCompositeModels'):
        overview["compositeModels"] = [
            {"name": model['name'], "type": model['type']}
            for model in asset['assetCompositeModels']
        ]

    return success_response(overview, event)

def get_asset_properties_with_values(sitewise, asset_id):
    """Get properties of an asset with their current values."""
    response = sitewise.describe_asset(assetId=asset_id)
    properties = []
    for prop in response['assetProperties']:
        try:
            current_value = get_current_property_value(sitewise, asset_id, prop['id'])
            properties.append({
                "name": prop['name'],
                "id": prop['id'],
                "dataType": prop['dataType'],
                "unit": prop.get('unit', 'N/A'),
                "alias": prop.get('alias', 'N/A'),
                "currentValue": current_value
            })
        except Exception as e:
            properties.append({
                "name": prop['name'],
                "id": prop['id'],
                "dataType": prop['dataType'],
                "unit": prop.get('unit', 'N/A'),
                "alias": prop.get('alias', 'N/A'),
                "currentValue": f"Error retrieving value - {str(e)}"
            })
    return properties

def get_current_property_value(sitewise, asset_id, property_id):
    """Get the current value of a property."""
    try:
        response = sitewise.get_asset_property_value(assetId=asset_id, propertyId=property_id)
        value = response['propertyValue']['value']
        return next(iter(value.values()))
    except Exception as e:
        return f"Error: {str(e)}"

def get_property_value(sitewise, asset_id, property_id, query_parameters, event):
    """Get property value (current, historical, or aggregated)."""
    value_type = query_parameters.get('type', 'current')

    asset = sitewise.describe_asset(assetId=asset_id)
    property_info = next((prop for prop in asset['assetProperties'] if prop['id'] == property_id), None)
    if not property_info:
        return error_response(404, f"Property not found for asset {asset_id}")

    if value_type == 'current':
        resp = get_current_value(sitewise, asset, property_info)
        return success_response(resp, event)
    elif value_type == 'historical':
        resp = get_historical_value(sitewise, asset, property_info, query_parameters)
        return success_response(resp, event)
    elif value_type == 'aggregated':
        resp = get_aggregated_value(sitewise, asset, property_info, query_parameters)
        return success_response(resp, event)
    else:
        return error_response(400, f"Invalid value type: {value_type}")

def get_current_value(sitewise, asset, property_info):
    """Get current value of a property."""
    response = sitewise.get_asset_property_value(assetId=asset['assetId'], propertyId=property_info['id'])
    value = response['propertyValue']['value']
    timestamp = response['propertyValue']['timestamp']['timeInSeconds']

    # Extract the value based on the property type
    if property_info['dataType'] in ['INTEGER', 'DOUBLE']:
        current_value = next(iter(value.values()))
    elif property_info['dataType'] == 'BOOLEAN':
        current_value = bool(next(iter(value.values())))
    elif property_info['dataType'] == 'STRING':
        current_value = next(iter(value.values()))
    else:
        current_value = str(next(iter(value.values())))

    return {
        "asset": asset['assetName'],
        "property": property_info['name'],
        "dataType": property_info['dataType'],
        "currentValue": current_value,
        "timestamp": format_timestamp(timestamp)
    }

def get_historical_value(sitewise, asset, property_info, query_parameters):
    """Get historical values of a property."""
    start_time = parse_time(query_parameters.get('start_time', '-1h'))
    end_time = parse_time(query_parameters.get('end_time', 'now'))

    response = sitewise.get_asset_property_value_history(
        assetId=asset['assetId'],
        propertyId=property_info['id'],
        startDate=int(start_time.timestamp()),
        endDate=int(end_time.timestamp())
    )

    values = []
    for v in response.get('assetPropertyValueHistory', []):
        if property_info['dataType'] in ['INTEGER', 'DOUBLE']:
            value = next(iter(v['value'].values()))
        elif property_info['dataType'] == 'BOOLEAN':
            value = bool(next(iter(v['value'].values())))
        elif property_info['dataType'] == 'STRING':
            value = next(iter(v['value'].values()))
        else:
            value = str(next(iter(v['value'].values())))

        values.append({
            "value": value,
            "timestamp": format_timestamp(v['timestamp']['timeInSeconds']),
            "quality": v['quality']
        })

    return {
        "asset": asset['assetName'],
        "property": property_info['name'],
        "dataType": property_info['dataType'],
        "startTime": start_time.isoformat(),
        "endTime": end_time.isoformat(),
        "historicalData": values
    }

def get_aggregated_value(sitewise, asset, property_info, query_parameters):
    """Get aggregated values of a property."""
    if property_info['dataType'] not in ['INTEGER', 'DOUBLE']:
        return error_response(400, f"Aggregation is not supported for {property_info['dataType']} data type")

    start_time = parse_time(query_parameters.get('start_time', '-1h'))
    end_time = parse_time(query_parameters.get('end_time', 'now'))
    resolution = query_parameters.get('resolution', '1h')
    aggregate_types = query_parameters.get('aggregate_types', 'AVERAGE').split(',')

    response = sitewise.get_asset_property_aggregates(
        assetId=asset['assetId'],
        propertyId=property_info['id'],
        aggregateTypes=aggregate_types,
        resolution=resolution,
        qualities=['GOOD'],
        startDate=int(start_time.timestamp()),
        endDate=int(end_time.timestamp()),
        timeOrdering='ASCENDING'
    )

    aggregates = []
    for a in response['aggregatedValues']:
        agg_values = {
            agg_type: round(float(a['value'].get(agg_type.lower(), 'N/A')), 2) 
            if a['value'].get(agg_type.lower()) != 'N/A' else None
            for agg_type in aggregate_types
        }
        aggregates.append({
            "timestamp": format_timestamp(a['timestamp']),
            "values": agg_values
        })

    return {
        "asset": asset['assetName'],
        "property": property_info['name'],
        "dataType": property_info['dataType'],
        "startTime": start_time.isoformat(),
        "endTime": end_time.isoformat(),
        "resolution": resolution,
        "aggregatedData": aggregates
    }


def parse_time(time_str):
    """
    Parse time string to datetime object.
    Supports:
    - 'now'
    - Relative time: -<number><unit> where unit is m (minutes), h (hours), or d (days)
    - ISO 8601 format
    - YYYY-MM-DD HH:MM:SS format
    - Unix timestamp (integer or float)
    """
    if not time_str:
        return datetime.now(timezone.utc)

    if time_str == 'now':
        return datetime.now(timezone.utc)

    if isinstance(time_str, (int, float)):
        # Unix timestamp
        return datetime.fromtimestamp(time_str, tz=timezone.utc)

    if isinstance(time_str, str):
        if time_str.startswith('-'):
            # Relative time
            match = re.match(r'-(\d+)([mhd])', time_str)
            if match:
                amount, unit = match.groups()
                amount = int(amount)
                if unit == 'm':
                    delta = timedelta(minutes=amount)
                elif unit == 'h':
                    delta = timedelta(hours=amount)
                elif unit == 'd':
                    delta = timedelta(days=amount)
                else:
                    raise ValueError(f"Unsupported time unit: {unit}")
                return datetime.now(timezone.utc) - delta

        # ISO format
        try:
            return datetime.fromisoformat(time_str.replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
        except ValueError:
            # If it's not ISO format, try parsing as a custom format
            try:
                return datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            except ValueError:
                raise ValueError(f"Invalid datetime format: {time_str}")

    raise ValueError(f"Unsupported time format: {time_str}")


def format_timestamp(timestamp):
    """Format timestamp to ISO 8601 string."""
    if isinstance(timestamp, (int, float)):
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
    return timestamp.isoformat()



def success_response(response, event):
    actionGroup = event['actionGroup']
    apiPath = event['apiPath']
    httpMethod =  event['httpMethod']
    messageVersion = event['messageVersion']


    responseBody =  {
        "application/json": {
            "body": response
        }
    }
    
    action_response = {
        'actionGroup': actionGroup,
        'apiPath': apiPath,
        'httpMethod': httpMethod,
        'httpStatusCode': 200,
        'responseBody': responseBody
    }

    return  {'response': action_response, 'messageVersion': messageVersion}


def error_response(status_code, message, event):
    actionGroup = event['actionGroup']
    apiPath = event['apiPath']
    httpMethod =  event['httpMethod']
    messageVersion = event['messageVersion']

    responseBody =  {
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

    return  {'response': action_response, 'messageVersion': messageVersion}
    