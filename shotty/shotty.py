import boto3
import click
import botocore
import sys

session = boto3.Session(profile_name='shotty')
ec2 = session.resource('ec2')

def filter_instances(project):
    instances=[]
    if project:
        filters=[{'Name':'tag:Project','Values':[project]}]
        instances = ec2.instances.filter(Filters=filters)
    else:
        instances = ec2.instances.all()
    return instances

def filter_single_instance(instance):
    instances=[]
    instances = ec2.instances.filter(InstanceIds=[instance])
    return instances

def has_pending_snapshot(volume):
    snapshots = list(volume.snapshots.all())
    return snapshots and snapshots[0].state == 'pending'


@click.group()
def cli():
    """shotty manages snapshots"""

@cli.group('volumes')
def volumes():
    """Commands for volumes"""

@volumes.command('list')
@click.option('--project', default=None,
    help="Only instances for project (tag Project:<name>)")
@click.option('--instance', default=None,
    help="Only instances with spacific id ")
def list_volumes(instance,project):
    """List Volumes"""
    if instance:
        instances= filter_single_instance(instance)
    else:
        instances = filter_instances(project)
    for i in instances:
        for v in i.volumes.all():
            print(', '.join((
            v.id,
            i.id,
            v.state,
            str(v.size) + "GiB",
            v.encrypted and "Encrypted" or "Not Encrypted"
            )))

@cli.group('snapshots')
def snapshots():
    """Command for snapshots"""

@snapshots.command('list')
@click.option('--all', 'list_all', default=False, is_flag=True,
    help="List all snapshots for each volume not just the most recent.")
def list_snapshots(list_all):
    """List Snapshots"""
    instances = filter_instances(project)
    for i in instances:
        for v in i.volumes.all():
            for s in v.snapshots.all():
                print(', '.join((
                    s.id,
                    v.id,
                    i.id,
                    s.state,
                    s.progress,
                    s.start_time.strftime("%c"))))

                if s.state == 'completed' and not list_all: break
    return

@cli.group('instances')
def instances():
    """Commands for instances"""

@instances.command('list')
@click.option('--project', default=None,
    help="Only instances for project (tag Project:<name>)")
def list_instances(project):
    "List EC2 instances"
    instances = filter_instances(project)
    for i in instances:
        print(', '.join((
            i.id,
            i.instance_type,
            i.placement['AvailabilityZone'],
            i.state['Name'],
            i.public_dns_name)))
    return

@instances.command('stop')
@click.option('--force', 'force', default=False, is_flag=True,
    help="Forces running of command if project tag is not set.")
@click.option('--project', default=None,
    help="Only instances for project (tag Project:<name>)")
@click.option('--instance', default=None,
    help="Only instances with spacific id ")
def stop_instances(instance,project,force):
    "Stop Ec2 instances"
    if instance:
        instances= filter_single_instance(instance)
    elif project or force:
        instances = filter_instances(project)
    else:
        raise SystemExit("Instance, Project and Force flags are not set.")

    for i in instances:
        print("Stopping {0}...".format(i.id))
        try:
            i.stop()
        except botocore.exceptions.ClientError as e:
            print("Could not Stop {0}".format(i.id) + str(e))
            continue
    return

@instances.command('start')
@click.option('--force', 'force', default=False, is_flag=True,
    help="Forces running of command if project tag is not set.")
@click.option('--project', default=None,
    help="Only instances for project (tag Project:<name>)")
@click.option('--instance', default=None,
    help="Only instances with spacific id ")
def stop_instances(instance,project,force):
    "Start Ec2 instances"

    if instance:
        instances= filter_single_instance(instance)
    elif project or force:
        instances = filter_instances(project)
    else:
        raise SystemExit("Project and Force flags are not set.")

    for i in instances:
        print("Starting {0}...".format(i.id))
        try:
            i.start()
        except botocore.exceptions.ClientError as e:
            print("Could not Start {0}. ".format(i.id) + str(e))
            continue
    return


@instances.command('snapshot')
@click.option('--force', 'force', default=False, is_flag=True,
    help="Forces running of command if project tag is not set.")
@click.option('--project', default=None,
    help="Only instances for project (tag Project:<name>)")
def snapshot_instances(project,force):
    "Create snapshots for Ec2 instances"

    if project or force:
        instances = filter_instances(project)
    else:
        raise SystemExit("Project and Force flags are not set.")

    for i in instances:
        i.stop()
        i.wait_until_stopped()
        for v in i.volumes.all():
            if has_pending_snapshot(v):
                print("Skipping {0}, snapshot already in progress",format(v.id))
                continue
            print("Creating snapshot of {0}...".format(i.id))
            v.create_snapshot("Created by Snapshotalyzer")
        print("Starting {0}".format(i.id))
        i.start()
        i.wait_until_running()
    print("Job Done...!")
    return

@instances.command('reboot')
@click.option('--force', 'force', default=False, is_flag=True,
    help="Forces running of command if project tag is not set.")
@click.option('--project', default=None,
    help="Only instances for project (tag Project:<name>)")
def reboot_instances(project,force):
    "Reboot Ec2 instances"

    if project or force:
        instances = filter_instances(project)
    else:
        raise SystemExit("Project and Force flags are not set.")

    for i in instances:
        i.wait_until_running()
        print("Rebooting {0}...".format(i.id))
        i.reboot()
    return

@instances.command('tag')
def tag_instances():
    "Tag Ec2 instances"

    instances = filter_instances(project)
    for i in instances:
        i.create_tags(Tags=[{'Key':'Project', 'Value':'niloo-python'}])
        print("Tagging {0}...".format(i.id))
    return


if __name__ == '__main__':
    cli()
