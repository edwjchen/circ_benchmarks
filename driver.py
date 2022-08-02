#!/usr/bin/env python3
import argparse
import time
from util import *
from benchmark import *

# ad hoc testing


def test():
    test_path = HYCC_SOURCE + \
        "/examples/benchmarks/mnist/mnist.c"
    spec_file = CIRC_BENCHMARK_SOURCE+"specs/mnist.spec"
    args = []

    make_dir("tmp")
    os.chdir("tmp")
    cmd = [CBMC_GC, test_path,
           "--minimization-time-limit", str(MINIMIZATION_TIME)] + args
    print(" ".join(cmd))
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    os.chdir("..")

    os.chdir("tmp")
    cmd = [CIRCUIT_SIM, MPC_CIRC,
           "--spec-file", spec_file]
    print(" ".join(cmd))
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    os.chdir("..")
    print(result.stdout)
    remove_tmp()

#####################################################################


def install(features):
    def verify_path_empty(path) -> bool:
        return not os.path.isdir(path) or (os.path.isdir(path) and not os.listdir(path))

    if verify_path_empty(ABY_SOURCE):
        subprocess.run(["git", "submodule", "update",
                       "--init", "--remote", "modules/ABY"])

    if verify_path_empty(KAHIP_SOURCE):
        subprocess.run(["git", "submodule", "update",
                       "--init", "--remote", "modules/KaHIP"])

    if "hycc" in features:
        if verify_path_empty(HYCC_SOURCE):
            subprocess.run(["git", "submodule", "update",
                           "--init", "--remote", "modules/HyCC"])

    if "circ" in features:
        if verify_path_empty(CIRC_SOURCE):
            subprocess.run(["git", "submodule", "update",
                           "--init", "--remote", "modules/circ"])

    # install python requirements
    subprocess.run(["pip3", "install", "-r", "requirements.txt"])


def build(features):
    install(features)

    # build hycc
    subprocess.run(["./scripts/build_hycc.zsh"], check=True)

    # install hycc aby dependency
    if not os.path.isdir(ABY_HYCC_DIR):
        subprocess.run(["cp", "-r", ABY_HYCC, ABY_HYCC_DIR], check=True)
        with open(ABY_CMAKE, 'a') as f:
            print("add_subdirectory(aby-hycc)", file=f)

    # build aby
    subprocess.run(["./scripts/build_aby.zsh"], check=True)

    # build kahip
    subprocess.run(["./scripts/build_kahip.zsh"], check=True)


def benchmark(features):
    build(features)
    make_test_results()
    make_dir(HYCC_CIRCUIT_PATH)
    if "hycc" in features:
        print("Running hycc Benchmarks")
        start = time.time()
        test_cases = [
            ("biomatch", "biomatch/biomatch.c"),
            ("kmeans", "kmeans/kmeans.c"),
            # ("gauss", "gauss/gauss.c"),
            # ("db_join", "db/db_join.c"),
            # ("db_join2", "db/db_join2.c"),
            # ("db_merge", "db/db_merge.c"),
            # ("mnist", "mnist/mnist.c"),
            # ("mnist_decomp_main", "mnist/mnist_decomp_main.c"),
            # ("mnist_decomp_convolution", "mnist/mnist_decomp_convolution.c"),
            # ("cryptonets", "cryptonets/cryptonets.c"),
        ]
        # run hycc benchmarks
        for (name, path) in test_cases:
            benchmark_hycc(name, path)
        end = time.time()
        line = "LOG: Total hycc benchmark time: {}".format(end-start)
        write_log(line, "hycc_total_time")

    if "circ" in features:
        global VERSION
        VERSION = "{}_biomatch_is-{}_np-{}_ml-{}_mss-{}_cm-{}".format(
            "circ", SIZE, NUM_PARTS, MUT_LEVEL, MUT_STEP_SIZE, COST_MODEL)
        log_path = format("test_results/log_{}.txt".format(VERSION))
        if os.path.exists(log_path):
            print("Benchmark already ran: {}".format(log_path))
            return

        print("Running circ Benchmarks")
        # run circ benchmarks
        start = time.time()
        benchmark_circ_biomatch()
        end = time.time()

        line = "Total circ benchmark time: {}".format(end-start)
        print(line)
        write_to_both(line)

        parse_circ_log(log_path)


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
    parser.add_argument("-i", "--install", action="store_true",
                        help="install all dependencies")
    parser.add_argument("-b", "--build", action="store_true",
                        help="build depedencies")
    parser.add_argument("-t", "--test", action="store_true", help="adhoc test")
    parser.add_argument("--benchmark", action="store_true",
                        help="run benchmark")
    parser.add_argument("-f", "--features", nargs="+",
                        help="set features <circ, hycc>, reset features with -F none")
    parser.add_argument("-l", "--list", action="store_true",
                        help="list features")
    parser.add_argument("-c", "--clean", action="store_true",
                        help="remove all generated files")
    parser.add_argument("--delete", action="store_true",
                        help="Reinstall submodules")
    args = parser.parse_args()

    def verify_single_action(args: argparse.Namespace):
        actions = [k for k, v in vars(args).items() if (
            type(v) is bool or k in ["features"]) and bool(v)]
        if len(actions) != 1:
            parser.error(
                "parser error: only one action can be specified. got: " + " ".join(actions))
    verify_single_action(args)

    features = load_features()
    assert args.features or args.list or len(features) == 1, "Only 1 feature at a time, features: {}".format(features)

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
