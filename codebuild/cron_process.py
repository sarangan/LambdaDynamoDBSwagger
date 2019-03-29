import boto3
import json
from botocore.vendored import requests
from datetime import datetime

account_id = "XXXX"
client_id = "XXXXX"
client_secret = "XXXXX"
access_token_url = "XXXX"
profiles_base_url = "XXXXX"
dynamodb_table = "XXXX"

dynamo_db = boto3.client('dynamodb')

#get access token for bright cove
def get_access_token():
    access_token = None
    r = requests.post(access_token_url, params="grant_type=client_credentials", auth=(client_id, client_secret), verify=False)
    if r.status_code == 200:
        access_token = r.json().get('access_token')
    return access_token

def get_videos(size = 25, page = 1 ):
    access_token = get_access_token()
    offset = size * (page - 1)

    headers = {'Authorization': 'Bearer ' + access_token, "Content-Type": "application/json"}
    url = ("https://cms.api.brightcove.com/v1/accounts/{accountid}/videos?limit={size}&offset={offset}&sort=-published_at&q=state:ACTIVE").format(accountid=account_id, size=size, offset=offset)
    r = requests.get(url, headers=headers)
    return r.json()

#get altered category for new li
def getCategory(category):
    lo_category = 'NA'
    if category:
        category = category.lower().strip()

        if category == 'lifestyle - beauty':
            lo_category = 'beauty'
        elif category in ['entertainment - movies','entertainment - music','entertainment - others','entertainment - theatre','entertainment - tv']:
            lo_category = 'entertainment'
        elif category == 'lifestyle - fashion':
            lo_category = 'fashion'
        elif category == 'lifestyle - food':
            lo_category = 'food'
        elif category in ['lifestyle - business','lifestyle - history','lifestyle - hobbies','lifestyle - motoring','lifestyle - nightlife','lifestyle - others','lifestyle - shopping','lifestyle - travel','news - business','news - crime','news - education','news - environment','news - general','news - housing','news - politics','news - transport']:
            lo_category = 'lifestyle'
        elif category in ['lifestyle - technology','news - technology']:
            lo_category = 'tech'
        elif category in ['lifestyle - health','news - health','sports - badminton','sports - basketball','sports - formula 1','sports - others','sports - rugby','sports - soccer','sports - swimming','sports - tennis']:
            lo_category = 'wellness'

    return lo_category

#format null to str
def formatData(data, default="NA"):

    if data:
        return data
    else:
        return default

#format tags
def formatTags(tags=[]):

    list_temp = []
    for x in tags:
        list_temp.append(
            {
                'S': str(x)
            }
        )

    return list_temp

#insert brightcove data to dynamodb
def generate_item(item):

    video_item = {}

    if 'id' in item and item['id'] and 'name' in item and item['name'] and 'published_at' in item and item['published_at'] and 'state' in item and str(item['state']).upper() == 'ACTIVE':

        if 'name' in item and item['name']:
            video_item['name'] = {'S': item['name'] }

        if 'description' in item and item['description']:
            video_item['description'] = {'S': item['description'] }

        if 'long_description' in item and item['long_description']:
            video_item['long_description'] = {'S': item['long_description'] }

        if 'tags' in item and item['tags'] and len(item['tags']) > 0:
            video_item['tags'] = { 'L': formatTags(item['tags']) }

        if 'images' in item and item['images']:
            images = {}
            if 'poster' in item['images'] and item['images']['poster']:
                if 'src' in item['images']['poster'] and item['images']['poster']['src']:
                    images['poster'] = {'S' : item['images']['poster']['src']}
            if 'thumbnail' in item['images'] and item['images']['thumbnail']:
                if 'src' in item['images']['thumbnail'] and item['images']['thumbnail']['src']:
                    images['thumbnail'] = {'S' : item['images']['thumbnail']['src']}
            video_item['images'] = { 'M': images }

        if 'published_at' in item and item['published_at']:
            video_item['published_at'] = { 'S': item['published_at'] }

        if 'folder_id' in item and item['folder_id']:
            video_item['folder_id'] = {'S': item['folder_id'] }

        # if 'state' in item and item['state']:
        #     video_item['state'] = { 'S': item['state']}

        video_item['video_view'] = { 'N': '0'}

        extra = {}
        if 'complete' in item and item['complete']:
            extra['complete'] = {'BOOL':formatData(item['complete'], False)}
        if 'duration' in item and item['duration']:
            extra['duration'] = {'N': str(formatData(item['duration'],0))}
        if 'original_filename' in item and item['original_filename']:
            extra['original_filename'] = {'S': item['original_filename']}
        if 'reference_id' in item and item['reference_id']:
            extra['reference_id'] = {'S': item['reference_id']}
        if 'economics' in item and item['economics']:
            extra['economics'] = {'S': item['economics']}
        video_item['extra'] = { 'M': extra }

        if 'custom_fields' in item and item['custom_fields']:
            custom_fields = {}
            if 'source' in item['custom_fields'] and item['custom_fields']['source']:
                custom_fields['source'] = {'S': item['custom_fields']['source']}
            if 'category' in item['custom_fields'] and item['custom_fields']['category']:
                custom_fields['category'] = {'S': item['custom_fields']['category']}
                video_item['li_category'] = {'S': getCategory(item['custom_fields']['category'])}
            if 'sphcopyright' in item['custom_fields'] and item['custom_fields']['sphcopyright']:
                custom_fields['sphcopyright'] = {'S': item['custom_fields']['sphcopyright']}
            if 'language' in item['custom_fields'] and item['custom_fields']['language']:
                custom_fields['language'] = {'S': item['custom_fields']['language']}
            if 'rightsusageterms' in item['custom_fields'] and item['custom_fields']['rightsusageterms']:
                custom_fields['rightsusageterms'] = {'S': item['custom_fields']['rightsusageterms']}
            video_item['custom_fields'] = { 'M': custom_fields }

        if 'updated_by' in item and item['updated_by']:
            updated_by = {}
            if 'type' in item['updated_by'] and item['updated_by']['type']:
                updated_by['type'] = {'S': item['updated_by']['type']}
            if 'updated_at' in item['updated_by'] and item['updated_by']['updated_at']:
                updated_by['updated_at'] = {'S': item['updated_by']['updated_at']}
            video_item['updated_by'] = { 'M': updated_by }

        if 'created_by' in item and item['created_by']:
            created_by = {}
            if 'type' in item['created_by'] and item['created_by']['type']:
                created_by['type'] = {'S': item['created_by']['type']}
            if 'id' in item['created_by'] and item['created_by']['id']:
                created_by['id'] = {'N': str(item['created_by']['id'])}
            if 'email' in item['created_by'] and item['created_by']['email']:
                created_by['email'] = {'S': item['created_by']['email']}
            if 'created_at' in item and item['created_at']:
                created_by['created_at'] = {'S': item['created_at']}
            video_item['created_at'] = { 'M': created_by }

        if 'id' in item and item['id']:
                video_item['id'] = {'N': str(item['id']) }
                # response = dynamo_db.put_item(TableName = dynamodb_table, Item = video_item)
                # return response
                return video_item

    return False

