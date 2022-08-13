from concurrent.futures import ThreadPoolExecutor
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
# COMPILE_INSTANCE_TYPE = "c5.large"
COMPILE_INSTANCE_TYPE = "r6a.16xlarge"

LAN = "LAN"
WAN = "WAN"
EAST = "east"
WEST = "west"

ec2_east = boto3.resource("ec2",
                          aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
                          aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
                          region_name="us-east-2")
ec2_west = boto3.resource("ec2",
                          aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
                          aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
                          region_name="us-west-2")


def create_instances():
    # create two AWS East Instances if they haven't been made
    instances = list(ec2_east.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["stopping", "pending", "running", "stopped"]}]))
    num_instances_to_create = max(0, 2 - len(instances))
    if num_instances_to_create > 0:
        ec2_east.create_instances(ImageId="ami-05b63781e32145c7f",
                                  InstanceType=instance_type,
                                  KeyName="aws-east",
                                  MinCount=1,
                                  MaxCount=num_instances_to_create,
                                  Monitoring={
                                      "Enabled": False},
                                  SecurityGroups=[
                                      "circ4mpc"]
                                  )

    print("Created {} instances".format(num_instances_to_create))

    # create one AWS West Instance if they haven't been made
    west_instances = list(ec2_west.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["stopping", "pending", "running", "stopped"]}]))
    num_west_instance_to_create = max(0, 1 - len(west_instances))
    if num_west_instance_to_create > 0:
        ec2_west.create_instances(ImageId="ami-0ddf424f81ddb0720",
                                  InstanceType=instance_type,
                                  KeyName="aws-west",
                                  MinCount=1,
                                  MaxCount=num_west_instance_to_create,
                                  Monitoring={
                                      "Enabled": False},
                                  SecurityGroups=[
                                      "circ4mpc"]
                                  )
    print("Created {} west instances".format(num_west_instance_to_create))


def create_instances(location, num, instance_type):
    instances = []
    if location == EAST:
        while len(instances) < num:
            instances += ec2_east.create_instances(ImageId="ami-05b63781e32145c7f",
                                        InstanceType=instance_type,
                                        KeyName="aws-east",
                                        MinCount=1,
                                        MaxCount=num - len(instances),
                                        Monitoring={
                                            "Enabled": False},
                                        SecurityGroups=[
                                            "circ4mpc"]
                                        )
        
        print("Created {} east instances".format(num))
    else:
        # create one AWS West Instance if they haven't been made
        while len(instances) < num:
            instances += ec2_east.create_instances(ImageId="ami-05b63781e32145c7f",
                                        InstanceType=instance_type,
                                        KeyName="aws-east",
                                        MinCount=1,
                                        MaxCount=num - len(instances),
                                        Monitoring={
                                            "Enabled": False},
                                        SecurityGroups=[
                                            "circ4mpc"]
                                        )
        print("Created {} west instances".format(num))
    [instance.wait_until_running() for instance in instances]
    [instance.load() for instance in instances]
    return instances

