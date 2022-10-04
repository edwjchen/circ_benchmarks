import boto3
import json
import os
import multiprocessing
from matplotlib.font_manager import json_dump
import paramiko
import subprocess
import sys
import time

# instance_type = "t2.micro"
# instance_type = "c5.large"
compile_instance_type = "c6a.16xlarge"
run_instance_type = "r5.xlarge"

LAN = "LAN"
WAN = "WAN"

ec2_east1 = boto3.resource("ec2",
                           aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
                           aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
                           region_name="us-east-1")
ec2_east2 = boto3.resource("ec2",
                           aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
                           aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
                           region_name="us-east-2")
ec2_west = boto3.resource("ec2",
                          aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
                          aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
                          region_name="us-west-2")


def create_west_compile_instance():
    print("Creating west instance")
    instance = ec2_west.create_instances(ImageId="ami-0c09c7eb16d3e8e70",
                                         InstanceType=compile_instance_type,
                                         KeyName="aws-west",
                                         MinCount=1,
                                         MaxCount=1,
                                         Monitoring={
                                             "Enabled": False},
                                         SecurityGroups=[
                                             "circ4mpc"
                                         ],
                                         BlockDeviceMappings=[
                                             {
                                                 'DeviceName': '/dev/sda1',
                                                 'Ebs': {
                                                     'DeleteOnTermination': True,
                                                     'VolumeSize': 32,
                                                     'VolumeType': 'gp2',
                                                 }
                                             },
                                         ]
                                         )[0]
    instance.wait_until_running()
    instance.load()
    return instance


def create_east1_compile_instance():
    print("Creating east1 instance")
    instance = ec2_east1.create_instances(ImageId="ami-0149b2da6ceec4bb0",
                                          InstanceType=compile_instance_type,
                                          KeyName="aws-virg",
                                          MinCount=1,
                                          MaxCount=1,
                                          Monitoring={
                                              "Enabled": False},
                                          SecurityGroups=[
                                              "circ4mpc"
                                          ],
                                          BlockDeviceMappings=[
                                              {
                                                  'DeviceName': '/dev/sda1',
                                                  'Ebs': {
                                                      'DeleteOnTermination': True,
                                                      'VolumeSize': 32,
                                                      'VolumeType': 'gp2',
                                                  }
                                              },
                                          ]
                                          )[0]
    instance.wait_until_running()
    instance.load()
    return instance


def create_east2_compile_instance():
    print("Creating east2 instance")
    instance = ec2_east2.create_instances(ImageId="ami-0d5bf08bc8017c83b",
                                          InstanceType=compile_instance_type,
                                          KeyName="aws-east",
                                          MinCount=1,
                                          MaxCount=1,
                                          Monitoring={
                                              "Enabled": False},
                                          SecurityGroups=[
                                              "circ4mpc"
                                          ],
                                          BlockDeviceMappings=[
                                              {
                                                  'DeviceName': '/dev/sda1',
                                                  'Ebs': {
                                                      'DeleteOnTermination': True,
                                                      'VolumeSize': 32,
                                                      'VolumeType': 'gp2',
                                                  }
                                              },
                                          ]
                                          )[0]
    instance.wait_until_running()
    instance.load()
    return instance


def get_compile_instance():
    stopped_instances = [(i, "aws-west") for i in list(ec2_west.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]))] + \
        [(i, "aws-east") for i in list(ec2_east2.instances.filter(
            Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]))] + \
        [(i, "aws-virg") for i in list(ec2_east1.instances.filter(
            Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]))]

    stopped_compile_instances = [
        i for i in stopped_instances if i[0].instance_type == compile_instance_type]

    if len(stopped_compile_instances):
        instance = stopped_compile_instances[0][0]
        print("Starting instance")
        instance.start()
        instance.wait_until_running()
        instance.load()
        return stopped_compile_instances[0]
    else:
        try:
            instance = create_west_compile_instance()
            return (instance, "aws-west")
        except:
            print("Failed to create west instance")

        try:
            instance = create_east1_compile_instance()
            return (instance, "aws-virg")
        except:
            print("Failed to create east1 instance")

        try:
            instance = create_east2_compile_instance()
            return (instance, "aws-east")
        except:
            print("Failed to create east2 instance")


