import boto3
import click
import botocore

session = boto3.Session(profile_name='shotty')
ec2 = session.resource('ec2')

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
def list_volumes():
    """List Volumes"""
    for i in ec2.instances.all():
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
    for i in ec2.instances.all():
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
def list_instances():
    "List EC2 instances"
    for i in ec2.instances.all():
        print(', '.join((
            i.id,
            i.instance_type,
            i.placement['AvailabilityZone'],
            i.state['Name'],
            i.public_dns_name)))
    return

@instances.command('stop')
def stop_instances():
    "Stop Ec2 instances"
    for i in ec2.instances.all():
        print("Stopping {0}...".format(i.id))
        try:
            i.stop()
        except botocore.exceptions.ClientError as e:
            print("Could not Stop {0}".format(i.id) + str(e))
            continue
    return

@instances.command('start')
def stop_instances():
    "Start Ec2 instances"
    for i in ec2.instances.all():
        print("Starting {0}...".format(i.id))
        try:
            i.start()
        except botocore.exceptions.ClientError as e:
            print("Could not Start {0}. ".format(i.id) + str(e))
            continue
    return


@instances.command('snapshot')
def snapshot_instances():
    "Create snapshots for Ec2 instances"

    for i in ec2.instances.all():
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

if __name__ == '__main__':

    cli()
