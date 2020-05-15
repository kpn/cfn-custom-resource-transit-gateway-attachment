import json
import logging

import boto3
from botocore.exceptions import ClientError
from crhelper import CfnResource
from retrying import retry

logger = logging.getLogger(__name__)

helper = CfnResource(json_logging=False, log_level='DEBUG', boto_level='CRITICAL')

default_options = {
    'Ipv6Support': 'enable',
    'DnsSupport': 'enable',
}


def get_options(properties):
    """Retrieve Options from the custom resources. Returns default values if they are not set."""
    try:
        options = properties['Options']
        if 'Ipv6Support' not in options:
            options['Ipv6Support'] = default_options['Ipv6Support']
        if 'DnsSupport' not in options:
            options['DnsSupport'] = default_options['DnsSupport']
    except KeyError:
        print('No options found, use default settings')
        options = default_options

    return options


def retry_if_result_true(result):
    """Return True if we should retry, False otherwise"""
    return result


@retry(stop_max_attempt_number=60, wait_fixed=5000, retry_on_result=retry_if_result_true)
def wait_attachment_state(ec2_client, attachment_id, desired_state):
    logger.debug('Waiting state  of attachment {} to be {}'.format(attachment_id, desired_state))

    try:
        resp = ec2_client.describe_transit_gateway_vpc_attachments(TransitGatewayAttachmentIds=[attachment_id])
    except ClientError as e:
        logger.debug('Failed to wait:{}'.format(e))
        return True
    attachments = resp['TransitGatewayVpcAttachments']
    if len(attachments) != 1:
        # Attachment_id not found, wont retry
        return False

    current_state = attachments[0]['State']
    logger.debug('Current state of attachment id={id}: {state}'.format(id=attachment_id, state=current_state))
    return current_state != desired_state

def create_if_not_exist_service_linked_role():
    iam_client = boto3.client('iam')
    resp = iam_client.list_roles()
    for role in resp['Roles']:
        if role['RoleName'] == 'AWSServiceRoleForVPCTransitGateway':
            # service-linked role existed, exit
            break
    else:
        # create service-linked role if not found
        iam_client.create_service_linked_role(AWSServiceName='transitgateway.amazonaws.com')

@helper.create
def create_resource(event, _):
    """Create new TransitGatewayVpcAttachment object"""

    logger.info('Creating')
    logger.debug('Event: {0}'.format(json.dumps(event)))

    properties_ = event['ResourceProperties']
    options = get_options(properties_)
    try:
        transit_gateway_id = properties_['TransitGatewayId']
        vpc_id = properties_['VpcId']
        subnet_ids = properties_['SubnetIds']
        tags = properties_['Tags'] if 'Tags' in properties_ else []
    except KeyError as e:
        raise ValueError('Error - setting not found: {}'.format(e))

    try:
        ec2_client = boto3.client('ec2')
    except ClientError as e:
        raise ValueError('Failed to create EC2 client: {}'.format(e))

    create_if_not_exist_service_linked_role()

    resp = ec2_client.create_transit_gateway_vpc_attachment(
        TransitGatewayId=transit_gateway_id,
        VpcId=vpc_id,
        SubnetIds=subnet_ids,
        Options=options,
        TagSpecifications=[
            {
                'ResourceType': 'transit-gateway-attachment',
                'Tags': tags,
            }
        ]
    )
    attachment_id = resp['TransitGatewayVpcAttachment']['TransitGatewayAttachmentId']
    if resp['TransitGatewayVpcAttachment']['State'] != 'available':
        # wait until state is 'available'
        wait_attachment_state(ec2_client, attachment_id, 'available')
    return attachment_id


@helper.delete
def delete_resource(event, _):
    logger.info('Deleting')
    logger.debug('Event: {0}'.format(json.dumps(event)))
    try:
        ec2_client = boto3.client('ec2')
    except ClientError as e:
        raise ValueError('Failed to create EC2 client: {}'.format(e))
    attachment_id = event['PhysicalResourceId']
    logger.debug('Deleting TransitGatewayAttachment with Id={}'.format(attachment_id))

    resp = ec2_client.describe_transit_gateway_vpc_attachments(TransitGatewayAttachmentIds=[attachment_id])
    if len(resp['TransitGatewayVpcAttachments']) == 0:
        logger.debug('TransitGatewayAttachment with Id={} does not exist. Ignore'.format(attachment_id))
        return

    current_state = resp['TransitGatewayVpcAttachments'][0]['State']
    if current_state == 'deleted':
        logger.info('TransitGatewayAttachment {} already deleted'.format(attachment_id))
        return
    logger.debug('Deleting TransitGatewayAttachment {id} with state={state}'.format(id=attachment_id, state=current_state))

    resp = ec2_client.delete_transit_gateway_vpc_attachment(TransitGatewayAttachmentId=attachment_id)
    if resp['TransitGatewayVpcAttachment']['State'] != 'deleted':
        # wait until state is 'deleted'
        wait_attachment_state(ec2_client, attachment_id, 'deleted')


@helper.update
def update_resource(event, _):
    logger.debug('Event: {0}'.format(json.dumps(event)))
    logger.info('Not yet implement')


def lambda_handler(event, context):
    helper(event, context)