def compile_hycc_test(test_name, test_path, minimization_time, arguments):
    params = {
        "name": test_name,
        "path": test_path,
        "mt": minimization_time,
        "a": arguments,
    }

    # get compile instance
    (instance, k) = get_compile_instance()
    print("instance:", instance)
    print("key:",  k)

    # Connect to ec2 instance
    key = paramiko.Ed25519Key.from_private_key_file("{}.pem".format(k))
    ip = instance.public_dns_name
    print("ip:", ip)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    retry = 0
    while retry < 5:
        try:
            client.connect(hostname=ip,
                           username="ubuntu", pkey=key)
            break
        except:
            time.sleep(5)
            retry += 1
            print("retry:", retry)

    if retry == 5:
        sys.exit("could not connect to ec2 instance")
    else:
        print("Connected to:", ip)

    # setup HyCC on ec2 instance
    _, stdout, _ = client.exec_command("cd ~/circ_benchmarks")
    print("Setting up:", ip)
    if stdout.channel.recv_exit_status():
        _, stdout, _ = client.exec_command(
            "cd ~ && git clone https://github.com/edwjchen/circ_benchmarks.git && cd ~/circ_benchmarks && git checkout aws2 -f && git add . && git stash && git pull -f && git submodule init && git submodule update && ./scripts/dependencies.sh && pip3 install pandas && python3 driver.py -f hycc && python3 driver.py -b")
        if stdout.channel.recv_exit_status():
            print(ip, " failed setup")
    else:
        _, stdout, _ = client.exec_command(
            "cd ~/circ_benchmarks && git checkout aws2 -f && git add . && git stash && git pull -f && git submodule init && git submodule update && ./scripts/dependencies.sh && pip3 install pandas && python3 driver.py -f hycc && python3 driver.py -b")
        if stdout.channel.recv_exit_status():
            print(ip, " failed setup 2")
    print("Set up:", ip)

    # Write compile params to file
    print("Writing compile params: ", params)
    with open("compile_params.json", "w") as f:
        json.dump(params, f)
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i {}.pem\" --progress compile_params.json ubuntu@{}:~/circ_benchmarks/.".format(k, ip), shell=True)
    print("Finished writing compile params: ", ip)

    # Compile test case
    cmd = "cd ~/circ_benchmarks && python3 driver.py --compile_with_params"
    print("Compiling:", cmd)
    _, stdout, stderr = client.exec_command(cmd)
    print("\n".join(stderr.readlines()))
    if stdout.channel.recv_exit_status():
        print(stderr)
        print(ip, " failed compiles")
    print("Compiled:", ip)

    # close client
    client.close()

    # scp compiled hycc_circuit_dir & test_results to local directory
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i {}.pem\" --progress ubuntu@{}:~/circ_benchmarks/hycc_circuit_dir .".format(k, ip), shell=True)
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i {}.pem\" --progress ubuntu@{}:~/circ_benchmarks/test_results .".format(k, ip), shell=True)

    # stop instance
    print("Stopping instance")
    instance.stop()
    instance.wait_until_stopped()
    print("Finished!")


# # compile biomatch testcases
# compile_hycc_test("biomatch",
#                   "biomatch/biomatch.c", 0, ["--all-variants"])
# compile_hycc_test("biomatch_outline",
#                   "biomatch_outline/biomatch.c", 0, ["--all-variants", "--outline"])
# compile_hycc_test("biomatch",
#                   "biomatch/biomatch.c", 600, ["--all-variants"])
# compile_hycc_test("biomatch_outline",
#                   "biomatch_outline/biomatch.c", 600, ["--all-variants", "--outline"])

# # compile kmeans testcases
# compile_hycc_test("kmeans",
#                   "kmeans/kmeans.c", 0, ["--all-variants"])
# compile_hycc_test("kmeans_outline",
#                   "kmeans_outline/kmeans.c", 0, ["--all-variants", "--outline"])
# compile_hycc_test("kmeans",
#                   "kmeans/kmeans.c", 600, ["--all-variants"])
# compile_hycc_test("kmeans_outline",
#                   "kmeans_outline/kmeans.c", 600, ["--all-variants", "--outline"])

# # compile gauss testcases
# compile_hycc_test("gauss",
#                   "gauss/gauss.c", 0, ["--all-variants"])
# compile_hycc_test("gauss_outline",
#                   "gauss_outline/gauss.c", 0, ["--all-variants", "--outline"])
# compile_hycc_test("gauss",
#                   "gauss/gauss.c", 600, ["--all-variants"])
# compile_hycc_test("gauss_outline",
#                   "gauss_outline/gauss.c", 600, ["--all-variants", "--outline"])

# # Select
# cmd = "cd ~/circ_benchmarks && python3 driver.py --select_with_params"
# print("Selecting:", cmd)
# _, stdout, stderr = client.exec_command(cmd)
# print("\n".join(stderr.readlines()))
# if stdout.channel.recv_exit_status():
#     print(stderr)
#     print(ip, " failed selecting")
# print("Selected:", ip)


