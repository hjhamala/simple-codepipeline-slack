import boto3
import uuid
import ast
import requests
import json
import os
from botocore.exceptions import ClientError


def initialize_s3(bucket, key):
    s3 = boto3.client('s3')
    code_pipeline = boto3.client('codepipeline')
    print("Initializing statuses")
    pipelines_statuses_t = {}
    for pipeline in code_pipeline.list_pipelines()["pipelines"]:
        pipelines_statuses_t.update({pipeline['name'] : "Succeeded"})
    filename = "/tmp/" + str(uuid.uuid4())
    f = open(filename, 'w+')
    f.write(str(pipelines_statuses_t))
    f = open(filename, 'r+')
    s3.upload_fileobj(f, bucket, key)
    f.close()

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    code_pipeline = boto3.client('codepipeline')

    software_name = os.environ['SOFTWARE']

    build_start = os.environ['BUILD_START']
    success = os.environ['BUILD_SUCCESS']
    failure = os.environ['BUILD_FAILURE']

    bucket = os.environ['BUCKET']
    key = os.environ['KEY']

    # Try to read stored values
    try:
        filename = "/tmp/" + str(uuid.uuid4())
        s3.download_file(bucket, key, filename)
        statuses = open(filename).read()
        pipelines_statuses = ast.literal_eval(statuses)

        pipelines_statuses_t = {}
        for pipeline in code_pipeline.list_pipelines()["pipelines"]:
            pipelines_statuses_t.update({pipeline['name'] : "Succeeded"})

        if len(pipelines_statuses) != len(pipelines_statuses_t):
            print('Pipelines changed')
            initialize_s3(bucket, key)

        for pipeline in pipelines_statuses:
            res = code_pipeline.get_pipeline_state(name=pipeline)
            execution_id =  res['stageStates'][0]['latestExecution']['pipelineExecutionId']
            status = code_pipeline.get_pipeline_execution(pipelineName=pipeline,pipelineExecutionId=execution_id)
            status_string = status['pipelineExecution']['status']
            if status_string != pipelines_statuses[pipeline]:
                filename = "/tmp/" + str(uuid.uuid4())
                pipelines_statuses[pipeline] = status_string
                f = open(filename, 'w+')
                f.write(str(pipelines_statuses))
                f = open(filename, 'r+')
                s3.upload_fileobj(f, bucket, key)
                f.close()
                message = software_name + " proudly presents: Status change in: " + pipeline + " New status: " + status_string
                url = build_start
                if status_string == "InProgress":
                    url = build_start
                if status_string == "Succeeded":
                    url = success
                if status_string == "Failed":
                    url = failure
                response = requests.post(
                    url, data=json.dumps({'text': message}),
                    headers={'Content-Type': 'application/json'}
                )


    except ClientError as e:
        if e.response['Error']['Code'] == "404":
            # No file so lets create it
            initialize_s3(bucket, key)
        print "Something else went wrong"







