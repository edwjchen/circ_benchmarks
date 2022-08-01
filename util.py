import pandas as pd
import copy
import subprocess
import os

feature_path = ".features.txt"
valid_features = {"circ", "hycc"}

TIMEOUT = 1000

# installation variables
ABY_SOURCE = "./modules/ABY"
HYCC_SOURCE = "./modules/HyCC"
CIRC_SOURCE = "./modules/circ"
KAHIP_SOURCE = "./modules/KaHIP"

ABY_HYCC = HYCC_SOURCE+"/aby-hycc"
ABY_HYCC_DIR = ABY_SOURCE + "/src/examples/aby-hycc/"
ABY_CMAKE = ABY_SOURCE + "/src/examples/CMakeLists.txt"

# benchmark variables
TMP_PATH = "./tmp/"
PARENT_DIR = "../"
CBMC_GC = HYCC_SOURCE + "/bin/cbmc-gc"
CIRCUIT_SIM = HYCC_SOURCE + "/bin/circuit-sim"
ABY_CBMC_GC = ABY_SOURCE + "/build/bin/aby-hycc"
MPC_CIRC = "mpc_main.circ"
MODULE_BUNDLE = HYCC_SOURCE+"/src/circuit-utils/py/module_bundle.py"
SELECTION = HYCC_SOURCE+"/src/circuit-utils/py/selection.py"
COSTS = HYCC_SOURCE+"/src/circuit-utils/py/costs.json"

# joint parameters
RERUN = 1
SIZE = 256

# hycc parameters
MINIMIZATION_TIME = 0
COST_MODEL = "hycc"  # opa

# circ parameters
NUM_PARTS = 3
MUT_LEVEL = 4
MUT_STEP_SIZE = 1
TEST_FILE = "./examples/C/mpc/benchmarks/biomatch/2pc_biomatch_" + \
    str(SIZE) + ".c"
TEST_NAME = "biomatch"

# logging variables
DELIMITER = "\nLOG: ====================================\n"
VERSION = ""


def save_features(features):
    """ Save features to file """
    with open(feature_path, 'w') as f:
        feature_str = "\n".join(features)
        f.write(feature_str)


def load_features():
    """ Load features from file """
    if os.path.exists(feature_path):
        with open(feature_path, 'r') as f:
            features = f.read().splitlines()
            return set(features)
    else:
        return set()


def make_tmp():
    subprocess.run(["mkdir", "-p", "tmp"])


def remove_tmp():
    subprocess.run(["rm", "-rf", "tmp"])

###############################################################################
# Logging
###############################################################################

def wrap_cmd(cmd):
    time_cmd = "/usr/bin/time --format='%e seconds %M kB'"
    return " ".join([time_cmd] + cmd)