def create_instances():
    # # create two AWS East Instances if they haven't been made
    # all_instances = []
    # instances = list(ec2_east.instances.filter(
    #     Filters=[{"Name": "instance-state-name", "Values": ["stopping", "pending", "running", "stopped"]}]))
    # num_instances_to_create = max(0, 2 - len(instances))
    # if num_instances_to_create > 0:
    #     all_instances += ec2_east.create_instances(ImageId="ami-05b63781e32145c7f",
    #                               InstanceType=instance_type,
    #                               KeyName="aws-east",
    #                               MinCount=1,
    #                               MaxCount=num_instances_to_create,
    #                               Monitoring={
    #                                   "Enabled": False},
    #                               SecurityGroups=[
    #                                   "circ4mpc"]
    #                               )

    # print("Created {} east instances".format(num_instances_to_create))

    # create one AWS West Instance if they haven't been made
    instance = ec2_west.create_instances(ImageId="ami-0ddf424f81ddb0720",
                                         InstanceType=run_instance_type,
                                         KeyName="aws-west",
                                         MinCount=1,
                                         MaxCount=1,
                                         Monitoring={
                                             "Enabled": False},
                                         SecurityGroups=[
                                             "circ4mpc"]
                                         )[0]
    print("Created {} west instances".format(1))

    # stop instances created
    instance.wait_until_running()
    instance.load()
    print("ssh -i aws-west.pem ubuntu@{}".format(instance.public_dns_name))


# def start_instances():
#     stopped_instances = list(ec2_east.instances.filter(
#         Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]))
#     count = 0
#     num = len(stopped_instances)
#     for i in range(num):
#         instance = stopped_instances[i]
#         ec2_east.instances.filter(InstanceIds=[instance.id]).start()
#         count += 1
#     print("Started {} East instances".format(count))

#     stopped_instances = list(ec2_west.instances.filter(
#         Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]))
#     count = 0
#     num = len(stopped_instances)
#     for i in range(num):
#         instance = stopped_instances[i]
#         ec2_west.instances.filter(InstanceIds=[instance.id]).start()
#         count += 1
#     print("Started {} West instances".format(count))


def stop_instances():
    running_instances = list(ec2_east.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]))
    count = 0
    num = len(running_instances)
    for i in range(num):
        instance = running_instances[i]
        print("Stopping", instance.public_dns_name)
        ec2_east.instances.filter(InstanceIds=[instance.id]).stop()
        count += 1
    print("Stopped {} East instances".format(count))

    running_instances = list(ec2_west.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]))
    count = 0
    num = len(running_instances)
    for i in range(num):
        instance = running_instances[i]
        print("Stopping", instance.public_dns_name)
        ec2_west.instances.filter(InstanceIds=[instance.id]).stop()
        count += 1
    print("Stopped {} West instances".format(count))


def terminate_instances():
    instances = list(ec2_east.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["running", "stopped"]}]))
    count = 0
    num = len(instances)
    for i in range(num):
        instance = instances[i]
        count += 1
        ec2_east.instances.filter(InstanceIds=[instance.id]).terminate()
    print("Terminated {} East instances".format(count))

    instances = list(ec2_west.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["running", "stopped"]}]))
    count = 0
    num = len(instances)
    for i in range(num):
        instance = instances[i]
        count += 1
        ec2_west.instances.filter(InstanceIds=[instance.id]).terminate()
    print("Terminated {} West instances".format(count))


def print_stats(ec2_resource):
    stats = {}
    stats["total"] = len(list(ec2_resource.instances.filter(Filters=[
        {"Name": "instance-state-name", "Values": ["running", "stopped", "pending", "stopping"]}])))
    stats["running"] = len(list(ec2_resource.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}])))
    stats["stopped"] = len(list(ec2_resource.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}])))
    stats["pending"] = len(list(ec2_resource.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["pending"]}])))
    stats["stopping"] = len(list(ec2_resource.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["stopping"]}])))
    print(json.dumps(stats, indent=4))


def stats(setting):
    if setting == LAN:
        print("==== LAN ====")
        print("East:")
        print_stats(ec2_east)
    elif setting == WAN:
        print("==== WAN ====")
        print("East:")
        print_stats(ec2_east)
        print("West:")
        print_stats(ec2_west)


def hosts():
    running_east_instances = list(ec2_east.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]))
    running_east_instance_ips = [
        instance.public_dns_name for instance in running_east_instances]
    for ip in running_east_instance_ips:
        print("ssh -i \"aws-east.pem\" ubuntu@{}".format(ip))

    running_west_instances = list(ec2_west.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]))
    running_west_instance_ips = [
        instance.public_dns_name for instance in running_west_instances]
    for ip in running_west_instance_ips:
        print("ssh -i \"aws-west.pem\" ubuntu@{}".format(ip))


