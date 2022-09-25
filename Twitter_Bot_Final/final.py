#IMPORT LIBRARIES
import requests
import numpy as np
import pandas as pd
from pandas import Timestamp
import tweepy
import os
import dataframe_image as dfi
import boto3
import botocore 
from io import BytesIO
from datetime import date
from io import StringIO
from PIL import Image
import time
import json

##CALL TO AWS SECRET MANAGER
client = boto3.client('secretsmanager')
response = client.get_secret_value(SecretId='apex_twitter_bot_secrets')
database_secrets = json.loads(response['SecretString'])

##MAKE CALL TO APEX CRAFTING END POINT
##https://portal.apexlegendsapi.com/
apex_api_key = database_secrets['apex_api_key']
url = 'https://api.mozambiquehe.re/crafting?auth='+ apex_api_key

##MAKE REQUEST AND FORMAT RETURN AS JSON
r = requests.get(url)
data = r.json()

##FLATTEN JSON
flattened = pd.json_normalize(data
                             , record_path =['bundleContent']
                             , meta= ['bundle', 'bundleType', 'startDate', 'endDate']
                             , errors='ignore')

##REMOVE EXTRA AMMO ROWS - JUST NEED ONE ROW FOR AMMO
flattened.drop(flattened[flattened['item'] == 'special'].index, inplace = True)
flattened.drop(flattened[flattened['item'] == 'shotgun'].index, inplace = True)
flattened.drop(flattened[flattened['item'] == 'highcal'].index, inplace = True)
flattened.drop(flattened[flattened['item'] == 'sniper'].index, inplace = True)
flattened.drop(flattened[flattened['item'] == 'arrows'].index, inplace = True)

##REARRANGE COLUMNS
flattened = flattened[["bundleType", "startDate", "endDate", "itemType.name", "item", "cost", "itemType.rarity", "itemType.asset"]]

##RENAME FIELDS
flattened = flattened.rename(columns = {'bundleType':'Type'
                                        , 'startDate':'Start Date (UTC)'
                                        , 'endDate':'End Date (UTC)'
                                        , 'itemType.name':'Item Name'
                                        , 'item':'Item'
                                        , 'cost':'Cost'
                                        , 'itemType.rarity':'Rarity'
                                        , 'itemType.asset':'Asset'})

##REMOVE UNDERSCORES
flattened['Item Name'] = flattened['Item Name'].str.replace("_", " ")
flattened['Item'] = flattened['Item'].str.replace("_", " ")

##MAKE COLUMNS TITLE CASE
flattened.Type = flattened.Type.str.title()
flattened['Item Name'] = flattened['Item Name'].str.title()
flattened['Item'] = flattened['Item'].str.title()

##CONVERT DATES
flattened['Start Date (UTC)'] = pd.to_datetime(flattened['Start Date (UTC)'])
flattened['End Date (UTC)'] = pd.to_datetime(flattened['End Date (UTC)'])

#START DATE CONVERT FROM UTC TO EST
list_temp = []
for row in flattened['Start Date (UTC)']:
    list_temp.append(Timestamp(row, tz = 'UTC').tz_convert('US/Eastern'))
flattened['Start (EST)'] = list_temp

flattened['Start (EST)'] = flattened['Start (EST)'].dt.strftime("%-m/%d/%y %H:%M")

##END DATE CONVERT FROM UTC TO EST
list_temp = []
for row in flattened['End Date (UTC)']:
    list_temp.append(Timestamp(row, tz = 'UTC').tz_convert('US/Eastern'))
flattened['End (EST)'] = list_temp

flattened['End (EST)'] = flattened['End (EST)'].dt.strftime("%-m/%d/%y %H:%M")

##FINALIZE FIELDS
flattened = flattened[["Type", "Item Name", "Rarity", "Cost", "Start (EST)", "End (EST)" ]]

##RENAME FIELDS
flattened = flattened.rename(columns = {'New Item Name':'Item'})

##REPLACE NAN WITH '-'
flattened['Start (EST)'] = flattened['Start (EST)'].replace(np.nan, '-')
flattened['End (EST)'] = flattened['End (EST)'].replace(np.nan, '-')

##DROP INDEX
df = flattened.style.hide_index()

