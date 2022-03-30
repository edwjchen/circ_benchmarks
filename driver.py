#!/usr/bin/env python3

import os
import argparse
import subprocess

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
MINIMIZATION_TIME = 0
MODULE_BUNDLE=HYCC_SOURCE+"/src/circuit-utils/py/module_bundle.py"
SELECTION=HYCC_SOURCE+"/src/circuit-utils/py/selection.py"
COSTS=HYCC_SOURCE+"/src/circuit-utils/py/costs.json"

def make_tmp():
    subprocess.run(["mkdir", "-p", "tmp"])

def remove_tmp():
    subprocess.run(["rm", "-rf", "tmp"])

def build_mpc_circuit(test_path, args=[]):
    os.chdir(TMP_PATH)
    cmd = [PARENT_DIR+CBMC_GC, test_path, "--minimization-time-limit", str(MINIMIZATION_TIME)] + args
    subprocess.run(cmd, check=True)
    os.chdir(PARENT_DIR)

def optimize_selection(costs_path=COSTS):
    os.chdir(TMP_PATH)
    subprocess.run(["python3", PARENT_DIR+MODULE_BUNDLE, "."], check=True)
    subprocess.run(["python3", PARENT_DIR+SELECTION, ".", PARENT_DIR+costs_path], check=True)
    os.chdir(PARENT_DIR)

def run_sim(spec_file):
    os.chdir(TMP_PATH)
    cmd = [PARENT_DIR+CIRCUIT_SIM, MPC_CIRC, "--spec-file", PARENT_DIR+spec_file]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    assert("is valid" in result.stdout)
    os.chdir(PARENT_DIR)
    
def run_aby(spec_file, args=[]):
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

def run_aby_sim(spec_file):
    run_aby(spec_file, [MPC_CIRC])

def run_yaoonly(spec_file):
    run_aby(spec_file, ["-c", "yaoonly.cmb"])

def run_yaohybrid(spec_file):
    run_aby(spec_file, ["-c", "yaohybrid.cmb"])

def run_gmwonly(spec_file):
    run_aby(spec_file, ["-c", "gmwonly.cmb"])

def run_gmwhyrbid(spec_file):
    run_aby(spec_file, ["-c", "gmwhybrid.cmb"])

def run_optimized(spec_file):
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
        print("Compilation of all_benchmarks failed with args: " + ", ".join(args))

    remove_tmp()

def benchmark_hycc_biomatch():
    test_path = PARENT_DIR + HYCC_SOURCE + "/examples/benchmarks/biomatch/biomatch.c"
    spec_file = "tests/hycc/biomatch_1.spec"

    # benchmark cbmc-gc benchmarks 
    run_benchmark(test_path, spec_file)

    # benchmark cbmc-gc benchmarks 
    args=["--all-variants"]
    run_all_benchmarks(test_path, spec_file, args)

    args=["--all-variants", "--outline"]
    run_all_benchmarks(test_path, spec_file, args)

# ad hoc testing 
def test():
    make_tmp()
    test_path = PARENT_DIR + HYCC_SOURCE + "/examples/benchmarks/biomatch/biomatch.c"
    spec_file = "tests/hycc/biomatch_1.spec"
    args = ["--all-variants"]
    build_mpc_circuit(test_path, args)
    optimize_selection()
    run_yaoonly(spec_file)
    remove_tmp()

#####################################################################

def install():
    def verify_path_empty(path) -> bool:
        return not os.path.isdir(path) or (os.path.isdir(path) and not os.listdir(path)) 

    if verify_path_empty(ABY_SOURCE):
        subprocess.run(["git", "submodule", "init", "modules/ABY"])
        subprocess.run(["git", "submodule", "update"])

    if verify_path_empty(HYCC_SOURCE):
        subprocess.run(["git", "submodule", "init", "modules/HyCC"])
        subprocess.run(["git", "submodule", "update"])

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
            print("add_subdirectory(aby-hycc)",file=f)

    # build aby
    subprocess.run(["./scripts/build_aby.zsh"], check=True)

def benchmark():
    build()

    # run hycc benchmarks
    benchmark_hycc_biomatch()

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