def setup_instances():
    stopped_instances = []
    keys = []

    stopped_east_instances = list(ec2_east.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]))
    stopped_instances += stopped_east_instances
    keys += ["aws-east.pem" for _ in stopped_east_instances]

    stopped_west_instances = list(ec2_west.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]))
    stopped_instances += stopped_west_instances
    keys += ["aws-west.pem" for _ in stopped_east_instances]

    for instance, key in zip(stopped_instances, keys):
        print("Setting up:")
        instance.start()
        instance.wait_until_running()
        instance.load()
        setup_worker(instance.public_dns_name, key)
        instance.stop()
        instance.wait_until_stopped()
        print("Stopped instance")


def setup_worker(ip, key_file):
    print("ip:", ip, "\nkey:", key_file)
    key = paramiko.Ed25519Key.from_private_key_file(key_file)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    retry = 0
    while retry < 5:
        try:
            client.connect(hostname=ip, username="ubuntu", pkey=key)
            break
        except:
            time.sleep(5)
            retry += 1
            print("retry:", retry)

    print("Connected to:", ip)
    _, stdout, _ = client.exec_command("cd ~/circ_benchmarks")
    if stdout.channel.recv_exit_status():
        _, stdout, _ = client.exec_command(
            "cd ~ && git clone https://github.com/edwjchen/circ_benchmarks.git && cd ~/circ_benchmarks && git checkout aws -f && git add . && git stash && git pull -f &&./scripts/dependencies.sh && pip3 install pandas && python3 driver.py -f hycc && python3 driver.py -b")
        if stdout.channel.recv_exit_status():
            print(ip, " failed setup")
    else:
        _, stdout, _ = client.exec_command(
            "cd ~/circ_benchmarks && git checkout aws -f && git add . && git stash && git pull -f && ./scripts/dependencies.sh && pip3 install pandas && python3 driver.py -f hycc && python3 driver.py -b")
        if stdout.channel.recv_exit_status():
            print(ip, " failed setup 2")

    print("Set up:", ip)
    client.close()


def refresh_instances():
    running_instance_ips = []
    keys = []
    running_east_instances = list(ec2_east.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]))
    running_east_instance_ips = [
        instance.public_dns_name for instance in running_east_instances]
    running_instance_ips += running_east_instance_ips
    keys += ["aws-east.pem" for _ in running_east_instance_ips]

    running_west_instances = list(ec2_west.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]))
    running_west_instance_ips = [
        instance.public_dns_name for instance in running_west_instances]
    running_instance_ips += running_west_instance_ips
    keys += ["aws-west.pem" for _ in running_west_instance_ips]

    pool = multiprocessing.Pool(len(running_instance_ips))
    pool.starmap(refresh_worker, zip(running_instance_ips, keys))


def refresh_worker(ip, key_file):
    print("Refreshing: {}".format(ip))
    key = paramiko.Ed25519Key.from_private_key_file(key_file)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=ip, username="ubuntu", pkey=key)

    root = "~/circ_benchmarks/modules/"
    _, stdout, _ = client.exec_command(
        "cd {}ABY && git pull && cd {}circ && git pull && cd {}HyCC && git pull".format(root, root, root))

    if stdout.channel.recv_exit_status():
        print(ip, " failed to refresh")

    client.close()


def compile_benchmarks():
    # start west instance
    stopped_instances = list(ec2_west.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]))
    stopped_instances = [
        i for i in stopped_instances if i.instance_type == instance_type]
    count = 0
    num = len(stopped_instances)
    for i in range(num):
        instance = stopped_instances[i]
        print("Starting instance")
        instance.start()
        instance.wait_until_running()
        instance.load()
        count += 1
    print("Started {} West instances".format(count))

    # compile on west instance
    running_west_instances = list(ec2_west.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]))
    running_west_instances = [
        i for i in running_west_instances if i.instance_type == instance_type]
    ip = [instance.public_dns_name for instance in running_west_instances][0]
    id = [instance.id for instance in running_west_instances][0]
    key = paramiko.Ed25519Key.from_private_key_file("aws-west.pem")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    retry = 0
    while retry < 5:
        try:
            client.connect(hostname=ip, username="ubuntu", pkey=key)
            break
        except:
            time.sleep(5)
            retry += 1
            print("retry:", retry)
    print("connected to:", ip)

    # cmd = "cd ~/circ_benchmarks && git checkout aws -f && git pull && python3 driver.py -f hycc circ && python3 driver.py --compile"
    cmd = "cd ~/circ_benchmarks && git checkout aws -f && git add . && git stash && git pull -f && python3 driver.py -f hycc && python3 driver.py --compile"
    print("Running:", cmd)
    _, stdout, stderr = client.exec_command(cmd)
    print("\n".join(stderr.readlines()))
    if stdout.channel.recv_exit_status():
        print(stderr)
        print(ip, " failed compiles")

    print("Compiled:", ip)
    client.close()

    # scp compiled hycc_circuit_dir & test_results to local directory
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i aws-west.pem\" --progress ubuntu@{}:~/circ_benchmarks/hycc_circuit_dir .".format(ip), shell=True)
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i aws-west.pem\" --progress ubuntu@{}:~/circ_benchmarks/circ_circuit_dir .".format(ip), shell=True)
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i aws-west.pem\" --progress ubuntu@{}:~/circ_benchmarks/test_results .".format(ip), shell=True)

    # stop west instance
    print("Stopping west instance")
    running_west_instances[0].stop()
    running_west_instances[0].wait_until_stopped()
    print("Stopped west instance")


