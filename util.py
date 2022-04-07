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

# hycc parameters
MINIMIZATION_TIME = 0
RERUN = 3
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