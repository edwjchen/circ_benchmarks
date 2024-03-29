import json
import subprocess
import os

feature_path = ".features.txt"
valid_features = {"circ", "hycc"}
instance_metadata_path = ".instance_metadata.txt"

TIME_CMD = "/usr/bin/time --format='%e seconds %M kB'"
TIMEOUT = 60 * 60 * 24 # one day 

# installation variables
# TODO: update CIRC_BENCHMARK_SOURCE path
CIRC_BENCHMARK_SOURCE = os.getcwd() + "/"
ABY_SOURCE = CIRC_BENCHMARK_SOURCE+"modules/ABY"
HYCC_SOURCE = CIRC_BENCHMARK_SOURCE+"modules/HyCC"
CIRC_SOURCE = CIRC_BENCHMARK_SOURCE+"modules/circ"
KAHIP_SOURCE = CIRC_BENCHMARK_SOURCE+"modules/KaHIP"
KAHYPAR_SOURCE = CIRC_BENCHMARK_SOURCE+"modules/kahypar"


ABY_HYCC = HYCC_SOURCE+"/aby-hycc"
ABY_HYCC_DIR = ABY_SOURCE + "/src/examples/aby-hycc/"
ABY_CMAKE = ABY_SOURCE + "/src/examples/CMakeLists.txt"

# benchmark variables
HYCC_CIRCUIT_PATH = CIRC_BENCHMARK_SOURCE+"hycc_circuit_dir/"
CBMC_GC = HYCC_SOURCE + "/bin/cbmc-gc"
CIRCUIT_SIM = HYCC_SOURCE + "/bin/circuit-sim"
ABY_CBMC_GC = ABY_SOURCE + "/build/bin/aby-hycc"
MPC_CIRC = "mpc_main.circ"
MODULE_BUNDLE = HYCC_SOURCE+"/src/circuit-utils/py/module_bundle.py"
SELECTION = HYCC_SOURCE+"/src/circuit-utils/py/selection.py"

CIRC_CIRCUIT_PATH = CIRC_BENCHMARK_SOURCE+"circ_circuit_dir/"
CIRC_TARGET = CIRC_SOURCE + "/target/release/examples/circ"
ABY_INTERPRETER = ABY_SOURCE + "/build/bin/aby_interpreter"

# joint parameters
RERUN = 1
COST_MODELS = ["hycc"]
# TODO: if more cost models are added, need to give hycc the path to the json
COSTS = HYCC_SOURCE+"/src/circuit-utils/py/costs.json"


# hycc parameters
HYCC_TEST_CASES = [
    ("biomatch", "biomatch/biomatch.c"),
    # ("kmeans", "kmeans/kmeans.c"),
    # ("gauss", "gauss/gauss.c"),
    # ("db_join", "db/db_join.c"),
    # ("db_join2", "db/db_join2.c"),
    # ("db_merge", "db/db_merge.c"),
    # ("mnist", "mnist/mnist.c"),
    # ("mnist_decomp_main", "mnist/mnist_decomp_main.c"),
    # ("mnist_decomp_convolution", "mnist/mnist_decomp_convolution.c"),
    # ("cryptonets", "cryptonets/cryptonets.c"),
    # TODO: add histogram
]

MINIMIZATION_TIMES = [0, 600]
HYCC_SELECTION_SCHEMES = [
    "yaoonly",
    "yaohybrid",
    "gmwonly",
    "gmwhybrid",
    "ps_optimized"
]
HYCC_COMPILE_ARGUMENTS = [
    ["--all-variants"],
    # ["--all-variants", "--outline"]
]

# circ parameters
CIRC_TEST_CASES = [
    "biomatch",
    # "kmeans",
    # "gauss",
    # "db_join",
    # "db_join2",
    # "db_merge",
    # "mnist",
    # "mnist_decomp_main",
    # "mnist_decomp_convolution",
    # "cryptonets",
    # "histogram",
]

CIRC_NO_PARTITION_SELECTION_SCHEMES = [
    "b",
    "y",
    "a+b",
    "a+y",
    "greedy",
    "smart_glp",
]
CIRC_PARTITION_SELECTION_SCHEMES = [
    "css",
    "smart_lp",
]
PARTITIONERS = [
    0, # KaHIP
    # 1 # KaHyPar
]
PARTITION_SIZES = [1000, 3000, 5000]
MUT_LEVELS = [1, 2, 4]
MUT_STEP_SIZES = [1, 2, 4]



# logging variables
DELIMITER = "\nLOG: ====================================\n"


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


def save_instance_metadata(data):
    """ Save address to file """
    with open(instance_metadata_path, 'w') as f:
        json.dump(data, f)


def load_instance_metadata():
    """ Load features from file """
    if os.path.exists(instance_metadata_path):
        with open(instance_metadata_path, 'r') as f:
            return json.load(f)
    else:
        return {}