def start_instances():
    stopped_instances = list(ec2_east.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]))
    count = 0
    num = len(stopped_instances)
    for i in range(num):
        instance = stopped_instances[i]
        ec2_east.instances.filter(InstanceIds=[instance.id]).start()
        count += 1
    print("Started {} East instances".format(count))

    stopped_instances = list(ec2_west.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]))
    count = 0
    num = len(stopped_instances)
    for i in range(num):
        instance = stopped_instances[i]
        ec2_west.instances.filter(InstanceIds=[instance.id]).start()
        count += 1
    print("Started {} West instances".format(count))


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

    print("Setting up:")
    pool = multiprocessing.Pool(len(running_instance_ips))
    pool.starmap(setup_worker, zip(running_instance_ips, keys))


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
    count = 0
    num = len(stopped_instances)
    for i in range(num):
        instance = stopped_instances[i]
        ec2_west.instances.filter(InstanceIds=[instance.id]).start()
        count += 1
    print("Started {} West instances".format(count))
    time.sleep(15)

    # compile on west instance
    running_west_instances = list(ec2_west.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]))
    ip = [instance.public_dns_name for instance in running_west_instances][0]
    id = [instance.id for instance in running_west_instances][0]
    key = paramiko.Ed25519Key.from_private_key_file("aws-west.pem")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=ip, username="ubuntu", pkey=key)

    _, stdout, _ = client.exec_command(
        "cd ~/circ_benchmarks && python3 driver.py -f hycc circ && python3 driver.py --compile")
    if stdout.channel.recv_exit_status():
        print(ip, " failed compiles")

    print("Compiled:", ip)
    client.close()

    # scp compiled hycc_circuit_dir & test_results to local directory
    if not os.path.exists("./aws/"):
        os.makedirs("./aws/")
    if not os.path.exists("./aws/"+id):
        os.mkdir("./aws/"+id)

    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i aws-west.pem\" --progress ubuntu@{}:~/circ_benchmarks/hycc_circuit_dir ./aws/{}".format(ip, id), shell=True)
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i aws-west.pem\" --progress ubuntu@{}:~/circ_benchmarks/circ_circuit_dir ./aws/{}".format(ip, id), shell=True)
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i aws-west.pem\" --progress ubuntu@{}:~/circ_benchmarks/test_results ./aws/{}".format(ip, id), shell=True)

    # start all other instances
    start_instances()
    time.sleep(15)

    # then scp hycc_circ_dir to other instances
    running_east_instances = list(ec2_east.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]))
    running_east_instance_ips = [
        instance.public_dns_name for instance in running_east_instances]
    ids = [id for _ in running_east_instance_ips]

    print("SCP hycc_circuit_dirs:")
    pool = multiprocessing.Pool(len(running_east_instance_ips))
    pool.starmap(compile_scp_worker, zip(running_east_instance_ips, ids))

    # stop all instances
    stop_instances()


def compile_scp_worker(ip, id):
    print("ip:", ip, "\nid:", id)
    key = paramiko.Ed25519Key.from_private_key_file("aws-east.pem")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=ip, username="ubuntu", pkey=key)
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i aws-east.pem\" --progress ./aws/{}/hycc_circuit_dir/ ubuntu@{}:~/circ_benchmarks/hycc_circuit_dir".format(id, ip), shell=True)
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i aws-east.pem\" --progress ./aws/{}/circ_circuit_dir/ ubuntu@{}:~/circ_benchmarks/circ_circuit_dir".format(id, ip), shell=True)
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i aws-east.pem\" --progress ./aws/{}/test_results/ ubuntu@{}:~/circ_benchmarks/test_results".format(id, ip), shell=True)

    print("SCP'd:", ip)
    client.close()


def run_benchmarks(setting):
    if setting == LAN:
        lan()
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
        wan()
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


def benchmark_hycc_worker(ip, connect_ip, role, key_file):
    print("Running HyCC benchmark:\nip: {}\nconnect: {}\nrole: {}\n".format(
        ip, connect_ip, role))
    key = paramiko.Ed25519Key.from_private_key_file(key_file)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=ip, username="ubuntu", pkey=key)

    cmd = "cd ~/circ_benchmarks/ && python3 driver.py --address {} && python3 driver.py --role {} && python3 driver.py -f hycc && python3 driver.py --benchmark".format(
        connect_ip, role)
    _, stdout, _ = client.exec_command(cmd)

    if stdout.channel.recv_exit_status():
        print(ip, " failed running benchmark")

    client.close()


def benchmark_circ_worker(ip, connect_ip, role, key_file):
    print("Running CirC benchmark:\nip: {}\nconnect: {}\nrole: {}\n".format(
        ip, connect_ip, role))
    key = paramiko.Ed25519Key.from_private_key_file(key_file)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=ip, username="ubuntu", pkey=key)

    cmd = "cd ~/circ_benchmarks/ && python3 driver.py --address {} && python3 driver.py --role {} && python3 driver.py -f circ && python3 driver.py --benchmark".format(
        connect_ip, role)
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