def run_cmds(server_cmd, client_cmd, name, version):
    write_log("LOG: Test: {}".format(name), version)
    os.chdir(TMP_PATH)
    server_cmd = wrap_cmd(server_cmd)
    client_cmd = wrap_cmd(client_cmd)
    print(server_cmd)
    server_proc = subprocess.Popen(server_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    client_proc = subprocess.Popen(client_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    server_stdout, server_stderr = server_proc.communicate(timeout=TIMEOUT)
    client_stdout, client_stderr = client_proc.communicate(timeout=TIMEOUT)
    os.chdir(PARENT_DIR)

    if server_proc.returncode: 
        write_log("LOG: Error: Process returned with status code {}".format(server_proc.returncode), version)
        write_log("LOG: Error message: {}".format(" ".join(server_stderr.decode("utf-8").split("\n"))), version)
        return
    
    if client_proc.returncode: 
        write_log("LOG: Error: Process returned with status code {}".format(client_proc.returncode), version)
        write_log("LOG: Error message: {}".format(" ".join(client_stderr.decode("utf-8").split("\n"))), version)
        return 

    # record server
    server_out = server_stdout.decode("utf-8")
    write_log(server_out, version)

    server_err = server_stderr.decode("utf-8")
    last_line = [l for l in server_err.split("\n") if l][-1]
    memory_output = "LOG: Server Time / Memory: {}".format(last_line)
    write_log(memory_output, version)

    # record client 
    client_out = client_stdout.decode("utf-8")
    write_log(client_out, version)

    client_err = client_stderr.decode("utf-8")
    last_line = [l for l in client_err.split("\n") if l][-1]
    memory_output = "LOG: Client Time / Memory: {}".format(last_line)
    write_log(memory_output, version)


def run_cmd(cmd, name, version):
    write_log("LOG: Test: {}".format(name), version)
    os.chdir(TMP_PATH)
    cmd = wrap_cmd(cmd)
    print(cmd)
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate(timeout=TIMEOUT)
    os.chdir(PARENT_DIR)

    if proc.returncode: 
        write_log("LOG: Error: Process returned with status code {}".format(proc.returncode), version)
        write_log("LOG: Error message: {}".format(" ".join(stderr.decode("utf-8").split("\n"))), version)
        raise RuntimeError

    # record stdout
    out = stdout.decode("utf-8")
    write_log(out, version)

    # record stderr
    err = stderr.decode("utf-8")
    last_line = [l for l in err.split("\n") if l][-1]
    memory_output = "LOG: Time / Memory: {}".format(last_line)
    write_log(memory_output, version)


def make_test_results():
    subprocess.run(["mkdir", "-p", "test_results"])


def write_to_log(text, version):
    log_path = format("test_results/log_{}.txt".format(version))
    if not os.path.exists(log_path):
        subprocess.run(["touch", log_path])

    lines = text.split("\n")
    for line in lines:
        clean_line = line.strip()
        if clean_line.startswith("LOG:"):
            with open(log_path, "a") as f:
                f.write(clean_line + "\n")


def write_to_run(text, version):
    run_path = format("test_results/run_{}.txt".format(version))
    if not os.path.exists(run_path):
        subprocess.run(["touch", run_path])

    with open(run_path, "a") as f:
        f.write(text + "\n")


def write_log(text, version):
    write_to_log(text, version)
    write_to_run(text, version)


####################
# to csv
####################


def get_last_elem(line):
    return line.split()[-1]


def standardize_time(t):
    if t.endswith("ms"):
        return float(t[:-2]) / 1000
    else:
        return float(t[:-1])


def parse_circ_log(path):
    with open(path, "r") as f:
        log = f.read()
        results = []
        data = {}
        for line in log.split("\n"):
            if not line:
                if data:
                    results.append(copy.deepcopy(data))
                data = {}
            elif line.startswith("Running"):
                data["selection_scheme"] = get_last_elem(line)
            elif line.startswith("Test"):
                test_case = line.split()[-1]
                data["test_case"] = test_case
            elif line.startswith("Parameters"):
                params = [int(l) for l in line.split(":")[-1].split(",")]
                data["input_size"] = params[0]
                data["num_parts"] = params[1]
                data["mutation_level"] = params[2]
                data["mutation_step_size"] = params[3]
            elif "RERUN:" in line:
                run = int(get_last_elem(line))
                if "run" in data and run != data["run"]:
                    results.append(copy.deepcopy(data))
                data["run"] = run

            elif "Cost model:" in line:
                data["cost_model"] = get_last_elem(line)
            elif "Cost of assignment total:" in line:
                data["ilp_cost"] = float(get_last_elem(line))
            elif "Cost of assignment node:" in line:
                data["op_cost"] = float(get_last_elem(line))
            elif "Cost of assignment conv:" in line:
                data["conv_cost"] = float(get_last_elem(line))
            elif "Compile cost:" in line:
                t = get_last_elem(line)
                t = standardize_time(t)
                data["compile_time"] = t
            elif "Server load time:" in line:
                data["server_load_time"] = float(get_last_elem(line))
            elif "Server exec time:" in line:
                data["server_exec_time"] = float(get_last_elem(line))
            elif "Server total time:" in line:
                data["server_total_time"] = float(get_last_elem(line))
            elif "Client load time:" in line:
                data["client_load_time"] = float(get_last_elem(line))
            elif "Client exec time:" in line:
                data["client_exec_time"] = float(get_last_elem(line))
            elif "Client total time:" in line:
                data["client_total_time"] = float(get_last_elem(line))
            elif "Mutation+ILP time:" in line:
                t = get_last_elem(line)
                t = standardize_time(t)
                data["ilp_time"] = t
            elif "ILP time:" in line:
                t = get_last_elem(line)
                t = standardize_time(t)
                data["ilp_time"] = t
            elif "Comb time:" in line:
                t = get_last_elem(line)
                t = standardize_time(t)
                data["comb_time"] = t
            elif "Part time:" in line:
                t = get_last_elem(line)
                t = standardize_time(t)
                data["part_time"] = t
            elif "num_nodes:" in line:
                data["num_nodes"] = int(get_last_elem(line))
            elif "avg_partition_size:" in line:
                data["avg_partition_size"] = float(get_last_elem(line))

        df = pd.DataFrame(results)

        # clean values
        num_nodes = [n for n in df.num_nodes.unique() if not pd.isna(n)]
        assert(len(num_nodes) == 1)
        num_nodes = num_nodes[0]
        avg_partition_size = [
            n for n in df.avg_partition_size.unique() if not pd.isna(n)]
        assert(len(avg_partition_size) == 1)
        avg_partition_size = avg_partition_size[0]
        df["num_nodes"] = df.num_nodes.apply(
            lambda x: num_nodes if pd.isna(x) else x)
        df["avg_partition_size"] = df.avg_partition_size.apply(
            lambda x: avg_partition_size if pd.isna(x) else x)
        df = df.fillna(0)

        csv_path = "csvs/{}.csv".format(path.split("/")[-1].split(".")[0])
        df.to_csv(csv_path)


def parse_hycc_log(path):
    with open(path, "r") as f:
        log = f.read()

        test_name = ""
        minimization_time = 0
        input_size = 0
        cost_model = ""
        variant = ""
        module_bundle_time = 0
        selection_time = 0

        results = []
        data = {}
        for line in log.split("\n"):
            if line.startswith("Using"):
                data["test_case"] = test_name
                data["minimization_time"] = minimization_time
                data["input_size"] = input_size
                data["cost_model"] = cost_model
                data["variant"] = variant
                data["module_bundle_time"] = module_bundle_time
                data["selection_time"] = selection_time

            if not line:
                if data and "server_load_time" in data:
                    results.append(copy.deepcopy(data))
                    data = {}
            elif line.startswith("Running HyCC"):
                data["selection_scheme"] = get_last_elem(line)
            elif line.startswith("TEST PATH:"):
                test_case = get_last_elem(line).split("/")[-1].split(".")[0]
                name = test_case.split("_")[0]
                data["test_case"] = name
                test_name = data["test_case"]
            elif line.startswith("Running with args:"):
                data["variant"] = get_last_elem(line)
                variant = data["variant"]
            elif line.startswith("Using"):
                data["runner"] = get_last_elem(line)
            elif "Compile time:" in line:
                data["compile_time"] = float(get_last_elem(line))
            elif "RERUN:" in line:
                run = int(get_last_elem(line))
                if "run" in data and run != data["run"]:
                    results.append(copy.deepcopy(data))
                data["run"] = run
            elif "MINIMIZATION TIME:" in line:
                data["minimization_time"] = int(get_last_elem(line))
                minimization_time = data["minimization_time"]
            elif "SIZE:" in line:
                data["input_size"] = int(get_last_elem(line))
                input_size = data["input_size"]
            elif "COST MODEL:" in line:
                data["cost_model"] = get_last_elem(line)
                cost_model = data["cost_model"]
            elif "Server load time:" in line:
                data["server_load_time"] = float(get_last_elem(line))
            elif "Server exec time:" in line:
                data["server_exec_time"] = float(get_last_elem(line))
            elif "Client load time:" in line:
                data["client_load_time"] = float(get_last_elem(line))
            elif "Client exec time:" in line:
                data["client_exec_time"] = float(get_last_elem(line))
            elif "Load time:" in line:
                data["server_load_time"] = float(get_last_elem(line))
            elif "Exec time:" in line:
                data["server_exec_time"] = float(get_last_elem(line))
            elif "Module bundle time:" in line:
                data["module_bundle_time"] = float(get_last_elem(line))
                module_bundle_time = data["module_bundle_time"]
            elif "Selection time:" in line:
                data["selection_time"] = float(get_last_elem(line))
                selection_time = data["selection_time"]

        df = pd.DataFrame(results)
        csv_path = "csvs/{}.csv".format(path.split("/")[-1].split(".")[0])
        df.to_csv(csv_path)
