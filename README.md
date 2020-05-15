# What is it
A CloudFormation custom resource to create TransitGatewayAttachment with enabled IPv6.

Why: because current [Cloud Formation TransitGatewayAttachment](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-transitgatewayattachment.html) does not support IPv6 enabling.

# Instructions

## Setup
Package
```
S3_BUCKET=<your-s3-bucket-for-package>
make clean package
```

Deploy:
```
aws cloudformation deploy --stack-name cfn-cr-transit-gateway-attachment \
  --template-file ./template.packaged.yaml \
  --capabilities CAPABILITY_NAMED_IAM
```

## Test
Test custom resource with a stack containing IPv6-enabled VPC, TransitGateway and TransitGatewayAttachment.
```
aws cloudformation deploy --stack-name test-cr-transit-gateway-attachment \
  --template-file ./test/example.yaml
```