##DELETE YESTERDAYS APEX CRAFTING ITEM TABLE FROM S3 BUCKET
def s3_delete():
    ##CALL TO SECRETS MANAGER
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='apex_twitter_bot_secrets')
    database_secrets = json.loads(response['SecretString'])

    ##GET AWS ACCESS AND SECRET KEYS
    aws_access_key_id = database_secrets['S3_ACCESS_KEY']
    aws_secret_access_key = database_secrets['S3_SECRET_KEY']

    ##DEFINE WHICH S3 BUCKET TO DELETE FROM 
    bucket_name = 'twitterapextables'

    ##DELETE ALL OBJECTS FROM S3 BUCKET
    s3_resource = boto3.resource('s3', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
    bucket = s3_resource.Bucket(bucket_name)
    bucket.objects.delete()

##WRITE TODAYS CRAFTING ITEMS TO THE S3 BUCKET
def s3_write():
    ##CALL TO SECRETS MANAGER
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='apex_twitter_bot_secrets')
    database_secrets = json.loads(response['SecretString'])

    ##GET AWS ACCESS AND SECRET KEYS
    aws_access_key_id = database_secrets['S3_ACCESS_KEY']
    aws_secret_access_key = database_secrets['S3_SECRET_KEY']

    ##DEFINE NAME OF FILE TO BE WRITTEN TO THE S3 BUCKET
    from datetime import date
    today = date.today()
    date = str(today.strftime("%m%d%y"))
    filename = 'REPLICATOR_CRAFTING_' + date + '.jpeg'

    ##CONVERT DATAFRAME TO IMAGE AND STORE IMAGE OF DATAFRAME IN MEMORY  
    buf = BytesIO()
    dfi.export(df, buf, table_conversion = 'matplotlib')
    PNG = buf.getvalue()

    ##DEFINE WHICH S3 BUCKET TO WRITE TO 
    bucket = 'twitterapextables' 

    ##WRITE TODAYS IMAGE OF DATAFRAME TO S3 BUCKET
    s3_resource = boto3.resource('s3', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
    s3_resource.Object(bucket, filename).put(Body=PNG)
   
##TWEET OUT TODAYS CRAFTING MATERIALS 
def create_tweet():
    ##DEFINE THE NAME OF THE BUCKET TO PULL THE IMAGE FROM AND DEFINE DATE VARIABLE
    from datetime import date
    today = date.today()
    date = str(today.strftime("%m%d%y"))
    filename = 'REPLICATOR_CRAFTING_' + date + '.jpeg'
    key = 'REPLICATOR_CRAFTING_' + date + '.jpeg'

    ##GET IMAGE FROM S3 THAT NEEDS TO BE TWEETED OUT
    def image_from_s3(bucket, key):
        ##CALL TO SECRETS MANAGER
        client = boto3.client('secretsmanager')
        response = client.get_secret_value(SecretId='apex_twitter_bot_secrets')
        database_secrets = json.loads(response['SecretString'])
        
        ##GET AWS ACCESS AND SECRET KEYS
        aws_access_key_id = database_secrets['S3_ACCESS_KEY']
        aws_secret_access_key = database_secrets['S3_SECRET_KEY']

        ##GET IMAGE FROM S3 BUCKET AND STORE IN MEMORY 
        s3 = boto3.resource('s3', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
        bucket = s3.Bucket(bucket)
        image = bucket.Object(key)
        img_data = image.get().get('Body').read()

        return Image.open(BytesIO(img_data))

    ##DEFINE WHICH S3 BUCKET AND FILE NAME TO PULL FROM 
    bucket = 'twitterapextables'
    key = 'REPLICATOR_CRAFTING_' + date + '.jpeg'

    ##CALL IMAGE_FROM_S3 FUNCTION AND PASS BUCKET AND KEY 
    ##STORES IMAGE FROM S3 IN IMG VARIABLE 
    img = image_from_s3(bucket, key)

    ##SAVE IMAGE AS PNG IN MEMORY
    b = BytesIO()
    img.save(b, "PNG")
    b.seek(0)    
   
    ##CALL TO SECRETS MANAGER
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='apex_twitter_bot_secrets')
    database_secrets = json.loads(response['SecretString'])

    ##GET TWITTER KEYS
    twitter_api_key = database_secrets['twitter_api_key']
    twitter_api_secret = database_secrets['twitter_api_secret']
    twitter_bearer_token = database_secrets['twitter_bearer_token']
    twitter_access_token = database_secrets['twitter_access_token']
    twitter_access_token_secret = database_secrets['twitter_access_token_secret']

    ##GAIN ACCESS AND CONNECT TO TWITTER API USING CREDENTIALS
    client = tweepy.Client(twitter_bearer_token, twitter_api_key, twitter_api_secret, twitter_access_token, twitter_access_token_secret)
    auth = tweepy.OAuth1UserHandler(twitter_api_key, twitter_api_secret, twitter_access_token, twitter_access_token_secret)
    api = tweepy.API(auth)
  
    ##DEFINE DATE VARIABLE FOR TWEET
    from datetime import date
    today = date.today()
    date = str(today.strftime("%-m/%d/%Y"))
   
    ##BUILD TWEET MESSAGE
    tweet = "Crafting as of " + date
   
    ##UPLOAD MEDIA TO TWITTER APIV1.1
    ret = api.media_upload(filename="dummy_string", file=b)

    ##ATTACH MEDIA AND TEXT TO TWEET
    api.update_status(media_ids=[ret.media_id_string], status=tweet)
   
##RUN ALL FUNCTIONS
s3_delete()
time.sleep(2)
s3_write() 
time.sleep(2)
create_tweet()