def lan():
    # start ec2 east instances if possible
    stopped_instances = list(ec2_east.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]))
    count = 0
    num = len(stopped_instances)
    for i in range(num):
        instance = stopped_instances[i]
        ec2_east.instances.filter(InstanceIds=[instance.id]).start()
        count += 1
    print("Started {} East instances".format(count))

    # stop ec2 west instances if possible
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
    time.sleep(15)


def wan():
    # start only 1 ec2 east instances if possible
    running_east_instances = list(ec2_east.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]))

    if not running_east_instances:
        stopped_instances = list(ec2_east.instances.filter(
            Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]))
        count = 0
        for i in range(1):
            instance = stopped_instances[i]
            ec2_east.instances.filter(InstanceIds=[instance.id]).start()
            count += 1
        print("Started {} East instances".format(count))
    elif len(running_east_instances) == 2:
        count = 0
        for i in range(1):
            instance = running_east_instances[i]
            print("Stopping", instance.public_dns_name)
            ec2_east.instances.filter(InstanceIds=[instance.id]).stop()
            count += 1
        print("Stopped {} West instances".format(count))

    # start only 1 ec2 west instances if possible
    stopped_west_instances = list(ec2_west.instances.filter(
        Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]))
    count = 0
    num = len(stopped_west_instances)
    for i in range(num):
        instance = stopped_west_instances[i]
        ec2_west.instances.filter(InstanceIds=[instance.id]).start()
        count += 1
    print("Started {} East instances".format(count))
    time.sleep(15)






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
#             stop_instances()
#         elif cmd_type == "compile":
#             compile_benchmarks()
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
#             setting = cmd_type
#             print("Operating in: {}".format(setting))
#             lan()
#         elif cmd_type == WAN:
#             setting = cmd_type
#             print("Operating in: {}".format(setting))
#             wan()
#         else:
#             print("unlucky, not a cmd")

#         if cmd_type != "stats":
#             stats(setting)

def get_stopped_instances(location):
    if location == EAST:
        instances = list(ec2_east.instances.filter(
            Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]))
        return instances
    else:
        instances = list(ec2_west.instances.filter(
            Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]))
        return instances


def setup_instances():
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

    print("Setting up:")
    pool = multiprocessing.Pool(len(running_instance_ips))
    pool.starmap(setup_worker, zip(running_instance_ips, keys))


def setup_worker(ip, key_file):
    print("Setting up:")
    print("ip:", ip, "\nkey:", key_file)
    key = paramiko.Ed25519Key.from_private_key_file(key_file)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    retry = 0
    while retry < 5:
        print("Try connecting: {}".format(retry))
        try:
            client.connect(hostname=ip, username="ubuntu", pkey=key)
            print("connected to:", ip)
            break
        except:
            time.sleep(5)
            retry += 1

    _, stdout, _ = client.exec_command("cd ~/circ_benchmarks")
    if stdout.channel.recv_exit_status():
        _, stdout, _ = client.exec_command(
            "cd ~ && git clone https://github.com/edwjchen/circ_benchmarks.git && cd ~/circ_benchmarks && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && source \"$HOME/.cargo/env\" && ./scripts/dependencies.sh && pip3 install pandas && python3 driver.py -f hycc circ && python3 driver.py -b")
        if stdout.channel.recv_exit_status():
            print(ip, " failed setup")
    else:
        _, stdout, _ = client.exec_command(
            "cd ~/circ_benchmarks && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && source \"$HOME/.cargo/env\" && ./scripts/dependencies.sh && pip3 install pandas && python3 driver.py -f hycc circ && python3 driver.py -b")
        if stdout.channel.recv_exit_status():
            print(ip, " failed setup 2")

    print("Set up:", ip)
    client.close()

