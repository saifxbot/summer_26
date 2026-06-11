import json

def lambda_handler(event, context):
    print("Hello world, from lambda function")

    print("Received SNS event:")
    print(json.dumps(event))

    return {
        "statusCode": 200,
        "body": json.dumps("Hello world, from lambda function")
    }