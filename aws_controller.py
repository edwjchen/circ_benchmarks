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
        stopped_east2_instances = filter_run_instances([(i, "aws-east") for i in list(ec2_east2.instances.filter(
            Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]))])

        if len(stopped_east2_instances) >= 2:
            print("Starting run instances")
            east1_instance = stopped_east2_instances[0]
            east2_instance = stopped_east2_instances[1]
            east1_instance[0].start()
            east2_instance[0].start()
            east1_instance[0].wait_until_running()
            east2_instance[0].wait_until_running()
            east1_instance[0].load()
            east2_instance[0].load()
            return (east1_instance, east2_instance)
        else:
            try:
                instance1 = create_east2_instance(run_instance_type)
                east1_instance = (instance1, "aws-east")
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
            return (east2_instance, west_instance)
        else:
            try:
                instance1 = create_west_instance(run_instance_type)
                west_instance = (instance1, "aws-west")
            except:
                print("Failed to create east1 instance")
                exit(0)

            try:
                instance2 = create_east2_instance(run_instance_type)
                east2_instance = (instance2, "aws-east")
            except:
                print("Failed to create east2 instance")
                exit(0)
            return (east2_instance, west_instance)


def get_select_instances(run_env):
    print(run_env, "SETTING")
    stopped_east2_instances = filter_run_instances([(i, "aws-east") for i in list(ec2_east2.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]))])
    if len(stopped_east2_instances) >= 1:
        print("Starting run instances")
        east2_instance = stopped_east2_instances[0]
        east2_instance[0].start()
        east2_instance[0].wait_until_running()
        east2_instance[0].load()
        return east2_instance
    else:
        try:
            instance2 = create_east2_instance(run_instance_type)
            east2_instance = (instance2, "aws-east")
        except:
            print("Failed to create east2 instance")
            exit(0)
        return east2_instance


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
            "cd ~ && git clone https://github.com/edwjchen/circ_benchmarks.git && cd ~/circ_benchmarks && git checkout aws2 -f && git add . && git stash && git pull -f && git submodule init && git submodule update && cd modules/HyCC && git checkout master -f && git add . && git stash && git pull -f && cd ~/circ_benchmarks && ./scripts/dependencies.sh && pip3 install pandas && python3 driver.py -f hycc && python3 driver.py -b && mkdir -p hycc_circuit_dir")
        if stdout.channel.recv_exit_status():
            print(ip, " failed setup")
    # else:
    #     _, stdout, _ = client.exec_command(
    #         "cd ~/circ_benchmarks && git checkout aws2 -f && git add . && git stash && git pull -f && git submodule init && git submodule update && cd modules/HyCC && git checkout master -f && git add . && git stash && git pull -f && cd ~/circ_benchmarks && ./scripts/dependencies.sh && pip3 install pandas && python3 driver.py -f hycc && python3 driver.py -b && mkdir -p hycc_circuit_dir")
    #     if stdout.channel.recv_exit_status():
    #         print(ip, " failed setup 2")

    print("Update repo")
    _, stdout, _ = client.exec_command(
        "cd ~/circ_benchmarks && git checkout aws2 -f && git reset --hard && git pull -f && git submodule init && git submodule update && cd modules/HyCC && git checkout master -f && git add . && git stash && git pull -f && cd ~/circ_benchmarks && ./scripts/dependencies.sh && pip3 install pandas && python3 driver.py -f hycc && python3 driver.py -b && mkdir -p hycc_circuit_dir")
    if stdout.channel.recv_exit_status():
        print(ip, " failed update (expected)")

    print("Build repo")
    _, stdout, _ = client.exec_command(
        "cd ~/circ_benchmarks && python3 driver.py -b && mkdir -p hycc_circuit_dir")
    if stdout.channel.recv_exit_status():
        print(ip, " failed setup 3")

    # # update ABY
    # print("Updating ABY")
    # _, stdout, _ = client.exec_command(
    #     "cd ~/circ_benchmarks && cd modules/ABY && git checkout public -f && git add . && git stash && git pull -f && cd extern/ENCRYPTO_utils && git checkout master -f && git add . && git stash && git pull -f")
    # if stdout.channel.recv_exit_status():
    #     print(ip, " failed setup 4")

    # update ABY
    print("Updating HyCC")
    _, stdout, _ = client.exec_command(
        "cd ~/circ_benchmarks && cd modules/HyCC && git checkout master -f && git reset --hard && git pull -f")
    if stdout.channel.recv_exit_status():
        print(ip, " failed setup 4")

    print("Removing old results directories")
    _, stdout, _ = client.exec_command(
        "cd ~/circ_benchmarks && rm -rf hycc_circuit_dir/ && rm -rf test_results/ && rm -rf run_test_results/")
    if stdout.channel.recv_exit_status():
        print(ip, " failed to remove hycc circuits")

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
    client = connect_to_instance(ip, k)
    sftp = client.open_sftp()
    with sftp.open('./circ_benchmarks/compile_params.json', 'w') as f:
        json.dump(params, f)
    client.close()
    print("Finished writing compile params: ", ip)

    # compile hycc
    compile_hycc(ip, k)

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