def setup_hycc_worker(ip, key_file):
    print("Setting up:")
    print("ip:", ip, "\nkey:", key_file)
    key = paramiko.Ed25519Key.from_private_key_file(key_file)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    retry = 0
    while retry < 5:
        print("Try connecting: {}".format(retry))
        try:
            client.connect(hostname=ip, username="ubuntu", pkey=key)
            print("connected to:", ip)
            break
        except:
            time.sleep(5)
            retry += 1

    _, stdout, _ = client.exec_command("cd ~/circ_benchmarks")
    if stdout.channel.recv_exit_status():
        _, stdout, _ = client.exec_command(
            "cd ~ && git clone https://github.com/edwjchen/circ_benchmarks.git && cd ~/circ_benchmarks && ./scripts/dependencies.sh && pip3 install pandas && python3 driver.py -f hycc && python3 driver.py -b")
        if stdout.channel.recv_exit_status():
            print(ip, " failed setup")
    else:
        _, stdout, _ = client.exec_command(
            "cd ~/circ_benchmarks && ./scripts/dependencies.sh && pip3 install pandas && python3 driver.py -f hycc && python3 driver.py -b")
        if stdout.channel.recv_exit_status():
            print(ip, " failed setup 2")

    print("Set up:", ip)
    client.close()

def compile_hycc_worker(instance, ip, key_file, param_str):
    print("Compile hycc:\nip: {}\nparam: {}".format(ip, param_str))
    key = paramiko.Ed25519Key.from_private_key_file(key_file)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    retry = 0
    while retry < 5:
        print("Try connecting: {}".format(retry))
        try:
            client.connect(hostname=ip, username="ubuntu", pkey=key)
            print("connected to:", ip)
            break
        except:
            time.sleep(5)
            retry += 1

    # compile
    cmd = "python3 driver.py --compile_aws {}".format(param_str)
    print("Running:", cmd)
    _, stdout, _ = client.exec_command(cmd)
    if stdout.channel.recv_exit_status():
        print(ip, " failed to compile:", param_str)

    # copy hycc_circ_dir
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i aws-east.pem\" --progress ./hycc_circuit_dir/ ubuntu@{}:~/circ_benchmarks/hycc_circuit_dir".format(ip), shell=True)
    # copy test_results 
    subprocess.call(
        "rsync -avz -e \"ssh -o StrictHostKeyChecking=no -i aws-east.pem\" --progress ./test_results/ ubuntu@{}:~/circ_benchmarks/test_results".format(ip), shell=True)

    client.close()

    # stop the instance
    instance.stop()


def compile_hycc_aws(all_param_strs):
    num_instances = len(all_param_strs)
    stopped_east_instances = get_stopped_instances(EAST)
    num_to_create = num_instances - len(stopped_east_instances)
    created_instances = []
    if num_to_create > 0:
        print("Creating instances")
        created_instances = create_instances(EAST, num_to_create, COMPILE_INSTANCE_TYPE)

        # setup created instances
        setup_instance_ips = [instance.public_dns_name for instance in created_instances]
        setup_keys = ["aws-east.pem" for _ in created_instances]

        for ip in setup_instance_ips:
            print("ssh -i \"aws-east.pem\" ubuntu@{}".format(ip))

        pool = multiprocessing.Pool(len(setup_instance_ips))
        pool.starmap(setup_hycc_worker, zip(setup_instance_ips, setup_keys))

    # start stopped_east_instances 
    print("Starting stopped instances")
    [instance.start() for instance in stopped_east_instances]
    [instance.wait_until_running() for instance in stopped_east_instances]
    [instance.load() for instance in stopped_east_instances]
    
    # compile benchmarks on all instances 
    all_instances = created_instances + stopped_east_instances
    compile_instance_ips = [instance.public_dns_name for instance in all_instances]
    compile_keys = ["aws-east.pem" for _ in all_instances]

    pool = multiprocessing.Pool(len(compile_instance_ips))
    pool.starmap_async(compile_hycc_worker, zip(all_instances, compile_instance_ips, compile_keys, all_param_strs))

    
    