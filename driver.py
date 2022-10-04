#!/usr/bin/env python3
import argparse
import time
from util import *
from benchmark import *
from parser import *
import sys


def test():
    # ad hoc testing
    test_path = HYCC_SOURCE + \
        "/examples/benchmarks/mnist/mnist.c"
    spec_file = CIRC_BENCHMARK_SOURCE+"specs/mnist.spec"
    args = []

    make_dir("tmp")
    os.chdir("tmp")
    cmd = [CBMC_GC, test_path,
           "--minimization-time-limit", str(0)] + args
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
    subprocess.run(["git", "pull", "--recurse-submodules"])

    def verify_path_empty(path) -> bool:
        return not os.path.isdir(path) or (os.path.isdir(path) and not os.listdir(path))

    if verify_path_empty(ABY_SOURCE):
        subprocess.run(["git", "submodule", "update",
                       "--init", "--remote", "modules/ABY"])

    if "hycc" in features:
        if verify_path_empty(HYCC_SOURCE):
            subprocess.run(["git", "submodule", "update",
                           "--init", "--remote", "modules/HyCC"])

    if "circ" in features:
        if verify_path_empty(CIRC_SOURCE):
            subprocess.run(["git", "submodule", "update",
                           "--init", "--remote", "modules/circ"])

        if verify_path_empty(KAHIP_SOURCE):
            subprocess.run(["git", "submodule", "update",
                            "--init", "--remote", "modules/KaHIP"])

        if verify_path_empty(KAHYPAR_SOURCE):
            subprocess.call("cd {}modules && rm -rf kahypar && git clone --recursive https://github.com/kahypar/kahypar.git && cd kahypar && mkdir build && cd build && cmake .. -DCMAKE_BUILD_TYPE=RELEASE && make".format(CIRC_BENCHMARK_SOURCE), shell=True)

    # set git branches
    os.chdir(ABY_SOURCE)
    # subprocess.run(["git", "checkout", "functions"])
    subprocess.run(["git", "checkout", "no_array"])
    subprocess.run(["git", "pull"], check=True)
    os.chdir(CIRC_BENCHMARK_SOURCE)

    os.chdir(CIRC_SOURCE)
    subprocess.run(["git", "checkout", "mpc_aws"])
    subprocess.run(["git", "pull"], check=True)
    # subprocess.run(["git", "checkout", "function_calls"])
    os.chdir(CIRC_BENCHMARK_SOURCE)

    # export env variables
    os.environ["ABY_SOURCE"] = ABY_SOURCE
    os.environ["KAHIP_SOURCE"] = KAHIP_SOURCE
    os.environ["KAHYPAR_SOURCE"] = KAHYPAR_SOURCE

    # install python requirements
    # subprocess.run(["pip3", "install", "-r", "requirements.txt"])


def build(features):
    subprocess.run(["git", "pull", "--recurse-submodules"])

    def verify_path_empty(path) -> bool:
        return not os.path.isdir(path) or (os.path.isdir(path) and not os.listdir(path))

    if verify_path_empty(ABY_SOURCE):
        subprocess.run(["git", "submodule", "update",
                       "--init", "--remote", "modules/ABY"])

    if "hycc" in features:
        # build hycc
        subprocess.run(["./scripts/build_hycc.zsh"], check=True)

        # install hycc aby dependency
        if not os.path.isdir(ABY_HYCC_DIR):
            subprocess.run(["cp", "-r", ABY_HYCC, ABY_HYCC_DIR], check=True)
            with open(ABY_CMAKE, 'a') as f:
                print("add_subdirectory(aby-hycc)", file=f)

    if "circ" in features:
        # build circ
        os.environ['ABY_SOURCE'] = "../ABY"
        os.environ['CIRC_SOURCE'] = CIRC_SOURCE
        os.chdir(CIRC_SOURCE)
        subprocess.run(["python3", "driver.py", "-F", "aby",
                        "c", "lp", "bench"], check=True)
        subprocess.run(
            ["python3", "driver.py", "--build_benchmark"], check=True)
        os.chdir(CIRC_BENCHMARK_SOURCE)

        # build aby
        subprocess.run(["./scripts/build_aby.zsh"], check=True)

        # build kahip
        subprocess.run(["./scripts/build_kahip.zsh"], check=True)