def get_version(params):
    return "hycc_{}_mt-{}_args-{}".format(params["name"], params["mt"], "".join(params["a"]))


def bundle_hycc(ip, k):
    client = connect_to_instance(ip, k)
    cmd = "cd ~/circ_benchmarks && python3 driver.py --bundle_with_params"
    print("Bundling:", cmd)
    _, stdout, stderr = client.exec_command(cmd)
    print("\n".join(stderr.readlines()))
    if stdout.channel.recv_exit_status():
        print(stderr)
        print(ip, " failed bundle")
    print("Bundled:", ip)
    client.close()


def select_hycc(ip, k):
    client = connect_to_instance(ip, k)
    cmd = "cd ~/circ_benchmarks && python3 driver.py --select_with_params"
    print("Selecting:", cmd)
    _, stdout, stderr = client.exec_command(cmd)
    print("\n".join(stderr.readlines()))
    if stdout.channel.recv_exit_status():
        print(stderr)
        print(ip, " failed select")
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
    print("Running hycc")
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

    print(server_params)
    print(client_params)

    # setup hycc
    ips = [ip1, ip2]
    ks = [k1, k2]
    pool = multiprocessing.Pool(len(ips))
    pool.starmap(setup_hycc, zip(ips, ks))

    # write run params to file
    print("Writing server params: ", server_params)
    client = connect_to_instance(ip1, k1)
    sftp = client.open_sftp()
    with sftp.open('./circ_benchmarks/run_params.json', 'w') as f:
        json.dump(server_params, f)
    client.close()
    print("Finished writing server params: ", ip1)

    print("Writing client params: ", client_params)
    client = connect_to_instance(ip2, k2)
    sftp = client.open_sftp()
    with sftp.open('./circ_benchmarks/run_params.json', 'w') as f:
        json.dump(client_params, f)
    client.close()
    print("Finished writing client params: ", ip2)

    # copy compiled circuits to instances
    version = get_version(params)
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i {}.pem\" --progress ./hycc_circuit_dir/{} ubuntu@{}:~/circ_benchmarks/hycc_circuit_dir".format(k1, version, ip1), shell=True)
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i {}.pem\" --progress ./hycc_circuit_dir/{} ubuntu@{}:~/circ_benchmarks/hycc_circuit_dir".format(k2, version, ip2), shell=True)

    # run test case
    pool = multiprocessing.Pool(len(ips))
    pool.starmap(run_hycc, zip(ips, ks))

    # get results
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i {}.pem\" --progress ubuntu@{}:~/circ_benchmarks/run_test_results server/".format(k1, ip1), shell=True)
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i {}.pem\" --progress ubuntu@{}:~/circ_benchmarks/run_test_results client/".format(k2, ip2), shell=True)

    # stop instances
    print("Stopping instance")
    instance1.stop()
    instance2.stop()
    instance1.wait_until_stopped()
    instance2.wait_until_stopped()
    print("Finished!")


def bundle_hycc_test(params):
    print("Bundling hycc")
    run_env = params["setting"]

    # get run instances
    instance1, k1 = get_select_instances(run_env)

    ip1 = instance1.public_dns_name
    print("instance1:", instance1)
    print("key1:",  k1)
    print("ip1:", ip1)

    server_params = params.copy()

    print(server_params)

    # setup hycc
    ips = [ip1]
    ks = [k1]
    pool = multiprocessing.Pool(len(ips))
    pool.starmap(setup_hycc, zip(ips, ks))

    # write run params to file
    print("Writing server params: ", server_params)
    client = connect_to_instance(ip1, k1)
    sftp = client.open_sftp()
    with sftp.open('./circ_benchmarks/compile_params.json', 'w') as f:
        json.dump(server_params, f)
    client.close()
    print("Finished writing server params: ", ip1)

    # copy compiled circuits to instances
    version = get_version(params)
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i {}.pem\" --progress ./hycc_circuit_dir/{} ubuntu@{}:~/circ_benchmarks/hycc_circuit_dir".format(k1, version, ip1), shell=True)

    # bundle test case
    pool = multiprocessing.Pool(len(ips))
    pool.starmap(bundle_hycc, zip(ips, ks))

    # get circuit results
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i {}.pem\" --progress ubuntu@{}:~/circ_benchmarks/hycc_circuit_dir .".format(k1, ip1), shell=True)

    # stop instances
    print("Stopping instance")
    instance1.stop()
    instance1.wait_until_stopped()
    print("Finished!")


