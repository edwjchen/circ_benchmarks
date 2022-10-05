import boto3
import json
import os
import multiprocessing
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


def create_west_instance(instance_type):
    print("Creating west instance")
    instance = ec2_west.create_instances(ImageId="ami-0c09c7eb16d3e8e70",
                                         InstanceType=instance_type,
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


def create_east1_instance(instance_type):
    print("Creating east1 instance")
    instance = ec2_east1.create_instances(ImageId="ami-0149b2da6ceec4bb0",
                                          InstanceType=instance_type,
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


def create_east2_instance(instance_type):
    print("Creating east2 instance")
    instance = ec2_east2.create_instances(ImageId="ami-0d5bf08bc8017c83b",
                                          InstanceType=instance_type,
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


def filter_compile_instances(instances):
    return [i for i in instances if i[0].instance_type == compile_instance_type]


def filter_run_instances(instances):
    return [i for i in instances if i[0].instance_type == run_instance_type]


def get_compile_instance():
    stopped_instances = [(i, "aws-west") for i in list(ec2_west.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]))] + \
        [(i, "aws-east") for i in list(ec2_east2.instances.filter(
            Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]))] + \
        [(i, "aws-virg") for i in list(ec2_east1.instances.filter(
            Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]))]

    stopped_compile_instances = filter_compile_instances(stopped_instances)

    if len(stopped_compile_instances):
        instance = stopped_compile_instances[0][0]
        print("Starting compile instances")
        instance.start()
        instance.wait_until_running()
        instance.load()
        return stopped_compile_instances[0]
    else:
        try:
            instance = create_west_instance(compile_instance_type)
            return (instance, "aws-west")
        except:
            print("Failed to create west instance")

        try:
            instance = create_east1_instance(compile_instance_type)
            return (instance, "aws-virg")
        except:
            print("Failed to create east1 instance")

        try:
            instance = create_east2_instance(compile_instance_type)
            return (instance, "aws-east")
        except:
            print("Failed to create east2 instance")


def get_run_instances(run_env):
    print(run_env, "SETTING")
    if run_env == LAN:
        stopped_east1_instances = filter_run_instances([(i, "aws-virg") for i in list(ec2_east1.instances.filter(
            Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]))])
        stopped_east2_instances = filter_run_instances([(i, "aws-east") for i in list(ec2_east2.instances.filter(
            Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]))])

        if len(stopped_east1_instances) >= 1 and len(stopped_east2_instances) >= 1:
            print("Starting run instances")
            east1_instance = stopped_east1_instances[0]
            east2_instance = stopped_east2_instances[0]
            east1_instance[0].start()
            east2_instance[0].start()
            east1_instance[0].wait_until_running()
            east2_instance[0].wait_until_running()
            east1_instance[0].load()
            east2_instance[0].load()
            return (east1_instance, east2_instance)
        else:
            try:
                instance1 = create_east1_instance(run_instance_type)
                east1_instance = (instance1, "aws-virg")
            except:
                print("Failed to create east1 instance")
                exit(0)

            try:
                instance2 = create_east2_instance(run_instance_type)
                east2_instance = (instance2, "aws-east")
            except:
                print("Failed to create east2 instance")
                exit(0)
            return (east1_instance, east2_instance)
    else:
        stopped_west_instances = filter_run_instances([(i, "aws-west") for i in list(ec2_west.instances.filter(
            Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]))])
        stopped_east2_instances = filter_run_instances([(i, "aws-east") for i in list(ec2_east2.instances.filter(
            Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]))])

        if len(stopped_west_instances) >= 1 and len(stopped_east2_instances) >= 1:
            print("Starting run instances")
            west_instance = stopped_west_instances[0]
            east2_instance = stopped_east2_instances[0]
            west_instance[0].start()
            east2_instance[0].start()
            west_instance[0].wait_until_running()
            east2_instance[0].wait_until_running()
            west_instance[0].load()
            east2_instance[0].load()
            return (west_instance, east2_instance)
        else:
            try:
                instance1 = create_west_instance(run_instance_type)
                west_instance = (instance1, "aws-virg")
            except:
                print("Failed to create east1 instance")
                exit(0)

            try:
                instance2 = create_east2_instance(run_instance_type)
                east2_instance = (instance2, "aws-east")
            except:
                print("Failed to create east2 instance")
                exit(0)
            return (west_instance, east2_instance)


