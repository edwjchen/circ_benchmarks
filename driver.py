#!/usr/bin/env python3

import argparse
import os
import subprocess
import time

# installation variables
ABY_SOURCE = "./modules/ABY"
HYCC_SOURCE = "./modules/HyCC"
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

MINIMIZATION_TIME = 0
RERUN = 3

# logging variables
VERSION_NUM = 0
LOG_PATH = ""
RUN_PATH = ""
DELIMITER = "\n====================================\n"

def make_tmp():
    subprocess.run(["mkdir", "-p", "tmp"])

def remove_tmp():
    subprocess.run(["rm", "-rf", "tmp"])

def build_mpc_circuit(test_path, args=[]):
    os.chdir(TMP_PATH)
    cmd = [PARENT_DIR+CBMC_GC, test_path, "--minimization-time-limit", str(MINIMIZATION_TIME)] + args
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    os.chdir(PARENT_DIR)
    write_output_to_log(result.stdout)
    write_to_run(result.stdout)

def optimize_selection(costs_path=COSTS):
    os.chdir(TMP_PATH)
    subprocess.run(["python3", PARENT_DIR+MODULE_BUNDLE, "."], check=True)
    subprocess.run(["python3", PARENT_DIR+SELECTION, ".", PARENT_DIR+costs_path], check=True)
    os.chdir(PARENT_DIR)

def run_sim(spec_file):
    for i in range(RERUN):
        write_to_log("Using CIRCUIT-SIM")
        write_to_log("RERUN: {}".format(i))
        os.chdir(TMP_PATH)
        cmd = [PARENT_DIR+CIRCUIT_SIM, MPC_CIRC, "--spec-file", PARENT_DIR+spec_file]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        os.chdir(PARENT_DIR)

        write_output_to_log(result.stdout)
        write_to_run(result.stdout)
    
def run_aby(spec_file, args=[]):
    for i in range(RERUN):
        write_to_log("Using ABY-HYCC")
        write_to_log("RERUN: {}".format(i))
        os.chdir(TMP_PATH)
        cmd = [PARENT_DIR+ABY_CBMC_GC, "--spec-file", PARENT_DIR+spec_file] + args
        server_cmd = cmd + ["-r", "0"]
        client_cmd = cmd + ["-r", "1"]
        server_proc = subprocess.Popen(server_cmd, stdout=subprocess.PIPE)
        client_proc = subprocess.Popen(client_cmd, stdout=subprocess.PIPE)
        _server_out, _server_errs = server_proc.communicate()
        _client_out, _client_errs = client_proc.communicate()

        server_out = _server_out.decode("utf-8")
        client_out = _client_out.decode("utf-8")

        os.chdir(PARENT_DIR)

        write_output_to_log(server_out)
        write_to_run(server_out)
        write_output_to_log(client_out)
        write_to_run(client_out)

def run_aby_sim(spec_file):
    run_aby(spec_file, [MPC_CIRC])

def run_yaoonly(spec_file):
    write_to_both("Running yaonly")
    run_aby(spec_file, ["-c", "yaoonly.cmb"])

def run_yaohybrid(spec_file):
    write_to_both("Running yaohybrid")
    run_aby(spec_file, ["-c", "yaohybrid.cmb"])

def run_gmwonly(spec_file):
    write_to_both("Running gmwonly")
    run_aby(spec_file, ["-c", "gmwonly.cmb"])

def run_gmwhyrbid(spec_file):
    write_to_both("Running gmwhybrid")
    run_aby(spec_file, ["-c", "gmwhybrid.cmb"])

def run_optimized(spec_file):
    write_to_both("Running ps_optimized")
    run_aby(spec_file, ["-c", "ps_optimized.cmb"])

def run_benchmark(test_path, spec_file, args=[]):
    make_tmp()

    # build benchmarks 
    build_mpc_circuit(test_path, args)

    # run benchmarks
    run_sim(spec_file)
    run_aby_sim(spec_file)

    remove_tmp()

def run_all_benchmarks(test_path, spec_file, args=[]):
    make_tmp()

    # build benchmarks
    try: 
        # compilation to arithmetic circuits is not always possible
        build_mpc_circuit(test_path, args)
        optimize_selection()

        # run benchmarks 
        run_yaoonly(spec_file)
        run_yaohybrid(spec_file)
        run_gmwonly(spec_file)
        run_gmwhyrbid(spec_file)
        run_optimized(spec_file)
    except: 
        if os.getcwd().endswith("tmp"):
            os.chdir(PARENT_DIR)
        write_to_both("Compilation of all_benchmarks failed with args: {}".format(args))
    remove_tmp()

def benchmark_hycc_biomatch():
    test_path = PARENT_DIR + HYCC_SOURCE + "/examples/benchmarks/biomatch/biomatch.c"
    spec_file = "tests/hycc/biomatch_1.spec"
    make_test_results()

    write_to_both("TEST PATH: {}".format(test_path))
    write_to_both("SPEC_FILE: {}".format(spec_file))
    write_to_both("MINIMIZATION TIME: {}".format(MINIMIZATION_TIME))
    write_to_both(DELIMITER)

    # benchmark cbmc-gc benchmarks 
    run_benchmark(test_path, spec_file)
    write_to_both(DELIMITER)

    # benchmark cbmc-gc benchmarks 
    args=["--all-variants"]
    write_to_both("Running with args: {}".format(args))
    run_all_benchmarks(test_path, spec_file, args)
    write_to_both(DELIMITER)

    args=["--all-variants", "--outline"]
    write_to_both("Running with args: {}".format(args))
    run_all_benchmarks(test_path, spec_file, args)
    write_to_both(DELIMITER)