def build_aby(features):
    subprocess.run(["git", "pull", "--recurse-submodules"])

    def verify_path_empty(path) -> bool:
        return not os.path.isdir(path) or (os.path.isdir(path) and not os.listdir(path))

    if verify_path_empty(ABY_SOURCE):
        subprocess.run(["git", "submodule", "update",
                       "--init", "--remote", "modules/ABY"])

    if verify_path_empty(HYCC_SOURCE):
        subprocess.run(["git", "submodule", "update",
                        "--init", "--remote", "modules/HyCC"])

    # set git branches
    os.chdir(ABY_SOURCE)
    # subprocess.run(["git", "checkout", "functions"])
    subprocess.run(["git", "checkout", "no_array"])
    subprocess.run(["git", "pull"], check=True)
    os.chdir(CIRC_BENCHMARK_SOURCE)

    if "hycc" in features:
        # build hycc
        subprocess.run(["git", "pull"], check=True)
        subprocess.run(["./scripts/build_hycc.zsh"], check=True)

        # install hycc aby dependency
        if not os.path.isdir(ABY_HYCC_DIR):
            subprocess.run(["cp", "-r", ABY_HYCC, ABY_HYCC_DIR], check=True)
            with open(ABY_CMAKE, 'a') as f:
                print("add_subdirectory(aby-hycc)", file=f)

    # build aby
    subprocess.run(["./scripts/build_aby.zsh"], check=True)


def compile(features):
    build(features)
    make_test_results()
    if "hycc" in features:
        print("Compiling HyCC Benchmarks")
        start = time.time()
        make_dir(HYCC_CIRCUIT_PATH)

        # run hycc benchmarks
        for (name, path) in HYCC_TEST_CASES:
            make_dir("test_results/hycc_{}".format(name))
            compile_hycc(name, path)
        end = time.time()
        line = "LOG: Total hycc compile time: {}".format(end-start)
        subprocess.call("echo \"{}\" >> {}/test_results/hycc_total_compile_time.txt".format(
            line, CIRC_BENCHMARK_SOURCE), shell=True)

    if "circ" in features:
        print("Compiling CirC Benchmarks")
        start = time.time()
        make_dir(CIRC_CIRCUIT_PATH)

        # run circ benchmarks
        for name in CIRC_TEST_CASES:
            make_dir("test_results/circ_{}".format(name))
            compile_circ(name)
        end = time.time()
        line = "LOG: Total circ compile time: {}".format(end-start)
        subprocess.call("echo \"{}\" >> {}/test_results/circ_total_compile_time.txt".format(
            line, CIRC_BENCHMARK_SOURCE), shell=True)


def compile_with_params(features):
    build(features)
    make_test_results()
    if "hycc" in features:
        print("Compiling HyCC Benchmarks")
        start = time.time()
        make_dir(HYCC_CIRCUIT_PATH)

        # check params
        if not os.path.exists("./compile_params.json"):
            sys.exit("compile_params.json: file does not exist")

        # compile_hycc
        with open('compile_params.json') as f:
            params = json.load(f)

        make_dir("test_results/hycc_{}".format(params["name"]))
        compile_hycc_with_params(params)
        end = time.time()
        line = "LOG: Total hycc compile time: {}".format(end-start)
        subprocess.call("echo \"{}\" >> {}/test_results/hycc_total_compile_time.txt".format(
            line, CIRC_BENCHMARK_SOURCE), shell=True)


def select(features):
    build(features)
    make_test_results()
    if "hycc" in features:
        print("Selecting HyCC Benchmarks")
        start = time.time()
        make_dir(HYCC_CIRCUIT_PATH)

        # run hycc benchmarks
        for (name, path) in HYCC_TEST_CASES:
            make_dir("test_results/hycc_{}".format(name))
            select_hycc(name)
        end = time.time()
        line = "LOG: Total hycc select time: {}".format(end-start)
        subprocess.call("echo \"{}\" >> {}/test_results/hycc_total_select_time.txt".format(
            line, CIRC_BENCHMARK_SOURCE), shell=True)


def select_with_params(features):
    build(features)
    make_test_results()
    if "hycc" in features:
        print("Selecting HyCC Benchmarks")
        start = time.time()
        make_dir(HYCC_CIRCUIT_PATH)

        # check params
        if not os.path.exists("./compile_params.json"):
            sys.exit("compile_params.json: file does not exist")

        # compile_hycc
        with open('compile_params.json') as f:
            params = json.load(f)

        # run hycc benchmarks
        make_dir("test_results/hycc_{}".format(params["name"]))
        select_hycc(params)
        end = time.time()
        line = "LOG: Total hycc select time: {}".format(end-start)
        subprocess.call("echo \"{}\" >> {}/test_results/hycc_total_select_time.txt".format(
            line, CIRC_BENCHMARK_SOURCE), shell=True)