def select_benchmarks():
    # start west instance
    stopped_instances = list(ec2_west.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]))
    stopped_instances = [
        i for i in stopped_instances if i.instance_type == instance_type]
    count = 0
    num = len(stopped_instances)
    for i in range(num):
        instance = stopped_instances[i]
        print("Starting instance")
        instance.start()
        instance.wait_until_running()
        instance.load()
        count += 1
    print("Started {} West instances".format(count))

    # compile on west instance
    running_west_instances = list(ec2_west.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]))
    running_west_instances = [
        i for i in running_west_instances if i.instance_type == instance_type]
    ip = [instance.public_dns_name for instance in running_west_instances][0]
    id = [instance.id for instance in running_west_instances][0]
    key = paramiko.Ed25519Key.from_private_key_file("aws-west.pem")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    retry = 0
    while retry < 5:
        try:
            client.connect(hostname=ip, username="ubuntu", pkey=key)
            break
        except:
            time.sleep(5)
            retry += 1
            print("retry:", retry)
    print("connected to:", ip)

    cmd = "cd ~/circ_benchmarks && git checkout aws -f && git add . && git stash && git pull -f && python3 driver.py -f hycc && python3 driver.py --select"
    print("Running:", cmd)
    _, stdout, stderr = client.exec_command(cmd)
    print("\n".join(stderr.readlines()))
    if stdout.channel.recv_exit_status():
        print(stderr)
        print(ip, " failed compiles")

    print("Compiled:", ip)
    client.close()

    # scp compiled hycc_circuit_dir & test_results to local directory
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i aws-west.pem\" --progress ubuntu@{}:~/circ_benchmarks/hycc_circuit_dir .".format(ip), shell=True)
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i aws-west.pem\" --progress ubuntu@{}:~/circ_benchmarks/circ_circuit_dir .".format(ip), shell=True)
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i aws-west.pem\" --progress ubuntu@{}:~/circ_benchmarks/test_results .".format(ip), shell=True)

    # stop west instance
    # print("Stopping west instance")
    # running_west_instances[0].stop()
    # running_west_instances[0].wait_until_stopped()
    # print("Stopped west instance")


def compile_scp_worker(ip, id):
    print("ip:", ip, "\nid:", id)
    key = paramiko.Ed25519Key.from_private_key_file("aws-east.pem")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=ip, username="ubuntu", pkey=key)
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i aws-east.pem\" --progress ./hycc_circuit_dir/ ubuntu@{}:~/circ_benchmarks/hycc_circuit_dir".format(ip), shell=True)
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i aws-east.pem\" --progress ./circ_circuit_dir/ ubuntu@{}:~/circ_benchmarks/circ_circuit_dir".format(ip), shell=True)
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i aws-east.pem\" --progress ./test_results/ ubuntu@{}:~/circ_benchmarks/test_results".format(ip), shell=True)

    print("SCP'd:", ip)
    client.close()


