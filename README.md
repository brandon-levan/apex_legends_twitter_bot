# Apex Legends Twitter Bot

## Summary
The goal of this project was to give Apex Players worldwide a feed that would display information about what loot is available in the Replicator for the current day. The solution I created is a Twitter account that posts a picture of table containing all of the items that can be found in the Replicator on the current day including attributes such as item name, rarity, cost, when the item enters and leaves the Replicator, and whether the loot item is in the Replicator for the day, week, or for the entire season. 

## Solution 

The solution was built using Python, Docker, and AWS. The solution was created with the following steps - 

* Get Data From the Apex Legends Status Crafting Rotation API and Format as a Data Frame
* Convert Data Frame to an Image File and Send an AWS S3 Bucket
* Read in Image File From S3 and Tweet Out the Information Using the Tweepy Package 
* Python Script That Does Steps 1-3 is Packaged Using Docker and Image is Uploaded to AWS ECR (Elastic Container Registry) 
* Python Script Stored in AWS ECR is Run Using AWS Lamba 
* AWS Lamba Function is Scheduled to Run Daily By Using AWS EventBirdge (Formerly AWS CloudWatch) 

Credentials for AWS, Apex Legends API, and Twitter are all stored in AWS Secrets Manager and are passed to the Python script using Boto3. Permissions on the AWS side are configured using AWS Identity and Access Management (IAM). 

A full explaination of technicalities of this project can be explained here [here](https://www.brandonlevan.me/blog/apex-legends-twitter-bot)

##Check Out My Blog Post on How I Built This Twitter Bot & My Twitter Bot
* [Building a Twitter Bot Using Python, Docker & Amazon Web Services - Blog Post](https://www.brandonlevan.me/blog/apex-legends-twitter-bot)
* [Twitter Bot - @whats_crafting](https://twitter.com/whats_crafting)


