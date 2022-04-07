import subprocess
import os

feature_path = ".features.txt"
valid_features = {"circ", "hycc"}

# installation variables
ABY_SOURCE = "./modules/ABY"
HYCC_SOURCE = "./modules/HyCC"
CIRC_SOURCE = "./modules/circ"
KAHIP_SOURCE = "./modules/KaHIP"

ABY_HYCC = HYCC_SOURCE+"/aby-hycc"
ABY_HYCC_DIR = ABY_SOURCE +"/src/examples/aby-hycc/"
ABY_CMAKE = ABY_SOURCE + "/src/examples/CMakeLists.txt"

# benchmark variables
TMP_PATH = "./tmp/"
PARENT_DIR = "../"
CBMC_GC = HYCC_SOURCE + "/bin/cbmc-gc"
CIRCUIT_SIM = HYCC_SOURCE + "/bin/circuit-sim"
ABY_CBMC_GC = ABY_SOURCE + "/build/bin/aby-hycc"
MPC_CIRC = "mpc_main.circ"
MODULE_BUNDLE=HYCC_SOURCE+"/src/circuit-utils/py/module_bundle.py"
SELECTION=HYCC_SOURCE+"/src/circuit-utils/py/selection.py"
COSTS=HYCC_SOURCE+"/src/circuit-utils/py/costs.json"

# joint parameters
SIZE = 256
RERUN = 3

# hycc parameters
MINIMIZATION_TIME = 0
COST_MODEL = "hycc" # opa

# circ parameters
NUM_PARTS = 3
MUT_LEVEL = 4
MUT_STEP_SIZE = 1
TEST_FILE = "./examples/C/mpc/benchmarks/biomatch/2pc_biomatch_" + str(SIZE) + ".c"
TEST_NAME = "biomatch"

# logging variables
DELIMITER = "\n====================================\n"
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

def make_test_results():
    subprocess.run(["mkdir", "-p", "test_results"])

def make_version(features):
    global VERSION
    if "hycc" in features:
        VERSION = "{}_biomatch_is-{}_mt-{}_cm-{}".format("hycc", SIZE, MINIMIZATION_TIME, COST_MODEL)

    if "circ" in features:
        VERSION = "{}_biomatch_is-{}_np-{}_ml-{}_mss-{}_cm-{}".format("circ", SIZE, NUM_PARTS, MUT_LEVEL, MUT_STEP_SIZE, COST_MODEL)

def write_output_to_log(text):
    lines = text.split("\n")
    for line in lines:
        clean_line = line.strip()
        if clean_line.startswith("LOG:"):
            write_to_log(clean_line)

def write_to_log(text):
    global VERSION
    log_path = format("test_results/log_{}.txt".format(VERSION))
    if not os.path.exists(log_path):
        subprocess.run(["touch", log_path])

    with open(log_path, "a") as f:
        f.write(text + "\n")

def write_to_run(text):
    global VERSION
    run_path = format("test_results/run_{}.txt".format(VERSION))
    if not os.path.exists(run_path):
        subprocess.run(["touch", run_path])

    with open(run_path, "a") as f:
        f.write(text + "\n")

def write_to_both(text):
    write_to_log(text)
    write_to_run(text)


####################
# to csv
####################
import copy
import pandas as pd

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

        #clean values 
        num_nodes = [n for n in df.num_nodes.unique() if not pd.isna(n)]
        assert(len(num_nodes) == 1)
        num_nodes = num_nodes[0]
        avg_partition_size = [n for n in df.avg_partition_size.unique() if not pd.isna(n)]
        assert(len(avg_partition_size) == 1)
        avg_partition_size = avg_partition_size[0]
        df["num_nodes"] = df.num_nodes.apply(lambda x: num_nodes if pd.isna(x) else x)
        df["avg_partition_size"] = df.avg_partition_size.apply(lambda x: avg_partition_size if pd.isna(x) else x)
        df = df.fillna(0)

        csv_path = "csvs/{}.csv".format(path.split(".")[0])
        df.to_csv(csv_path)