def make_dir(path):
    subprocess.run(["mkdir", "-p", path])


def remove_tmp():
    subprocess.run(["rm", "-rf", "tmp"])


def make_test_results():
    subprocess.run(["mkdir", "-p", "test_results"])

###############################################################################
# Logging
###############################################################################


def wrap_time(cmd):
    return TIME_CMD + " " + cmd


def run_cmds(server_cmd, client_cmd, name, params):
    write_log("LOG: {}".format(name), params)
    cmd = "{} & {}".format(" ".join(server_cmd), " ".join(client_cmd))
    print(cmd)
    cmd = wrap_time(cmd)
    proc = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()

    if proc.returncode:
        write_log("LOG: Error: Process returned with status code {}".format(
            proc.returncode), params)
        write_log("LOG: Error message: {}".format(
            " ".join(stderr.decode("utf-8").split("\n"))), params)
        return

    # record server
    out = stdout.decode("utf-8")
    write_log(out, params)

    err = stderr.decode("utf-8")
    last_line = [l for l in err.split("\n") if l][-1]
    memory_output = "LOG: Time / Memory: {}".format(last_line)
    write_log(memory_output, params)


def run_cmd(cmd, name, params):
    write_log("LOG: {}".format(name), params)
    cmd = wrap_time(" ".join(cmd))
    proc = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate(timeout=TIMEOUT)

    if proc.returncode:
        write_log("LOG: Error: Process returned with status code {}".format(
            proc.returncode), params)
        write_log("LOG: Error message: {}".format(
            " ".join(stderr.decode("utf-8").split("\n"))), params)
        raise RuntimeError

    # record stdout
    out = stdout.decode("utf-8")
    write_log(out, params)

    # record stderr
    err = stderr.decode("utf-8")
    last_line = [l for l in err.split("\n") if l][-1]
    memory_output = "LOG: Time / Memory: {}".format(last_line)
    write_log(memory_output, params)


def write_to_log(text, params):
    dir_path = "{}test_results/{}_{}/".format(
        CIRC_BENCHMARK_SOURCE, params["system"], params["name"])
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

    log_path = "{}test_results/{}_{}/log_{}.txt".format(
        CIRC_BENCHMARK_SOURCE, params["system"], params["name"], params["phase_version"])
    if not os.path.exists(log_path):
        subprocess.run(["touch", log_path])

    lines = text.split("\n")
    for line in lines:
        clean_line = line.strip()
        if clean_line.startswith("LOG:"):
            with open(log_path, "a") as f:
                f.write(clean_line + "\n")


def write_to_run(text, params):
    dir_path = "{}test_results/{}_{}/".format(
        CIRC_BENCHMARK_SOURCE, params["system"], params["name"])
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

    run_path = "{}test_results/{}_{}/run_{}.txt".format(
        CIRC_BENCHMARK_SOURCE, params["system"], params["name"], params["phase_version"])
    if not os.path.exists(run_path):
        subprocess.run(["touch", run_path])

    with open(run_path, "a") as f:
        f.write(text + "\n")


def write_log(text, params):
    write_to_log(text, params)
    write_to_run(text, params)


####################
# CirC Helpers
####################

def get_circ_build_path(name):
    if name == "biomatch":
        return "{}/examples/C/mpc/benchmarks/biomatch/biomatch.c".format(CIRC_SOURCE)
    if name == "kmeans":
        return "{}/examples/C/mpc/benchmarks/kmeans/2pc_kmeans_.c".format(CIRC_SOURCE)
    if name == "gauss":
        return "{}/examples/C/mpc/benchmarks/gauss/2pc_gauss_inline.c".format(CIRC_SOURCE)
    if name == "db_join":
        return "{}/examples/C/mpc/benchmarks/db/db_join.c".format(CIRC_SOURCE)
    if name == "db_join2":
        return "{}/examples/C/mpc/benchmarks/db/db_join2.c".format(CIRC_SOURCE)
    if name == "db_merge":
        return "{}/examples/C/mpc/benchmarks/db/db_merge.c".format(CIRC_SOURCE)
    if name == "mnist":
        return "{}/examples/C/mpc/benchmarks/mnist/mnist.c".format(CIRC_SOURCE)
    if name == "mnist_decomp_main":
        return "{}/examples/C/mpc/benchmarks/mnist/mnist_decomp_main.c".format(CIRC_SOURCE)
    if name == "mnist_decomp_convolution":
        return "{}/examples/C/mpc/benchmarks/mnist/mnist_decomp_convolution.c".format(CIRC_SOURCE)
    if name == "cryptonets":
        return "{}/examples/C/mpc/benchmarks/cryptonets/cryptonets.c".format(CIRC_SOURCE)
    if name == "histogram":
        return "{}/examples/C/mpc/benchmarks/histogram/histogram.c".format(CIRC_SOURCE)
    raise RuntimeError("Could not find test: {}".format(name))