def run_benchmarks(setting):
    if setting == LAN:
        running_east_instances = list(ec2_east.instances.filter(
            Filters=[{"Name": "instance-state-name", "Values": ["running"]}]))
        assert(len(running_east_instances) == 2)

        ips = [i.public_dns_name for i in running_east_instances]
        server_private_ip = running_east_instances[0].private_ip_address
        server_public_ip = running_east_instances[0].public_ip_address
        connect_ips = [server_private_ip, server_public_ip]
        roles = [0, 1]
        keys = ["aws-east.pem", "aws-east.pem"]

        pool = multiprocessing.Pool(len(ips))
        pool.starmap(benchmark_hycc_worker, zip(
            ips, connect_ips, roles, keys))

        pool = multiprocessing.Pool(len(ips))
        pool.starmap(benchmark_circ_worker, zip(
            ips, connect_ips, roles, keys))

    elif setting == WAN:
        running_east_instances = list(ec2_east.instances.filter(
            Filters=[{"Name": "instance-state-name", "Values": ["running"]}]))
        assert(len(running_east_instances) == 1)
        running_west_instances = list(ec2_west.instances.filter(
            Filters=[{"Name": "instance-state-name", "Values": ["running"]}]))
        assert(len(running_west_instances) == 1)

        ips = [running_east_instances[0].public_dns_name,
               running_west_instances[0].public_dns_name]
        server_private_ip = running_east_instances[0].private_ip_address
        server_public_ip = running_east_instances[0].public_ip_address
        connect_ips = [server_private_ip, server_public_ip]
        roles = [0, 1]
        keys = ["aws-east.pem", "aws-west.pem"]

        pool = multiprocessing.Pool(len(ips))
        pool.starmap(benchmark_hycc_worker, zip(
            ips, connect_ips, roles, keys))

        pool = multiprocessing.Pool(len(ips))
        pool.starmap(benchmark_circ_worker, zip(
            ips, connect_ips, roles, keys))

    # stop all instances
    stop_instances()


def benchmark_worker(ip, connect_ip, role, key_file, setting):
    print("Running HyCC benchmark:\nip: {}\nconnect: {}\nrole: {}\n".format(
        ip, connect_ip, role))
    key = paramiko.Ed25519Key.from_private_key_file(key_file)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=ip, username="ubuntu", pkey=key)

    cmd = "cd ~/circ_benchmarks/ && rm -rf run_test_results && python3 driver.py --address {} && python3 driver.py --role {} && python3 driver.py --setting {} && python3 driver.py -f hycc && python3 driver.py --benchmark".format(
        connect_ip, role, setting)
    _, stdout, _ = client.exec_command(cmd)

    if stdout.channel.recv_exit_status():
        print(ip, " failed running benchmark")

    client.close()


def results():
    # start all instances
    start_instances()
    time.sleep(15)

    running_instances = []
    keys = []

    running_east_instances = list(ec2_east.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]))
    running_instances += running_east_instances
    keys += ["aws-east.pem" for _ in running_east_instances]

    running_west_instances = list(ec2_west.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]))
    running_instances += running_west_instances
    keys += ["aws-west.pem" for _ in running_west_instances]

    running_instances = [
        (instance.public_dns_name, instance.id) for instance in running_instances]

    for (dns_name, id), key in zip(running_instances, keys):
        if not os.path.exists("./aws/{}".format(id)):
            os.makedirs("./aws/{}/".format(id))

        subprocess.call(
            "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i {}\" --progress ubuntu@{}:~/circ_benchmarks/test_results ./aws/{}".format(key, dns_name, id), shell=True)


def setup_run_worker(ip, key_file):
    print("ip:", ip, "\nkey:", key_file)
    key = paramiko.Ed25519Key.from_private_key_file(key_file)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    retry = 0
    while retry < 5:
        try:
            client.connect(hostname=ip, username="ubuntu", pkey=key)
            break
        except:
            time.sleep(5)
            retry += 1
            print("retry:", retry)

    print("Connected to:", ip)
    _, stdout, _ = client.exec_command("cd ~/circ_benchmarks")
    if stdout.channel.recv_exit_status():
        _, stdout, _ = client.exec_command(
            "cd ~ && git clone https://github.com/edwjchen/circ_benchmarks.git && cd ~/circ_benchmarks && git checkout aws -f && ./scripts/dependencies.sh && pip3 install pandas && python3 driver.py -f hycc && python3 driver.py --build_aby")
        if stdout.channel.recv_exit_status():
            print(ip, " failed setup")
    else:
        _, stdout, _ = client.exec_command(
            "cd ~/circ_benchmarks && rm -rf hycc_circuit_dir/*_cm-hycc && git checkout aws -f && git add . && git stash && git pull -f && rm -rf run_test_results && rm -rf east && ./scripts/dependencies.sh && pip3 install pandas && python3 driver.py -f hycc && python3 driver.py --build_aby")
        if stdout.channel.recv_exit_status():
            print(ip, " failed setup 2")
    print("Set up:", ip)
    client.close()


