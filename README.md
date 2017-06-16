# simple-codepipeline-slack
Lambda which posts AWS codepipeline changes to slack.

Guidelines for install:
* Make zipfile with necessary dependencies -> AST and requests
* install lambda
* create S3 bucket and give lambda execution role necessary permissions
* give lambda permission to read pipeline statuses (use the managed policy AWSCodePipelineReadOnlyAccess)
* set environment variables for the lambda
* create webhooks in Slack
* create trigger for lambda with CloudWatch Events for example: rate(1 minute)

Enviroment variables:
* SOFTWARE
* BUILD_START (webhook)
* BUILD_SUCCESS (webhook)
* BUILD_FAILURE (webhook)
* BUCKET
* KEY
