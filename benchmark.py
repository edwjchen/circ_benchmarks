from util import *
from subprocess import Popen, PIPE

################################################################################
# Benchmark hycc
################################################################################


def build_mpc_circuit(test_path, version, args=[]):
    write_log(DELIMITER, version)
    cmd = [PARENT_DIR+CBMC_GC, test_path,
           "--minimization-time-limit", str(MINIMIZATION_TIME)] + args
    run_cmd(cmd, "Build circuit time", version)

def bundle_modules(version):
    write_log(DELIMITER, version)
    cmd = ["python3", PARENT_DIR+MODULE_BUNDLE, "."]
    run_cmd(cmd, "Module bundle time", version)


def optimize_selection(version, costs_path=COSTS):
    write_log(DELIMITER, version)
    cmd = ["python3", PARENT_DIR+SELECTION, ".", PARENT_DIR+costs_path]
    run_cmd(cmd, "Selection time", version)


def run_sim(spec_file, version):
    write_log(DELIMITER, version)
    for i in range(RERUN):
        cmd = [PARENT_DIR+CIRCUIT_SIM, MPC_CIRC,
               "--spec-file", PARENT_DIR+spec_file]
        run_cmd(cmd, "CIRCUIT-SIM RERUN {}:".format(i), version)


def run_aby(spec_file, name, version, args=[]):
    write_log(DELIMITER, version)
    for i in range(RERUN):
        cmd = [PARENT_DIR+ABY_CBMC_GC, "--spec-file",
               PARENT_DIR+spec_file] + args
        server_cmd = cmd + ["-r", "0"]
        client_cmd = cmd + ["-r", "1"]
        run_cmds(server_cmd, client_cmd, "{} RERUN {}:".format(name, i), version)


def run_aby_sim(spec_file, version):
    run_aby(spec_file, "ABY-SIM", version, [MPC_CIRC])

def run_yaoonly(spec_file, version):
    if os.path.exists("tmp/yaoonly.cmb"):
        run_aby(spec_file, "yaoonly", version, ["-c", "yaoonly.cmb"])
    else:
        write_log(DELIMITER, version)
        write_log("LOG: Missing: yaoonly.cmb", version)


def run_yaohybrid(spec_file, version):
    if os.path.exists("tmp/yaohybrid.cmb"):
        run_aby(spec_file, "yaohybrid", version, ["-c", "yaohybrid.cmb"])
    else:
        write_log(DELIMITER, version)
        write_log("LOG: Missing: yaohybrid.cmb", version)


def run_gmwonly(spec_file, version):
    if os.path.exists("tmp/gmwonly.cmb"):
        run_aby(spec_file, "gmwonly", version, ["-c", "gmwonly.cmb"])
    else:
        write_log(DELIMITER, version)
        write_log("LOG: Missing: gmwonly.cmb", version)


def run_gmwhyrbid(spec_file, version):
    if os.path.exists("tmp/gmwhybrid.cmb"):
        run_aby(spec_file, "gmwhybrid", version, ["-c", "gmwhybrid.cmb"])
    else:
        write_log(DELIMITER, version)
        write_log("LOG: Missing: gmwhybrid.cmb", version)


def run_optimized(spec_file, version):
    if os.path.exists("tmp/ps_optimized.cmb"):
        run_aby(spec_file, "ps_optimized", version, ["-c", "ps_optimized.cmb"])
    else:
        write_log(DELIMITER, version)
        write_log("LOG: Missing: ps_optimized.cmb", version)


def run_simulation(test_path, spec_file, version, args=[]):
    remove_tmp()
    make_tmp()
    try:
        # build benchmarks
        build_mpc_circuit(test_path, version, args)

        # run benchmarks
        run_sim(spec_file, version)
        run_aby_sim(spec_file, version)
    except Exception as e:
        if os.getcwd().endswith("tmp"):
            os.chdir(PARENT_DIR)
        write_log("LOG: Failed simulating circuit with args: {}, exception: {}".format(args, e), version)
    remove_tmp()


def run_all_hycc_benchmarks(test_path, spec_file, version, args=[]):
    remove_tmp()
    make_tmp()
    # build benchmarks
    try:
        # compilation to arithmetic circuits is not always possible
        build_mpc_circuit(test_path, version, args)
        bundle_modules(version)
    except Exception as e:
        if os.getcwd().endswith("tmp"):
            os.chdir(PARENT_DIR)
        write_log("LOG: Failed building circuit with args: {}, exception: {}".format(args, e), version)

    # run benchmarks
    try:
        run_yaoonly(spec_file, version)
    except Exception as e:
        if os.getcwd().endswith("tmp"):
            os.chdir(PARENT_DIR)
        write_log("LOG: Failed yaoonly with args: {}, exception: {}".format(args, e), version)

    try:
        run_yaohybrid(spec_file, version)
    except Exception as e:
        if os.getcwd().endswith("tmp"):
            os.chdir(PARENT_DIR)
        write_log("LOG: Failed yaohybrid with args: {}, exception: {}".format(args, e), version)

    try:
        run_gmwonly(spec_file, version)
    except Exception as e:
        if os.getcwd().endswith("tmp"):
            os.chdir(PARENT_DIR)
        write_log("LOG: Failed gmwonly with args: {}, exception: {}".format(args, e), version)

    try:
        run_gmwhyrbid(spec_file, version)
    except Exception as e:
        if os.getcwd().endswith("tmp"):
            os.chdir(PARENT_DIR)
        write_log("LOG: Failed gmwhybrid with args: {}, exception: {}".format(args, e), version)

    # ps optimized
    try:
        optimize_selection(version)
    except Exception as e:
        if os.getcwd().endswith("tmp"):
            os.chdir(PARENT_DIR)
        write_log("LOG: Failed optimize_selection with args: {}, exception: {}".format(args, e), version)

    try:
        run_optimized(spec_file, version)
    except Exception as e:
        if os.getcwd().endswith("tmp"):
            os.chdir(PARENT_DIR)
        write_log("LOG: Failed run_optimized with args: {}, exception: {}".format(args, e), version)
    remove_tmp()


