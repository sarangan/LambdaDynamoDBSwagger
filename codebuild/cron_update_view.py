import boto3
import json
from botocore.vendored import requests
from datetime import datetime

account_id = "XXXX"
client_id = "XXXXX"
client_secret = "XXXXX"
access_token_url = "XXXX"
dynamodb_table = "XXXX"


dynamo_db = boto3.client('dynamodb')

#get access token for bright cove
def get_access_token():
    access_token = None
    r = requests.post(access_token_url, params="grant_type=client_credentials", auth=(client_id, client_secret), verify=False)
    if r.status_code == 200:
        access_token = r.json().get('access_token')
    return access_token


#get views
def get_views(category, limit=30):
    access_token = get_access_token()
    headers = {'Authorization': 'Bearer ' + access_token, "Content-Type": "application/json"}

    url = ("https://analytics.api.brightcove.com/v1/data?accounts={account_id}&dimensions=video&fields=video_view&sort=-video_view&from=-60d&to=now&limit={q_limit}&where=video.q==category:{q_category}").format(account_id=account_id, q_limit=limit, q_category=category )

    r = requests.get(url, headers=headers)

    return r.json()


#get the video item
def get_publish_key(video_id):
    response = dynamo_db.query(
        TableName=dynamodb_table,
        KeyConditionExpression='id = :vid',
        ProjectionExpression='published_at',
        ExpressionAttributeValues = {
            ':vid': {
                'N': video_id,
            }
        }
    )

    if response and 'Items' in response:
        get_item = response['Items']
        if get_item and len(get_item) > 0:
            #we found our item
            item = get_item[0]
            if item and 'published_at' in item:
                if 'S' in item['published_at']:
                    published_at = item['published_at']['S']
                    if published_at:
                        return published_at

    return False

#update dynamo_db table with views count
def update_views(video_id, video_view):

    get_published_at = get_publish_key(video_id)

    if video_id and video_view and get_published_at:
        response = dynamo_db.update_item(TableName = dynamodb_table,
        Key={
            'id': {
                'N': str(video_id)
            },
            'published_at': {
                'S': str(get_published_at)
            }
        },
        ExpressionAttributeNames={
            '#VV': 'video_view'
        },
        ExpressionAttributeValues={
            ':v': {
                'N': str(video_view),
            }
        },
        UpdateExpression='SET #VV = :v'
        )
        return response

    return False


#get all the bright cove categories
def getCategories():
    category = ('lifestyle - beauty', 'entertainment - movies','entertainment - music','entertainment - others','entertainment - theatre','entertainment - tv','lifestyle - fashion','lifestyle - food','lifestyle - business','lifestyle - history','lifestyle - hobbies','lifestyle - motoring','lifestyle - nightlife','lifestyle - others','lifestyle - shopping','lifestyle - travel','news - business','news - crime','news - education','news - environment','news - general','news - housing','news - politics','news - transport','lifestyle - technology','news - technology','lifestyle - health','news - health','sports - badminton','sports - basketball','sports - formula 1','sports - others','sports - rugby','sports - soccer','sports - swimming','sports - tennis')

    return category

## TODO: not using it
def get_views_video(video_id):
    access_token = get_access_token()
    headers = {'Authorization': 'Bearer ' + access_token, "Content-Type": "application/json"}

    url = ("https://analytics.api.brightcove.com/v1/data?accounts={account_id}&dimensions=video&fields=video_view&from=-60d&to=now&where=video=={video_id}").format(account_id=account_id, video_id=video_id )

    r = requests.get(url, headers=headers)

    return r.json()

#get the video item
def get_last_record():
    response = dynamo_db.query(
        TableName=dynamodb_table,
        KeyConditionExpression='id = :vid',
        ProjectionExpression='cron_log',
        ExpressionAttributeValues = {
            ':vid': {
                'N': str(1),
            }
        }
    )

    if response and 'Items' in response:
        get_item = response['Items']
        if get_item and len(get_item) > 0:
            #we found our item
            item = get_item[0]
            if item and 'cron_log' in item:
                cron_log_item = item['cron_log']
                if cron_log_item and 'M' in cron_log_item:
                    cron_log_item_data = cron_log_item['M']
                    # if 'page' in cron_log_item_data and cron_log_item_data['page']:
                    #     if 'N' in cron_log_item_data['page'] and cron_log_item_data['page']:
                    #         return int(cron_log_item_data['page']['N'])
                    #
                    # if 'category' in cron_log_item_data and cron_log_item_data['category']:
                    #     if 'N' in cron_log_item_data['category'] and cron_log_item_data['category']:
                    #         return_dict['category'] = int(cron_log_item_data['category']['N'])

                    return cron_log_item_data

    return 0


#insert last processed page
def update_last_process(last_record_data):
    cron_log_item = {}
    cron_log_item['id'] = {'N': str(1) }
    cron_log_item['published_at'] = {'S': 'NA'}
    cron_log_item['li_category'] = {'S': 'NA'}
    cron_log_item['video_view'] = {'N': '0'}

    if last_record_data:
        cron_log_item['cron_log'] = {'M': last_record_data}
    else:
        extra = {}
        extra['page'] = {'N': str(0)}
        extra['updated_at'] = {'S': str(datetime.now()) }

        extra['category'] = {'N': str(0) }
        extra['category_updated_at'] = {'S': str(datetime.now()) }
        cron_log_item['cron_log'] = {'M': extra}

    response = dynamo_db.put_item(TableName = dynamodb_table, Item = cron_log_item)
    return response



#invoke api call to update items
def update_item(event, context):
    bc_response = []
    last_category = -1
    last_record_data = get_last_record()
    if last_record_data:
        if 'category' in last_record_data and last_record_data['category']:
            if 'N' in last_record_data['category'] and last_record_data['category']:
                last_category = int(last_record_data['category']['N'])

    last_category += 1
    if last_category >= len(getCategories()):
        last_category = 0

    #update the last record
    if last_record_data:
        last_record_data['category'] = {'N': str(last_category) }
        last_record_data['category_updated_at'] = {'S': str(datetime.now()) }

    #for category in getCategories(): //not going to loop

    category = getCategories()[last_category]

    cat_views_result = get_views(category, 20)
    if cat_views_result:

        update_last_process(last_record_data) #update the page

        if 'items' in cat_views_result:
            cat_views = cat_views_result['items']
            if cat_views and len(cat_views_result['items']) > 0:
                for item in cat_views:
                    if 'video' in item and 'video_view' in item and item['video_view']:
                        bc_response.append(update_views(item['video'], item['video_view']) )

    return {"statusCode": 200, "result": bc_response, "bc_result" : cat_views_result }