# ad hoc testing 
def test():
    test_path = PARENT_DIR + HYCC_SOURCE + "/examples/benchmarks/biomatch/biomatch.c"
    spec_file = "tests/hycc/biomatch_1.spec"
    args = []

    os.chdir(TMP_PATH)
    cmd = [PARENT_DIR+CBMC_GC, test_path, "--minimization-time-limit", str(MINIMIZATION_TIME)] + args
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    os.chdir(PARENT_DIR)

    os.chdir(TMP_PATH)
    cmd = [PARENT_DIR+CIRCUIT_SIM, MPC_CIRC, "--spec-file", PARENT_DIR+spec_file]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    os.chdir(PARENT_DIR)
    
    print(result.stdout)

#####################################################################

# Logging results
def make_test_results():
    subprocess.run(["mkdir", "-p", "test_results"])

    for _base, _dirs, files in os.walk("./test_results"):
        VERSION_NUM = len(files) // 2

    global LOG_PATH
    global RUN_PATH
    LOG_PATH = "test_results/log_{}.txt".format(VERSION_NUM)
    RUN_PATH = "test_results/run_{}.txt".format(VERSION_NUM)
    subprocess.run(["touch", LOG_PATH])
    subprocess.run(["touch", RUN_PATH])

def write_output_to_log(text):
    lines = text.split("\n")
    for line in lines:
        clean_line = line.strip()
        if clean_line.startswith("LOG:"):
            write_to_log(clean_line)

def write_to_log(text):
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, "a") as f:
            f.write(text + "\n")
    else:
        print("pwd: {}".format(os.getcwd()))
        raise Exception("Path not found: {}".format(LOG_PATH))

def write_to_run(text):
    if os.path.exists(RUN_PATH):
        with open(RUN_PATH, "a") as f:
            f.write(text + "\n")
    else:
        print("pwd: {}".format(os.getcwd()))
        raise Exception("Path not found: {}".format(RUN_PATH))

def write_to_both(text):
    write_to_log(text)
    write_to_run(text)

#####################################################################

def install():
    def verify_path_empty(path) -> bool:
        return not os.path.isdir(path) or (os.path.isdir(path) and not os.listdir(path)) 

    if verify_path_empty(ABY_SOURCE):
        subprocess.run(["git", "submodule", "init", "modules/ABY"])
        subprocess.run(["git", "submodule", "update", "--remote", "modules/ABY"])

    if verify_path_empty(HYCC_SOURCE):
        subprocess.run(["git", "submodule", "init", "modules/HyCC"])
        subprocess.run(["git", "submodule", "update", "--remote", "modules/HyCC"])

    # install python requirements
    subprocess.run(["pip3", "install", "-r", "requirements.txt"])

def build():
    install()

    # build hycc
    subprocess.run(["./scripts/build_hycc.zsh"], check=True)

    # install hycc aby dependency
    if not os.path.isdir(ABY_HYCC_DIR):
        subprocess.run(["cp", "-r", ABY_HYCC, ABY_HYCC_DIR], check=True)
        with open(ABY_CMAKE,'a') as f:
            print("add_subdirectory(aby-hycc)", file=f)

    # build aby
    subprocess.run(["./scripts/build_aby.zsh"], check=True)

def benchmark():
    build()
    # run hycc benchmarks
    start = time.time()
    benchmark_hycc_biomatch()
    end = time.time()
    
    line = "Total benchmark time: {}".format(end-start)
    print(line)
    write_to_both(line)

def clean():
    print("cleaning")
    subprocess.run(["./scripts/clean_aby.zsh"], check=True)
    subprocess.run(["./scripts/clean_hycc.zsh"], check=True)

def delete():
    print("fresh install!")
    subprocess.run(["rm", "-rf", "modules/ABY"])
    subprocess.run(["rm", "-rf", "modules/HyCC"])

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--install", action="store_true", help="install all dependencies")
    parser.add_argument("-b", "--build", action="store_true", help="build depedencies")
    parser.add_argument("-t", "--test", action="store_true", help="test")
    parser.add_argument("--benchmark", action="store_true", help="benchmark hycc")
    parser.add_argument("-c", "--clean", action="store_true", help="remove all generated files")
    parser.add_argument("--delete", action="store_true", help="Reinstall submodules")
    args = parser.parse_args()


    def verify_single_action(args: argparse.Namespace):
        actions = [k for k, v in vars(args).items() if (type(v) is bool or k in ["features"]) and bool(v)]
        if len(actions) != 1:
            parser.error("parser error: only one action can be specified. got: " + " ".join(actions))
    verify_single_action(args)

    if args.install:
        install()

    if args.build:
        build()

    if args.test:
        test()

    if args.benchmark:
        benchmark()

    if args.clean:
        clean()

    if args.delete:
        delete()