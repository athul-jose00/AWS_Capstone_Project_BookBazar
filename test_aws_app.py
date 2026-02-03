from aws_app import app
import aws_app
import os
import sys
import boto3
from moto import mock_aws as _mock_aws

# Mock Credentials (must be set before importing aws_app)
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['AWS_SECURITY_TOKEN'] = 'testing'
os.environ['AWS_SESSION_TOKEN'] = 'testing'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

# Start Moto mock for all AWS services
mock = _mock_aws()
mock.start()

# Import the app AFTER starting moto so boto3 resources are intercepted


def setup_infrastructure():
    print('>>> Creating Mocked AWS Resources (DynamoDB Tables & SNS)...')

    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    sns = boto3.client('sns', region_name='us-east-1')

    # Create tables that match what aws_app expects
    # Users table (partition key: email)
    try:
        dynamodb.create_table(
            TableName='BookBazaar_Users',
            KeySchema=[{'AttributeName': 'email', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'email', 'AttributeType': 'S'}],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
    except Exception:
        pass

    # Books table (partition key: id)
    try:
        dynamodb.create_table(
            TableName='BookBazaar_Books',
            KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'id', 'AttributeType': 'S'}],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
    except Exception:
        pass

    # Orders table (partition key: id)
    try:
        dynamodb.create_table(
            TableName='BookBazaar_Orders',
            KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'id', 'AttributeType': 'S'}],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
    except Exception:
        pass

    # Create an SNS topic and set it on the imported module so aws_app uses it
    response = sns.create_topic(Name='bookbazar_topic')
    aws_app.SNS_TOPIC_ARN = response['TopicArn']

    print(
        f">>> Mock Environment Ready. SNS Topic ARN: {aws_app.SNS_TOPIC_ARN}")


if __name__ == '__main__':
    try:
        setup_infrastructure()
        print('\n>>> Starting Flask Server at http://localhost:5000')
        print('>>> Stop with CTRL+C. Mock data will be lost on exit.')
        # use_reloader=False prevents spawning a new process that loses mock state
        app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
    finally:
        mock.stop()
