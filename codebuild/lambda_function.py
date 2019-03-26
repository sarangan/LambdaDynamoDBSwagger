import boto3
import json

dynamo_db = boto3.client('dynamodb')
bc_table = "bc_videos"

def api_handler(event, context):

    response = {}

    if 'videoid' in event and event['videoid']:
        video_id = event['videoid']
        # response = dynamo_db.get_item(TableName='bc_videos', Key={
        #     'id': {
        #         'N': video_id,
        #     }
        # })
        response = dynamo_db.scan(TableName='bc_videos',
            ExpressionAttributeValues={
                ':s': {
                    'S': video_id,
                },
            },
            FilterExpression='state = :s'
        })

    return {"statusCode": 200, "result": response }