def select_hycc_test(params):
    print("Selecting hycc")
    run_env = params["setting"]

    # get run instances
    instance1, k1 = get_select_instances(run_env)

    ip1 = instance1.public_dns_name
    print("instance1:", instance1)
    print("key1:",  k1)
    print("ip1:", ip1)

    server_params = params.copy()

    # instance1 is the server
    server_params["role"] = 0
    server_params["address"] = instance1.private_ip_address
    server_params["setting"] = run_env

    print(server_params)

    # setup hycc
    ips = [ip1]
    ks = [k1]
    pool = multiprocessing.Pool(len(ips))
    pool.starmap(setup_hycc, zip(ips, ks))

    # write run params to file
    print("Writing server params: ", server_params)
    client = connect_to_instance(ip1, k1)
    sftp = client.open_sftp()
    with sftp.open('./circ_benchmarks/run_params.json', 'w') as f:
        json.dump(server_params, f)
    client.close()
    print("Finished writing server params: ", ip1)

    # copy compiled circuits to instances
    version = get_version(params)
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i {}.pem\" --progress ./hycc_circuit_dir/{} ubuntu@{}:~/circ_benchmarks/hycc_circuit_dir".format(k1, version, ip1), shell=True)

    # select test case
    pool = multiprocessing.Pool(len(ips))
    pool.starmap(select_hycc, zip(ips, ks))

    # get circuit results
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i {}.pem\" --progress ubuntu@{}:~/circ_benchmarks/hycc_circuit_dir .".format(k1, ip1), shell=True)

    # get results
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i {}.pem\" --progress ubuntu@{}:~/circ_benchmarks/test_results server/".format(k1, ip1), shell=True)

    # stop instances
    print("Stopping instance")
    instance1.stop()
    instance1.wait_until_stopped()
    print("Finished!")


test_compile_params = [
    # {
    #     "name": "biomatch",
    #     "path": "biomatch/biomatch.c",
    #     "mt": 600,
    #     "a": ["--all-variants"],
    # },
    # {
    #     "name": "kmeans",
    #     "path": "kmeans/kmeans.c",
    #     "mt": 600,
    #     "a": ["--all-variants"],
    # },
    # {
    #     "name": "gauss",
    #     "path": "gauss/gauss.c",
    #     "mt": 9,
    #     "a": ["--all-variants"],
    # },
    # {
    #     "name": "gcd",
    #     "path": "gcd/gcd.c",
    #     "mt": 600,
    #     "a": ["--all-variants"],
    # },
    # {
    #     "name": "histogram",
    #     "path": "histogram/histogram.c",
    #     "mt": 600,
    #     "a": ["--all-variants"],
    # },
    # {
    #     "name": "db_join2",
    #     "path": "db_join2/db_join2.c",
    #     "mt": 600,
    #     "a": ["--all-variants"],
    # },
    # {
    #     "name": "db_merge",
    #     "path": "db_merge/db_merge.c",
    #     "mt": 600,
    #     "a": ["--all-variants"],
    # },
    {
        "name": "mnist",
        "path": "mnist/mnist.c",
        "mt": 600,
        "a": ["--all-variants"],
    },
    # {
    #     "name": "cryptonets",
    #     "path": "cryptonets/cryptonets.c",
    #     "mt": 600,
    #     "a": ["--all-variants"],
    # },
]

# for compile_params in test_compile_params:
#     compile_hycc_test(compile_params)

test_select_lan_params = [
    {
        "setting": LAN,
        "cm": "lan"
    },
]

test_select_wan_params = [
    {
        "setting": WAN,
        "cm": "wan"
    },
]

# for compile_params in test_compile_params:
#     for select_params in test_select_lan_params:
#         p = {**compile_params, **select_params}
#         bundle_hycc_test(p)

# for compile_params in test_compile_params:
#     for select_params in test_select_lan_params:
#         p = {**compile_params, **select_params}
#         select_hycc_test(p)

# for compile_params in test_compile_params:
#     for select_params in test_select_wan_params:
#         p = {**compile_params, **select_params}
#         select_hycc_test(p)


test_run_lan_params = [
    # {
    #     "ss": "yaoonly",
    # },
    # {
    #     "ss": "gmwonly",
    # },
    {
        "ss": "yaohybrid",
    },
    # {
    #     "ss": "gmwhybrid",
    # },
    # {
    #     "ss": "lan_optimized",
    # },
]

for compile_params in test_compile_params:
    for select_params in test_select_lan_params:
        for run_params in test_run_lan_params:
            p = {**compile_params, **run_params}
            p = {**p, **select_params}
            run_hycc_test(p)

test_run_wan_params = [
    # {
    #     "ss": "yaoonly",
    # },
    # {
    #     "ss": "gmwonly",
    # },
    {
        "ss": "yaohybrid",
    },
    # {
    #     "ss": "gmwhybrid",
    # },
    # {
    #     "ss": "wan_optimized",
    # },
]

# for compile_params in test_compile_params:
#     for select_params in test_select_wan_params:
#         for run_params in test_run_wan_params:
#             p = {**compile_params, **run_params}
#             p = {**p, **select_params}
#             run_hycc_test(p)
