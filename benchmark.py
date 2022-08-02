from util import *

################################################################################
# Benchmark hycc
################################################################################


def build_mpc_circuit(test_path, version, args=[]):
    write_log(DELIMITER, version)
    cmd = [CBMC_GC, test_path,
           "--minimization-time-limit", str(MINIMIZATION_TIME)] + args
    run_cmd(cmd, "Build circuit time", version)

def bundle_modules(version):
    write_log(DELIMITER, version)
    cmd = ["python3", MODULE_BUNDLE, "."]
    run_cmd(cmd, "Module bundle time", version)


def optimize_selection(version, costs_path=COSTS):
    write_log(DELIMITER, version)
    cmd = ["python3",SELECTION, ".", costs_path]
    run_cmd(cmd, "Selection time", version)


def run_sim(spec_file, version):
    write_log(DELIMITER, version)
    cmd = [CIRCUIT_SIM, MPC_CIRC, "--spec-file", spec_file]
    for i in range(RERUN):
        run_cmd(cmd, "CIRCUIT-SIM RERUN {}:".format(i), version)


def run_aby(spec_file, name, version, args=[]):
    write_log(DELIMITER, version)
    cmd = [ABY_CBMC_GC, "--spec-file", spec_file] + args
    server_cmd = cmd + ["-r", "0"]
    client_cmd = cmd + ["-r", "1"]
    for i in range(RERUN):
        run_cmds(server_cmd, client_cmd, "{} RERUN {}:".format(name, i), version)


def run_aby_sim(spec_file, version):
    run_aby(spec_file, "ABY-SIM", version, [MPC_CIRC])

def run_yaoonly(spec_file, version):
    if os.path.exists("yaoonly.cmb"):
        run_aby(spec_file, "yaoonly", version, ["-c", "yaoonly.cmb"])
    else:
        write_log(DELIMITER, version)
        write_log("LOG: Missing: yaoonly.cmb", version)


def run_yaohybrid(spec_file, version):
    if os.path.exists("yaohybrid.cmb"):
        run_aby(spec_file, "yaohybrid", version, ["-c", "yaohybrid.cmb"])
    else:
        write_log(DELIMITER, version)
        write_log("LOG: Missing: yaohybrid.cmb", version)


def run_gmwonly(spec_file, version):
    if os.path.exists("gmwonly.cmb"):
        run_aby(spec_file, "gmwonly", version, ["-c", "gmwonly.cmb"])
    else:
        write_log(DELIMITER, version)
        write_log("LOG: Missing: gmwonly.cmb", version)


def run_gmwhyrbid(spec_file, version):
    if os.path.exists("gmwhybrid.cmb"):
        run_aby(spec_file, "gmwhybrid", version, ["-c", "gmwhybrid.cmb"])
    else:
        write_log(DELIMITER, version)
        write_log("LOG: Missing: gmwhybrid.cmb", version)


def run_optimized(spec_file, version):
    if os.path.exists("ps_optimized.cmb"):
        run_aby(spec_file, "ps_optimized", version, ["-c", "ps_optimized.cmb"])
    else:
        write_log(DELIMITER, version)
        write_log("LOG: Missing: ps_optimized.cmb", version)


def run_simulation(test_path, spec_file, version, args=[]):
    circuit_dir = "{}{}".format(HYCC_CIRCUIT_PATH, version)
    make_dir(circuit_dir)

    try:
        os.chdir(circuit_dir)
        # build benchmarks
        build_mpc_circuit(test_path, version, args)

        # run benchmarks
        run_sim(spec_file, version)
        run_aby_sim(spec_file, version)
    except Exception as e:
        write_log("LOG: Failed simulating circuit with args: {}, exception: {}".format(args, e), version)