def benchmark(features, instance_metadata):
    make_dir("run_test_results")
    make_dir(HYCC_CIRCUIT_PATH)
    if "hycc" in features:
        print("Running HyCC Benchmarks")
        start = time.time()

        # run hycc benchmarks
        for (name, path) in HYCC_TEST_CASES:
            make_dir("run_test_results/hycc_{}".format(name))
            benchmark_hycc(name, path, instance_metadata)
        end = time.time()
        line = "LOG: Total hycc benchmark time: {}".format(end-start)
        p = subprocess.Popen("echo \"{}\" >> {}/run_test_results/hycc_total_time.txt".format(
            line, CIRC_BENCHMARK_SOURCE), shell=True)
        p.communicate(timeout=10)

    if "circ" in features:
        print("Running CirC Benchmarks")
        start = time.time()

        # run circ benchmarks
        for name in CIRC_TEST_CASES:
            make_dir("test_results/circ_{}".format(name))
            benchmark_circ(name, instance_metadata)
        end = time.time()
        line = "LOG: Total circ benchmark time: {}".format(end-start)
        p = subprocess.Popen("echo \"{}\" >> {}/test_results/circ_total_time.txt".format(
            line, CIRC_BENCHMARK_SOURCE), shell=True)
        p.communicate(timeout=10)


def parse(features):
    if "hycc" in features:
        print("Parsing hycc logs")
        parse_hycc_logs()

    if "circ" in features:
        print("Parsing circ logs")
        parse_circ_logs()


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
    parser.add_argument("--build_aby", action="store_true",
                        help="build run depedencies")
    parser.add_argument("-t", "--test", action="store_true", help="adhoc test")
    parser.add_argument("--compile", action="store_true",
                        help="compile benchmarks")
    parser.add_argument("--compile_with_params", action="store_true",
                        help="compile benchmarks with params")
    parser.add_argument("--select", action="store_true",
                        help="select benchmarks")
    parser.add_argument("--select_with_params", action="store_true",
                        help="select benchmarks with params")
    parser.add_argument("--benchmark", action="store_true",
                        help="run benchmark")
    parser.add_argument("--parse", action="store_true",
                        help="run parser")
    parser.add_argument("-f", "--features", nargs="+",
                        help="set features <circ, hycc>, reset features with -f none")
    parser.add_argument("-l", "--list", action="store_true",
                        help="list features")
    parser.add_argument("-c", "--clean", action="store_true",
                        help="remove all generated files")
    parser.add_argument("--delete", action="store_true",
                        help="Reinstall submodules")
    parser.add_argument("--address",
                        help="AWS Instance addresses")
    parser.add_argument("--role",
                        help="AWS Instance role")
    parser.add_argument("--setting",
                        help="AWS setting")
    args = parser.parse_args()

    def verify_single_action(args: argparse.Namespace):
        actions = [k for k, v in vars(args).items() if (
            type(v) is bool or k in ["address", "role", "setting", "features"]) and bool(v)]
        if len(actions) != 1:
            parser.error(
                "parser error: only one action can be specified. got: " + " ".join(actions))
    verify_single_action(args)

    features = load_features()
    instance_metadata = load_instance_metadata()

    if args.install:
        install(features)

    if args.build:
        build(features)

    if args.build_aby:
        build_aby(features)

    if args.test:
        test()

    if args.compile:
        compile(features)

    if args.compile_with_params:
        compile_with_params(features)

    if args.select:
        select(features)

    if args.select_with_params:
        select_with_params(features)

    if args.benchmark:
        benchmark(features, instance_metadata)

    if args.parse:
        parse(features)

    if args.features:
        features = set_features(args.features)

    if args.address:
        instance_metadata["address"] = args.address
        save_instance_metadata(instance_metadata)

    if args.role:
        instance_metadata["role"] = args.role
        save_instance_metadata(instance_metadata)

    if args.setting:
        instance_metadata["setting"] = args.setting
        save_instance_metadata(instance_metadata)

    if args.list:
        print("Features:", sorted(list(features)))
        if instance_metadata:
            print("==== Metadata ====")
            for (k, v) in instance_metadata.items():
                print(k, ":", v)

    if args.clean:
        clean()

    if args.delete:
        delete()
