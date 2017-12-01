import boto3
import uuid
import ast
import requests
import json
import os
from botocore.exceptions import ClientError

def write_status(bucket, key, statuses):
    filename = "/tmp/" + str(uuid.uuid4())
    f = open(filename, 'w+')
    f.write(str(statuses))
    f = open(filename, 'r+')
    s3.upload_fileobj(f, bucket, key)
    f.close()

def initialize_s3(bucket, key):
    s3 = boto3.client('s3')
    code_pipeline = boto3.client('codepipeline')
    print("Initializing statuses")
    pipelines_statuses_t = {}
    for pipeline in code_pipeline.list_pipelines()["pipelines"]:
        pipelines_statuses_t.update({pipeline['name'] : "Succeeded"})
    write_status(bucket, key, pipelines_statuses_t)

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    code_pipeline = boto3.client('codepipeline')
    code_commit = boto3.client('codecommit')
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

        if len(pipelines_statuses) != len(code_pipeline.list_pipelines()["pipelines"]):
            print('Pipelines changed')
            initialize_s3(bucket, key)

        for pipeline in pipelines_statuses:
            res = code_pipeline.get_pipeline_state(name=pipeline)
            execution_id =  res['stageStates'][0]['latestExecution']['pipelineExecutionId']
            status = code_pipeline.get_pipeline_execution(pipelineName=pipeline,pipelineExecutionId=execution_id)
            status_string = status['pipelineExecution']['status']
            if status_string != pipelines_statuses[pipeline]:

                if not status['pipelineExecution']['artifactRevisions']:
                    # We dont have yet revision status so lets break out

                    print "Empty artifact revisions - breaking"
                    print (status)
                    continue
                artifact_url = status['pipelineExecution']['artifactRevisions'][0]['revisionUrl']
                commit_id = artifact_url.split('/')[-1]
                git_repository = artifact_url.split('/')[-3]
                commit_info = code_commit.get_commit(repositoryName=git_repository, commitId=commit_id)
                author = commit_info['commit']['committer']['name']
                commit_message = commit_info['commit']['message']
                pipelines_statuses[pipeline] = status_string

                message = software_name + " proudly presents: Status change in: " + pipeline + " New status: " + status_string
                pre_text = "Status change in: " + pipeline

                url = build_start
                if status_string == "InProgress":
                    url = build_start
                if status_string == "Succeeded":
                    url = success
                if status_string == "Failed":
                    url = failure
                slack_message = {
                    "attachments": [
                        {
                            "fallback": message,
                            "color": "#36a64f",
                            "pretext": pre_text,
                            "author_name": author,
                            "title": software_name,
                            "title_link": artifact_url,
                            "text": commit_message,
                            "fields": [
                                {
                                    "title": status_string,
                                    "short": False
                                }
                            ]
                        }
                    ]
                }
                response = requests.post(
                    url, data=json.dumps(slack_message),
                    headers={'Content-Type': 'application/json'}
                )
        write_status(bucket, key, pipelines_statuses)


    except ClientError as e:
        if e.response['Error']['Code'] == "404":
            # No file so lets create it
            initialize_s3(bucket, key)
        print "Something else went wrong"
        print (e)