def connect_to_instance(ip, k):
    # Connect to ec2 instance
    print("Connecting to ip:", ip)
    key = paramiko.Ed25519Key.from_private_key_file("{}.pem".format(k))
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
    return client


def setup_hycc(ip, k):
    # setup HyCC on ec2 instance
    client = connect_to_instance(ip, k)
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
    client.close()


def compile_hycc(ip, k):
    client = connect_to_instance(ip, k)
    cmd = "cd ~/circ_benchmarks && python3 driver.py --compile_with_params"
    print("Compiling:", cmd)
    _, stdout, stderr = client.exec_command(cmd)
    print("\n".join(stderr.readlines()))
    if stdout.channel.recv_exit_status():
        print(stderr)
        print(ip, " failed compiles")
    print("Compiled:", ip)
    client.close()


def compile_hycc_test(params):
    # get compile instance
    (instance, k) = get_compile_instance()
    ip = instance.public_dns_name
    print("instance:", instance)
    print("key:",  k)
    print("ip:", ip)

    # setup hycc
    setup_hycc(ip, k)

    # write compile params to file
    print("Writing compile params: ", params)
    with open("compile_params.json", "w") as f:
        json.dump(params, f)
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i {}.pem\" --progress compile_params.json ubuntu@{}:~/circ_benchmarks/.".format(k, ip), shell=True)
    print("Finished writing compile params: ", ip)

    # compile hycc
    compile_hycc(ip, k)

    # select hycc

    # get results
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i {}.pem\" --progress ubuntu@{}:~/circ_benchmarks/hycc_circuit_dir .".format(k, ip), shell=True)
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i {}.pem\" --progress ubuntu@{}:~/circ_benchmarks/test_results .".format(k, ip), shell=True)

    # stop instance
    print("Stopping instance")
    instance.stop()
    instance.wait_until_stopped()
    print("Finished!")


def select_hycc(ip, k):
    client = connect_to_instance(ip, k)
    cmd = "cd ~/circ_benchmarks && python3 driver.py --select_with_params"
    print("Selecting:", cmd)
    _, stdout, stderr = client.exec_command(cmd)
    print("\n".join(stderr.readlines()))
    if stdout.channel.recv_exit_status():
        print(stderr)
        print(ip, " failed compiles")
    print("Selected:", ip)
    client.close()


def run_hycc(ip, k):
    client = connect_to_instance(ip, k)
    print("Running HyCC benchmark:\nip:", ip)
    cmd = "cd ~/circ_benchmarks/ && python3 driver.py --run_with_params"
    _, stdout, _ = client.exec_command(cmd)
    if stdout.channel.recv_exit_status():
        print(ip, " failed running benchmark")
    print("Ran benchmark:", cmd)
    client.close()


