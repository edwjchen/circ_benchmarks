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
MINIMIZATION_TIME = 10

def test():
    test_path = PARENT_DIR + HYCC_SOURCE + "/examples/benchmarks/biomatch/biomatch.c"
    spec_file = "tests/hycc/biomatch_1.spec"
    args = []
    # build_mpc_circuit(test_path, args)
    # run_sim(spec_file)
    run_aby_sim(spec_file)

def make_tmp():
    subprocess.run(["mkdir", "-p", "tmp"])

def remove_tmp():
    subprocess.run(["rm", "-rf", "tmp"])

def build_mpc_circuit(test_path, args=[]):
    os.chdir(TMP_PATH)
    cmd = [PARENT_DIR+CBMC_GC, test_path, "--minimization-time-limit", str(MINIMIZATION_TIME)] + args
    subprocess.run(cmd, check=True)
    os.chdir(PARENT_DIR)

def build_mpc_all(test_path):
    build_mpc_circuit(test_path, ["--all-variants"])

def build_mpc_all_out(test_path):
    build_mpc_circuit(test_path, ["--all-variants", "--outline"])

def run_sim(spec_file):
    cmd = [CIRCUIT_SIM, TMP_PATH+MPC_CIRC, "--spec-file", spec_file]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    assert("is valid" in result.stdout)

def run_aby_sim(spec_file):
    # subprocess.run([ABY_CBMC_GC, TMP_PATH+MPC_CIRC, "--spec-file", spec_file] + ["-r", "0"] + [ABY_CBMC_GC, TMP_PATH+MPC_CIRC, "--spec-file", spec_file] + ["-r", "1"])
    cmd = [ABY_CBMC_GC, TMP_PATH+MPC_CIRC, "--spec-file", spec_file]
    server_cmd = cmd + ["-r", "0"]
    client_cmd = cmd + ["-r", "1"]

    server_proc = subprocess.Popen(server_cmd, stdout=subprocess.PIPE)
    client_proc = subprocess.Popen(client_cmd, stdout=subprocess.PIPE)
    server_outs, server_errs = server_proc.communicate()
    client_outs, client_errs = client_proc.communicate()
    print(server_outs, server_errs)
    print(client_outs, client_errs)

def run_aby(spec_file, args=[]):
    cmd = [ABY_CBMC_GC, "--spec-file", spec_file] + args
    server_cmd = cmd + ["-r", "0"]
    client_cmd = cmd + ["-r", "1"]
    final_cmd = server_cmd + ["&"] + client_cmd
    result = subprocess.run(final_cmd, check=True, capture_output=True, text=True)
    assert("is valid" in result.stdout)

def run_yaoonly(spec_file):
    run_aby(spec_file, ["-c", TMP_PATH+"yaoonly.cmb"])

def run_yaohybrid(spec_file):
    run_aby(spec_file, ["-c", TMP_PATH+"yaohybrid.cmb"])

def run_gmwonly(spec_file):
    run_aby(spec_file, ["-c", TMP_PATH+"gmwonly.cmb"])

def run_gmwhyrbid(spec_file):
    run_aby(spec_file, ["-c", TMP_PATH+"gmwhybrid.cmb"])

def clean_circ(test_dir):
    subprocess.run(["rm", "-f", test_dir+"/*.circ"])

def benchmark_hycc_biomatch():
    make_tmp()

    test_path = PARENT_DIR + HYCC_SOURCE + "/examples/benchmarks/biomatch/biomatch.c"
    spec_file = "tests/hycc/biomatch_1.spec"

    # build cbmc-gc benchmarks 
    build_mpc_circuit(test_path, args)
    run_sim(spec_file)
    run_aby_sim(spec_file)

     
    
    # build all

    # build yao-only

    # build yao-hybrid

    # build gmw-only

    # build gmw-hybrid

    # build optimized 


    pass


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

    benchmark_hycc_biomatch()
    pass

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