#!/usr/bin/env python3
import argparse
import time
from util import *
from benchmark import *

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

def install(features):
    def verify_path_empty(path) -> bool:
        return not os.path.isdir(path) or (os.path.isdir(path) and not os.listdir(path)) 

    if "hycc" in features:
        if verify_path_empty(ABY_SOURCE):
            subprocess.run(["git", "submodule", "update", "--init", "--remote", "modules/ABY"])

        if verify_path_empty(HYCC_SOURCE):
            subprocess.run(["git", "submodule", "update", "--init", "--remote", "modules/HyCC"])

    if "circ" in features:        
        if verify_path_empty(CIRC_SOURCE):
            subprocess.run(["git", "submodule", "update", "--init", "--remote", "modules/circ"])

    # install python requirements
    subprocess.run(["pip3", "install", "-r", "requirements.txt"])

def build(features):
    install(features)

    # build hycc
    subprocess.run(["./scripts/build_hycc.zsh"], check=True)

    # install hycc aby dependency
    if not os.path.isdir(ABY_HYCC_DIR):
        subprocess.run(["cp", "-r", ABY_HYCC, ABY_HYCC_DIR], check=True)
        with open(ABY_CMAKE,'a') as f:
            print("add_subdirectory(aby-hycc)", file=f)

    # build aby
    subprocess.run(["./scripts/build_aby.zsh"], check=True)


def benchmark(features):
    make_test_results()

    if "hycc" in features:
        # run hycc benchmarks
        start = time.time()
        benchmark_hycc_biomatch()
        end = time.time()
        
        line = "Total benchmark time: {}".format(end-start)
        print(line)
        write_to_both(line)

    if "circ" in features:
        start = time.time()
        
        # TODO: run circ benchmarks
        benchmark_circ_biomatch()

        end = time.time()
        line = "Total benchmark time: {}".format(end-start)
        print(line)
        write_to_both(line)

def set_features(features):
    if "none" in features:
        features = set()

    def verify_feature(f):
        if f in valid_features:
            return True
        return False
    features = set(sorted([f for f in features if verify_feature(f)]))
    save_features(features)
    print("Feature set:", sorted(list(features)))
    return features

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
    parser.add_argument("-f", "--features", nargs="+", help="set features <circ, hycc>, reset features with -F none")
    parser.add_argument("-l", "--list", action="store_true", help="list features")
    parser.add_argument("-c", "--clean", action="store_true", help="remove all generated files")
    parser.add_argument("--delete", action="store_true", help="Reinstall submodules")
    args = parser.parse_args()


    def verify_single_action(args: argparse.Namespace):
        actions = [k for k, v in vars(args).items() if (type(v) is bool or k in ["features"]) and bool(v)]
        if len(actions) != 1:
            parser.error("parser error: only one action can be specified. got: " + " ".join(actions))
    verify_single_action(args)

    features = load_features()

    if args.install:
        install(features)

    if args.build:
        build(features)

    if args.test:
        test()

    if args.benchmark:
        benchmark(features)
        
    if args.features:
        features = set_features(args.features)

    if args.list:
        print("Features:", sorted(list(features)))

    if args.clean:
        clean()

    if args.delete:
        delete()