def run_hycc_test(params):
    run_env = params["setting"]

    # get run instances
    ((instance1, k1), (instance2, k2)) = get_run_instances(run_env)
    ip1 = instance1.public_dns_name
    ip2 = instance2.public_dns_name
    print("instance1:", instance1)
    print("key1:",  k1)
    print("ip1:", ip1)
    print("instance2:", instance2)
    print("key2:",  k2)
    print("ip2:", ip2)

    server_params = params.copy()
    client_params = params.copy()

    # instance1 is the server
    server_params["role"] = 0
    server_params["address"] = instance1.private_ip_address
    server_params["setting"] = run_env
    client_params["role"] = 1
    client_params["address"] = instance1.public_dns_name
    client_params["setting"] = run_env

    # setup hycc
    ips = [ip1, ip2]
    ks = [k1, k2]
    pool = multiprocessing.Pool(len(ips))
    pool.starmap(setup_hycc, zip(ips, ks))

    # write run params to file
    print("Writing server params: ", server_params)
    with open("run_params.json", "w") as f:
        json.dump(server_params, f)
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i {}.pem\" --progress run_params.json ubuntu@{}:~/circ_benchmarks/.".format(k1, ip2), shell=True)
    print("Finished writing server params: ", ip1)

    print("Writing client params: ", client_params)
    with open("run_params.json", "w") as f:
        json.dump(client_params, f)
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i {}.pem\" --progress run_params.json ubuntu@{}:~/circ_benchmarks/.".format(k2, ip2), shell=True)
    print("Finished writing run params: ", ip2)

    # select test case
    pool = multiprocessing.Pool(len(ips))
    pool.starmap(select_hycc, zip(ips, ks))

    # run test case
    pool = multiprocessing.Pool(len(ips))
    pool.starmap(run_hycc, zip(ips, ks))

    # get results
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i {}.pem\" --progress ubuntu@{}:~/circ_benchmarks/run_test_results east1/".format(k1, ip1), shell=True)
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i {}.pem\" --progress ubuntu@{}:~/circ_benchmarks/run_test_results east2/".format(k2, ip2), shell=True)

    # stop instances
    print("Stopping instance")
    instance1.stop()
    instance2.stop()
    instance1.wait_until_stopped()
    instance2.wait_until_stopped()
    print("Finished!")


biomatch_compile_params = [
    {
        "name": "biomatch",
        "path": "biomatch/biomatch.c",
        "mt": 0,
        "a": ["--all-variants"],
    },
    {
        "name": "biomatch_outline",
        "path": "biomatch_outline/biomatch.c",
        "mt": 0,
        "a": ["--all-variants", "--outline"],
    },
    {
        "name": "biomatch",
        "path": "biomatch/biomatch.c",
        "mt": 600,
        "a": ["--all-variants"],
    },
    {
        "name": "biomatch_outline",
        "path": "biomatch_outline/biomatch.c",
        "mt": 600,
        "a": ["--all-variants", "--outline"],
    },
]

biomatch_run_params = [
    {
        "setting": LAN,
        "ss": "yaohybrid",
        "cm": "lan"
    },
    {
        "setting": LAN,
        "ss": "lan_optimized",
        "cm": "lan"
    },
    {
        "setting": WAN,
        "ss": "yaohybrid",
        "cm": "wan"
    },
    {
        "setting": WAN,
        "ss": "wan_optimized",
        "cm": "wan"
    },
]

kmeans_compile_params = [
    {
        "name": "kmeans",
        "path": "kmeans/kmeans.c",
        "mt": 0,
        "a": ["--all-variants"],
    },
    {
        "name": "kmeans_outline",
        "path": "kmeans_outline/kmeans.c",
        "mt": 0,
        "a": ["--all-variants", "--outline"],
    },
    {
        "name": "kmeans",
        "path": "kmeans/kmeans.c",
        "mt": 600,
        "a": ["--all-variants"],
    },
    {
        "name": "kmeans_outline",
        "path": "kmeans_outline/kmeans.c",
        "mt": 600,
        "a": ["--all-variants", "--outline"],
    },
]

gauss_compile_params = [
    {
        "name": "gauss",
        "path": "gauss/gauss.c",
        "mt": 0,
        "a": ["--all-variants"],
    },
    {
        "name": "gauss_outline",
        "path": "gauss_outline/gauss.c",
        "mt": 0,
        "a": ["--all-variants", "--outline"],
    },
    {
        "name": "gauss",
        "path": "gauss/gauss.c",
        "mt": 600,
        "a": ["--all-variants"],
    },
    {
        "name": "gauss_outline",
        "path": "gauss_outline/gauss.c",
        "mt": 600,
        "a": ["--all-variants", "--outline"],
    },
]


run_hycc_test((biomatch_compile_params[0] | biomatch_run_params[0]))
# run_hycc_test({}, WAN)