#insert batch items
def insert_batch_items(video_items):
    request_items = {}
    request_items[dynamodb_table] = video_items
    response = dynamo_db.batch_write_item( RequestItems=request_items )

    #response = dynamo_db.put_item(TableName = dynamodb_table, Item = video_item)
    return response

#get the video item
def get_last_page():
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
                    return cron_log_item_data
                    # if 'page' in cron_log_item_data and cron_log_item_data['page']:
                    #     if 'N' in cron_log_item_data['page'] and cron_log_item_data['page']:
                    #         return int(cron_log_item_data['page']['N'])

    return 0


#insert last processed page
def update_last_process(cron_log_item_data):
    cron_log_item = {}
    cron_log_item['id'] = {'N': str(1) }
    cron_log_item['published_at'] = {'S': 'NA'}
    cron_log_item['li_category'] = {'S': 'NA'}
    cron_log_item['video_view'] = {'N': '0'}

    if cron_log_item_data:
        cron_log_item['cron_log'] = {'M': cron_log_item_data}
    else:
        extra = {}
        extra['page'] = {'N': str(0)}
        extra['updated_at'] = {'S': str(datetime.now()) }

        extra['category'] = {'N': str(0) }
        extra['category_updated_at'] = {'S': str(datetime.now()) }
        cron_log_item['cron_log'] = {'M': extra}

    # extra = {}
    # extra['page'] = {'N': str(page)}
    # extra['updated_at'] = {'S': str(datetime.now()) }
    #cron_log_item['cron_log'] = {'M': extra}

    response = dynamo_db.put_item(TableName = dynamodb_table, Item = cron_log_item)
    return response


#invoke api call
def add_item(event, context):

    page = 1
    bc_response = []
    last_page = 0

    cron_log_item_data = get_last_page()
    if cron_log_item_data:
        if 'page' in cron_log_item_data and cron_log_item_data['page']:
            if 'N' in cron_log_item_data['page'] and cron_log_item_data['page']:
                last_page = int(cron_log_item_data['page']['N'])

    page = last_page + 1

    if cron_log_item_data:
        cron_log_item_data['page'] = {'N': str(page)}
        cron_log_item_data['updated_at'] = {'S': str(datetime.now()) }

    bc_result = get_videos(30, page)

    if bc_result:

        update_last_process(cron_log_item_data) #update the page
        video_items = []
        for item in bc_result:

            process_item = generate_item(item)
            if process_item:
                insert_data = {
                       'PutRequest': {
                           'Item': process_item
                       }
                }
                video_items.append(insert_data)

            if len(video_items) == 20: #20 batches

                #process batch
                bc_response.append(insert_batch_items(video_items))

                del video_items[:]

        if len(video_items) > 0:
            bc_response.append(insert_batch_items(video_items))

    if len(bc_result) == 0: #end of the page
        update_last_process(0)



    return {"statusCode": 200, "result": bc_response }