def run_lan():
    print("RUNNING LAN TEST")
    stopped_east_instances = list(ec2_east.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]))
    instances = [
        i for i in stopped_east_instances if i.instance_type == run_instance_type]

    if len(instances) >= 2:
        print("starting instances")
        instances = instances[:2]
        [i.start() for i in instances]
        [i.wait_until_running() for i in instances]
        [i.load() for i in instances]
        print("started {} instances".format(len(instances)))
    else:
        print("creating instances")
        instances = ec2_east.create_instances(ImageId="ami-05b63781e32145c7f",
                                              InstanceType=run_instance_type,
                                              KeyName="aws-east",
                                              MinCount=1,
                                              MaxCount=2,
                                              Monitoring={
                                                  "Enabled": False
                                              },
                                              SecurityGroups=[
                                                  "circ4mpc"
                                              ],
                                              BlockDeviceMappings=[
                                                  {
                                                      'DeviceName': '/dev/sda1',
                                                      'Ebs': {
                                                          'DeleteOnTermination': True,
                                                          'VolumeSize': 128,
                                                          'VolumeType': 'gp2',
                                                      }
                                                  },
                                              ]
                                              )
        [instance.wait_until_running() for instance in instances]
        [instance.load() for instance in instances]
        print("created {} instances".format(len(instances)))

    # install ABY
    ips = [instance.public_dns_name for instance in instances]
    keys = ["aws-east.pem" for _ in instances]
    print("Setting up instances")
    pool = multiprocessing.Pool(len(instances))
    pool.starmap(setup_run_worker, zip(ips, keys))

    # copy test cases to benchmark
    print("Rsync test cases to instances")
    for ip in [i.public_dns_name for i in instances]:
        print("copy to:", ip)
        subprocess.call(
            "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i aws-east.pem\" --progress ./hycc_circuit_dir/ ubuntu@{}:~/circ_benchmarks/hycc_circuit_dir".format(ip), shell=True)
        subprocess.call(
            "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i aws-east.pem\" --progress ./run_test_results/ ubuntu@{}:~/circ_benchmarks/run_test_results".format(ip), shell=True)

    ips = [i.public_dns_name for i in instances]
    server_private_ip = instances[0].private_ip_address
    server_public_ip = instances[0].public_ip_address
    connect_ips = [server_private_ip, server_public_ip]
    roles = [0, 1]
    keys = ["aws-east.pem", "aws-east.pem"]
    settings = ["lan", "lan"]

    print("benchmarking")
    pool = multiprocessing.Pool(len(instances))
    pool.starmap(benchmark_worker, zip(
        ips, connect_ips, roles, keys, settings))

    # scp compiled hycc_circuit_dir & test_results to local directory
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i aws-east.pem\" --progress ubuntu@{}:~/circ_benchmarks/run_test_results .".format(ips[0]), shell=True)

    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i aws-east.pem\" --progress ubuntu@{}:~/circ_benchmarks/run_test_results ./client".format(ips[1]), shell=True)

    print("Stopping instances")
    [instance.stop() for instance in instances]
    [instance.wait_until_stopped() for instance in instances]
    print("done!")


