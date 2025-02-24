# Work order creation stack

## Create the stack using the `AWS CLI`

```bash
aws cloudformation create-stack \
  --stack-name work-order-stack \
  --template-body file://workorder/infra-workorder-stack.yml \
  --capabilities CAPABILITY_IAM \
  --region us-east-1
```

## Update the stack using the `AWS CLI`

```bash
aws cloudformation update-stack \
  --stack-name work-order-stack \
  --template-body file://workorder/infra-workorder-stack.yml \
  --capabilities CAPABILITY_IAM \
  --region us-east-1
```

## Monitor the progress

```bash
aws cloudformation describe-stacks --stack-name work-order-stack --region us-east-1
```

## Sample Event in API Gateway

Headers:

```txt
"Content-Type": "application/json"
```

Request Body

```json
{"equipmentId":"EQ-12345","requestDescription":"Annual maintenance and calibration for boiler"}
```

Response body

```json
{"workOrderNumber": "22592", "equipmentId": "EQ-12345", "requestDescription": "Annual maintenance and calibration for boiler", "submissionDatetime": "2024-08-26T21:13:00.338225Z", "message": "Work order 22592 has been submitted for equipment EQ-12345 at 2024-08-26T21:13:00.338225Z with the following request: Annual maintenance and calibration for boiler"}
```

Response headers

```json
{
  "Content-Type": "application/json",
  "X-Amzn-Trace-Id": "Root=1-66ccefdc-1ebbdb646f57018fed6b72c5;Parent=2c1c6acec761268c;Sampled=0;lineage=1e581afe:0"
}
```

## Amazon Q Business Plugin

Custom Plugin -> API Schema -> Define with in-line OpenAPI schema editor -> paste

Then replace line 7 (server url) with the WorkOrderApiEndpoint output from CFN stack.