def get_circ_bytecode_path(name):
    if name == "biomatch":
        return "{}/scripts/aby_tests/tests/biomatch_c".format(CIRC_SOURCE)
    if name == "kmeans":
        return "{}/scripts/aby_tests/tests/2pc_kmeans__c".format(CIRC_SOURCE)
    if name == "gauss":
        return "{}/scripts/aby_tests/tests/2pc_gauss_inline_c".format(CIRC_SOURCE)
    if name == "db_join":
        return "{}/scripts/aby_tests/tests/db_join_c".format(CIRC_SOURCE)
    if name == "db_join2":
        return "{}/scripts/aby_tests/tests/db_join2_c".format(CIRC_SOURCE)
    if name == "db_merge":
        return "{}/scripts/aby_tests/tests/db_merge_c".format(CIRC_SOURCE)
    if name == "mnist":
        return "{}/scripts/aby_tests/tests/mnist_c".format(CIRC_SOURCE)
    if name == "mnist_decomp_main":
        return "{}/scripts/aby_tests/tests/mnist_decomp_main_c".format(CIRC_SOURCE)
    if name == "mnist_decomp_convolution":
        return "{}/scripts/aby_tests/tests/mnist_decomp_convolution_c".format(CIRC_SOURCE)
    if name == "cryptonets":
        return "{}/scripts/aby_tests/tests/cryptonets_c".format(CIRC_SOURCE)
    if name == "histogram":
        return "{}/scripts/aby_tests/tests/histogram_c".format(CIRC_SOURCE)
    raise RuntimeError("Could not find test: {}".format(name))


def get_circ_input_path(name):
    if name == "biomatch":
        return "{}/scripts/aby_tests/test_inputs/biomatch_1.txt".format(CIRC_SOURCE)
    if name == "kmeans":
        return "{}/scripts/aby_tests/test_inputs/kmeans.txt".format(CIRC_SOURCE)
    if name == "gauss":
        return "{}/scripts/aby_tests/test_inputs/gauss.txt".format(CIRC_SOURCE)
    if name == "db_join":
        return "{}/scripts/aby_tests/test_inputs/db_join.txt".format(CIRC_SOURCE)
    if name == "db_join2":
        return "{}/scripts/aby_tests/test_inputs/join2.txt".format(CIRC_SOURCE)
    if name == "db_merge":
        return "{}/scripts/aby_tests/test_inputs/merge.txt".format(CIRC_SOURCE)
    if name == "mnist":
        return "{}/scripts/aby_tests/test_inputs/mnist.txt".format(CIRC_SOURCE)
    if name == "mnist_decomp_main":
        return "{}/scripts/aby_tests/test_inputs/mnist_decomp_main.txt".format(CIRC_SOURCE)
    if name == "mnist_decomp_convolution":
        return "{}/scripts/aby_tests/test_inputs/mnist_decomp_convolution.txt".format(CIRC_SOURCE)
    if name == "cryptonets":
        return "{}/scripts/aby_tests/test_inputs/cryptonets.txt".format(CIRC_SOURCE)
    if name == "histogram":
        return "{}/scripts/aby_tests/test_inputs/histogram.txt".format(CIRC_SOURCE)
    raise RuntimeError("Could not find test: {}".format(name))


def get_circ_test_path(name, version):
    if name == "biomatch":
        return "{}/{}/biomatch_c".format(CIRC_CIRCUIT_PATH, version)
    if name == "kmeans":
        return "{}/{}/2pc_kmeans__c".format(CIRC_CIRCUIT_PATH, version)
    if name == "gauss":
        return "{}/{}/2pc_gauss_inline_c".format(CIRC_CIRCUIT_PATH, version)
    if name == "db_join":
        return "{}/{}/db_join_c".format(CIRC_CIRCUIT_PATH, version)
    if name == "db_join2":
        return "{}/{}/db_join2_c".format(CIRC_CIRCUIT_PATH, version)
    if name == "db_merge":
        return "{}/{}/db_merge_c".format(CIRC_CIRCUIT_PATH, version)
    if name == "mnist":
        return "{}/{}/mnist_c".format(CIRC_CIRCUIT_PATH, version)
    if name == "mnist_decomp_main":
        return "{}/{}/mnist_decomp_main_c".format(CIRC_CIRCUIT_PATH, version)
    if name == "mnist_decomp_convolution":
        return "{}/{}/mnist_decomp_convolution_c".format(CIRC_CIRCUIT_PATH, version)
    if name == "cryptonets":
        return "{}/{}/cryptonets_c".format(CIRC_CIRCUIT_PATH, version)
    if name == "histogram":
        return "{}/{}/histogram_c".format(CIRC_CIRCUIT_PATH, version)
    raise RuntimeError("Could not find test: {}".format(name))