def run_wan():
    print("RUNNING WAN TEST")
    stopped_west_instances = list(ec2_west.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]))
    stopped_east_instances = list(ec2_east.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]))

    # filter instances by type
    stopped_west_instances = [
        i for i in stopped_west_instances if i.instance_type == run_instance_type]
    stopped_east_instances = [
        i for i in stopped_east_instances if i.instance_type == run_instance_type]

    instances = []

    if len(stopped_west_instances) >= 1 and len(stopped_east_instances) >= 1:
        print("starting instances")
        west_instance = stopped_west_instances[0]
        east_instance = stopped_east_instances[0]
        instances = [west_instance, east_instance]
        [i.start() for i in instances]
        [i.wait_until_running() for i in instances]
        [i.load() for i in instances]
        print("started {} instances".format(len(instances)))
    else:
        print("creating 1 west and 1 east instances")

        west_instance = ec2_west.create_instances(ImageId="ami-0ddf424f81ddb0720",
                                                  InstanceType=run_instance_type,
                                                  KeyName="aws-west",
                                                  MinCount=1,
                                                  MaxCount=1,
                                                  Monitoring={
                                                      "Enabled": False},
                                                  SecurityGroups=[
                                                      "circ4mpc"],
                                                  BlockDeviceMappings=[
                                                      {
                                                          'DeviceName': '/dev/sda1',
                                                          'Ebs': {
                                                              'DeleteOnTermination': True,
                                                              'VolumeSize': 128,
                                                              'VolumeType': 'gp2',
                                                          }
                                                      },
                                                  ]
                                                  )
        east_instance = ec2_east.create_instances(ImageId="ami-05b63781e32145c7f",
                                                  InstanceType=run_instance_type,
                                                  KeyName="aws-east",
                                                  MinCount=1,
                                                  MaxCount=1,
                                                  Monitoring={
                                                      "Enabled": False
                                                  },
                                                  SecurityGroups=[
                                                      "circ4mpc"
                                                  ],
                                                  BlockDeviceMappings=[
                                                      {
                                                          'DeviceName': '/dev/sda1',
                                                          'Ebs': {
                                                              'DeleteOnTermination': True,
                                                              'VolumeSize': 128,
                                                              'VolumeType': 'gp2',
                                                          }
                                                      },
                                                  ]
                                                  )
        instances = [west_instance[0], east_instance[0]]
        [instance.wait_until_running() for instance in instances]
        [instance.load() for instance in instances]
        print("created {} instances".format(len(instances)))

    # install ABY
    ips = [instance.public_dns_name for instance in instances]
    keys = ["aws-west.pem", "aws-east.pem"]
    print("Setting up instances")
    pool = multiprocessing.Pool(len(instances))
    pool.starmap(setup_run_worker, zip(ips, keys))

    # copy test cases to benchmark
    print("Rsync test cases to instances")
    for ip, key in zip([i.public_dns_name for i in instances], ["aws-west.pem", "aws-east.pem"]):
        print("copy to:", ip)
        subprocess.call(
            "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i {}\" --progress ./hycc_circuit_dir/ ubuntu@{}:~/circ_benchmarks/hycc_circuit_dir".format(key, ip), shell=True)
        subprocess.call(
            "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i {}\" --progress ./circ_circuit_dir/ ubuntu@{}:~/circ_benchmarks/circ_circuit_dir".format(key, ip), shell=True)
        subprocess.call(
            "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i {}\" --progress ./run_test_results/ ubuntu@{}:~/circ_benchmarks/run_test_results".format(key, ip), shell=True)

    ips = [i.public_dns_name for i in instances]
    server_private_ip = instances[0].private_ip_address
    server_public_ip = instances[0].public_ip_address
    connect_ips = [server_private_ip, server_public_ip]
    roles = [0, 1]
    settings = ["wan", "wan"]

    print("benchmarking")
    pool = multiprocessing.Pool(len(instances))
    pool.starmap(benchmark_worker, zip(
        ips, connect_ips, roles, keys, settings))

    # scp compiled hycc_circuit_dir & test_results to local directory
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i aws-west.pem\" --progress ubuntu@{}:~/circ_benchmarks/run_test_results .".format(ips[0]), shell=True)

    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i aws-east.pem\" --progress ubuntu@{}:~/circ_benchmarks/run_test_results ./east".format(ips[1]), shell=True)

    print("Stopping instances")
    [instance.stop() for instance in instances]
    [instance.wait_until_stopped() for instance in instances]
    print("done!")


# if __name__ == "__main__":
#     setting = WAN  # default test setting
#     last_cmd = ""
#     while True:
#         cmds = input("> ").split(" ")
#         cmd_type = cmds[0]

#         # press enter to redo
#         if cmd_type == "" and last_cmd != "":
#             cmd_type = last_cmd
#         else:
#             last_cmd = cmd_type

#         if cmd_type == "help":
#             print("Not again... oh well here you go\n")
#             print("EC2: \tcreate start stop terminate stats")
#             print("Setup: \tsetup refresh")
#             print("Build: \tcompile")
#             print("Run: \trun")
#             print("Res: \tres results")
#             print("AWS: \tstats hosts")
#             print("Set: \tLAN WAN")
#             print("Quit: \tquit q")
#         elif cmd_type == "create":
#             create_instances()
#         elif cmd_type == "start":
#             start_instances()
#         elif cmd_type == "setup":
#             print("=== will stop instances after setup ===")
#             setup_instances()
#         elif cmd_type == "compile":
#             compile_benchmarks()
#         elif cmd_type == "select":
#             select_benchmarks()
#         elif cmd_type == "run":
#             run_benchmarks(setting)
#         elif cmd_type == "stop":
#             stop_instances()
#         elif cmd_type == "terminate":
#             terminate_instances()
#         elif cmd_type == "stats":
#             stats(setting)
#         elif cmd_type == "hosts":
#             hosts()
#         elif cmd_type == "refresh":
#             refresh_instances()
#         elif cmd_type in ["res", "results"]:
#             results()
#         elif cmd_type in ["quit", "q", "exit"]:
#             sys.exit(0)
#         elif cmd_type == LAN:
#             run_lan()
#         elif cmd_type == WAN:
#             run_wan()
#         # elif cmd_type == LAN:
#         #     setting = cmd_type
#         #     print("Operating in: {}".format(setting))
#         #     lan()
#         # elif cmd_type == WAN:
#         #     setting = cmd_type
#         #     print("Operating in: {}".format(setting))
#         #     wan()
#         else:
#             print("unlucky, not a cmd")

#         if cmd_type != "stats":
#             stats(setting)