def run_all_hycc_benchmarks(test_path, spec_file, version, args=[]):
    circuit_dir = "{}{}".format(HYCC_CIRCUIT_PATH, version)
    make_dir(circuit_dir)

    # build benchmarks
    try:
        # compilation to arithmetic circuits is not always possible
        os.chdir(circuit_dir)
        build_mpc_circuit(test_path, version, args)
        bundle_modules(version)
    except Exception as e:
        write_log("LOG: Failed building circuit with args: {}, exception: {}".format(args, e), version)

    # run benchmarks
    try:
        os.chdir(circuit_dir)
        run_yaoonly(spec_file, version)
    except Exception as e:
        write_log("LOG: Failed yaoonly with args: {}, exception: {}".format(args, e), version)

    try:
        os.chdir(circuit_dir)
        run_yaohybrid(spec_file, version)
    except Exception as e:
        write_log("LOG: Failed yaohybrid with args: {}, exception: {}".format(args, e), version)

    try:
        os.chdir(circuit_dir)
        run_gmwonly(spec_file, version)
    except Exception as e:
        write_log("LOG: Failed gmwonly with args: {}, exception: {}".format(args, e), version)

    try:
        os.chdir(circuit_dir)
        run_gmwhyrbid(spec_file, version)
    except Exception as e:
        write_log("LOG: Failed gmwhybrid with args: {}, exception: {}".format(args, e), version)

    # ps optimized
    try:
        os.chdir(circuit_dir)
        optimize_selection(version)
    except Exception as e:
        write_log("LOG: Failed optimize_selection with args: {}, exception: {}".format(args, e), version)

    try:
        os.chdir(circuit_dir)
        run_optimized(spec_file, version)
    except Exception as e:
        write_log("LOG: Failed run_optimized with args: {}, exception: {}".format(args, e), version)

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

    test_path = HYCC_SOURCE + \
        "/examples/benchmarks/{}".format(path)
    spec_file = "{}specs/{}.spec".format(CIRC_BENCHMARK_SOURCE, name)

    write_log("LOG: TEST PATH: {}".format(test_path), version)
    write_log("LOG: SPEC_FILE: {}".format(spec_file), version)
    write_log("LOG: MINIMIZATION TIME: {}".format(MINIMIZATION_TIME), version)
    write_log("LOG: COST MODEL: {}".format(COST_MODEL), version)

    # # benchmark simulation
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

def compile_circ_benchmarks(name, version, ss, np, ml, mss, cm):
    write_log(DELIMITER, version)
    cmd = [CIRC_TARGET, 
        "--parties", "2", 
        get_circ_build_path(name), "mpc", 
        "--cost-model", cm, 
        "--selection-scheme", ss]
    for i in range(RERUN):
        run_cmd(cmd, "RERUN {}:".format(i), version)

def run_circ_benchmark(name, version, address="127.0.0.1"):
    write_log(DELIMITER, version)
    cmd = [ABY_INTERPRETER, 
        "-m", "mpc", 
        "-f", get_circ_test_path(name), 
        "-t", get_circ_input_path(name), 
        "--address", address]
    server_cmd = cmd + ["-r", "0"]
    client_cmd = cmd + ["-r", "1"]
    for i in range(RERUN):
        run_cmds(server_cmd, client_cmd, "{} RERUN {}:".format(name, i), version)

def benchmark_circ(name):
    os.chdir(CIRC_SOURCE)
    
    versions = []
    for ss in SELECTION_SCHEMES:
        for np in NUM_PARTS:
            for ml in MUT_LEVELS:
                for mss in MUT_STEP_SIZES:
                    for cm in COST_MODELS:
                        version = "{}_ss-{}_np-{}_ml-{}_mss-{}_cm-{}".format("circ", ss, np, ml, mss, cm)
                        params = [ss, np, ml, mss, cm]
                        versions.append((version, params))

    for (version, params) in versions:
        log_path = format("{}test_results/log_{}.txt".format(CIRC_BENCHMARK_SOURCE, version))
        if os.path.exists(log_path):
            print("Benchmark already ran: {}".format(log_path))
            continue

        ss = params[0]
        np = params[1]
        ml = params[2]
        mss = params[3]
        cm = params[4]

        # write header 
        write_log(DELIMITER, version)
        write_log("LOG: Benchmarking CirC", version)
        write_log(DELIMITER, version)
        write_log("LOG: Test: {}".format(name), version)
        write_log("LOG: SELECTION_SCHEME: {}".format(ss), version)
        write_log("LOG: NUM_PARTS: {}".format(np), version)
        write_log("LOG: MUTATION_LEVEL: {}".format(ml), version)
        write_log("LOG: MUTATION_STEP_SIZE: {}".format(mss), version)
        write_log("LOG: COST_MODEL: {}".format(cm), version)

        # compile benchmark 
        compile_circ_benchmarks(name, version, ss, np, ml, mss, cm)

        # run benchmarks
        run_circ_benchmark(name, version)