def benchmark_hycc(name, path):
    version = "{}_{}_mt-{}_cm-{}".format(
        "hycc", name, MINIMIZATION_TIME, COST_MODEL)
    log_path = format("test_results/log_{}.txt".format(version))
    if os.path.exists(log_path):
        print("Benchmark already ran: {}".format(log_path))
        return

    write_log(DELIMITER, version)
    write_log("LOG: Benchmarking HyCC", version)
    write_log(DELIMITER, version)

    test_path = PARENT_DIR + HYCC_SOURCE + \
        "/examples/benchmarks/{}".format(path)
    spec_file = "tests/hycc/{}.spec".format(name)

    write_log("LOG: TEST PATH: {}".format(test_path), version)
    write_log("LOG: SPEC_FILE: {}".format(spec_file), version)
    write_log("LOG: MINIMIZATION TIME: {}".format(MINIMIZATION_TIME), version)
    write_log("LOG: COST MODEL: {}".format(COST_MODEL), version)

    # # benchmark cbmc-gc benchmarks
    # run_simulation(test_path, spec_file, version)
    # write_log(DELIMITER, version)

    # benchmark cbmc-gc benchmarks
    args = ["--all-variants"]
    write_log("LOG: Running with args: {}".format(args), version)
    run_all_hycc_benchmarks(test_path, spec_file, version, args)
    write_log(DELIMITER, version)

    args = ["--all-variants", "--outline"]
    write_log("LOG: Running with args: {}".format(args), version)
    run_all_hycc_benchmarks(test_path, spec_file, version, args)
    write_log(DELIMITER, version)


################################################################################
# Benchmark circ
################################################################################

def run_circ_benchmark(name):
    print("Running CirC {}".format(name))
    write_log("LOG: Running CirC {}".format(name))
    write_log("LOG: Test cases {}".format(TEST_NAME))
    write_log("LOG: Parameters: {}, {}, {}".format(
        NUM_PARTS, MUT_LEVEL, MUT_STEP_SIZE))
    for i in range(RERUN):
        write_log("RERUN: {}".format(i))
        os.chdir(CIRC_SOURCE)
        result = subprocess.run(["./scripts/build_mpc_c_benchmark.zsh", TEST_FILE, COST_MODEL, name, str(
            NUM_PARTS), str(MUT_LEVEL), str(MUT_STEP_SIZE)], check=True, capture_output=True, text=True)
        os.chdir(PARENT_DIR+PARENT_DIR)
        write_log(result.stdout)

        os.chdir(CIRC_SOURCE)
        result = subprocess.run(["python3", "./scripts/aby_tests/c_benchmark_aby.py",
                                "-t", TEST_NAME], check=True, capture_output=True, text=True)
        os.chdir(PARENT_DIR+PARENT_DIR)
        write_log(result.stdout)
    write_log("\n")


def benchmark_boolean_only():
    # benchmark boolean only
    run_circ_benchmark("b")


def benchmark_yao_only():
    # benchmark yao only
    run_circ_benchmark("y")


def benchmark_arithmetic_and_boolean():
    # benchmark a+b
    run_circ_benchmark("a+b")


def benchmark_arithmetic_and_yao():
    # benchmark a+y
    run_circ_benchmark("a+y")


def benchmark_greedy():
    # benchmark greedy
    run_circ_benchmark("greedy")


def benchmark_lp():
    # benchmark LP
    run_circ_benchmark("lp")


def benchmark_lp_nm():
    # benchmark LP
    run_circ_benchmark("lp+nm")


def benchmark_glp():
    # benchmark global LP
    run_circ_benchmark("glp")


def benchmark_circ_biomatch():
    write_log(DELIMITER)
    write_log("LOG: Benchmarking CirC")
    write_log(DELIMITER)

    # build benchmarks
    os.environ['ABY_SOURCE'] = "../ABY"
    os.chdir(CIRC_SOURCE)
    subprocess.run(["python3", "driver.py", "-F",
                   "aby", "c", "lp"], check=True)
    subprocess.run(["python3", "driver.py", "--benchmark"], check=True)
    os.chdir(PARENT_DIR+PARENT_DIR)

    # run benchmarks
    benchmark_boolean_only()
    benchmark_yao_only()
    benchmark_arithmetic_and_boolean()
    benchmark_arithmetic_and_yao()
    benchmark_greedy()
    benchmark_lp()
    benchmark_lp_nm()
    benchmark_glp()

    write_log(DELIMITER)
