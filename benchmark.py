from util import *

################################################################################
# Benchmark hycc
################################################################################


def optimize_selection(version, costs_path=COSTS):
    write_log(DELIMITER, version)
    cmd = ["python3", SELECTION, ".", costs_path]
    run_cmd(cmd, "Selection time", version)


def run_sim(spec_file, version):
    write_log(DELIMITER, version)
    cmd = [CIRCUIT_SIM, MPC_CIRC, "--spec-file", spec_file]
    for i in range(RERUN):
        run_cmd(cmd, "RERUN {}: CIRCUIT-SIM".format(i), version)


def run_aby(spec_file, name, version, args=[]):
    write_log(DELIMITER, version)
    cmd = [ABY_CBMC_GC, "--spec-file", spec_file] + args
    server_cmd = cmd + ["-r", "0"]
    client_cmd = cmd + ["-r", "1"]
    for i in range(RERUN):
        run_cmds(server_cmd, client_cmd,
                 "RERUN {}: {}".format(i, name), version)


def run_aby_sim(spec_file, version):
    run_aby(spec_file, "ABY-SIM", version, [MPC_CIRC])


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
        write_log("LOG: Failed simulating circuit with args: {}, exception: {}".format(
            args, e), version)
  

def run_hycc_benchmark(version, params, spec_file):
        args = params["a"]
        if not args:
            return

        ss = params["ss"]
        ss_file = "{}.cmb".format(ss)
        if ss == "ps_optimized":
            try: 
                optimize_selection(version)
            except Exception as e:
                write_log("LOG: Failed optimize_selection with args: {}, exception: {}".format(
                    " ".join(args), e), version)
        try:
            if os.path.exists(ss_file):
                run_aby(spec_file, ss, version, ["-c", ss_file])
            else:
                write_log("LOG: Missing: {}".format(ss_file), version)
        except Exception as e:
            args = params["a"]
            write_log("LOG: Failed {} with args: {}, exception: {}".format(
                ss, " ".join(args), e), version)


def compile_hycc_benchmark(version, test_path, params):
    args = params["a"]
    try:
        # compile
        cmd = [CBMC_GC, test_path,
            "--minimization-time-limit", str(params["mt"])] + args
        run_cmd(cmd, "Build circuit time", version)

        #bundle modules
        write_log(DELIMITER, version)
        cmd = ["python3", MODULE_BUNDLE, "."]
        run_cmd(cmd, "Module bundle time", version)
        return True
    except Exception as e:
        write_log("LOG: Failed simulating circuit with args: {}, exception: {}".format(
            " ".join(args), e), version)
        return False
    

def benchmark_hycc(name, path):
    test_path = HYCC_SOURCE + \
                    "/examples/benchmarks/{}".format(path)
    spec_file = "{}specs/{}.spec".format(CIRC_BENCHMARK_SOURCE, name)

    versions = []
    for cm in COST_MODELS:
        for mt in MINIMIZATION_TIMES:
            for a in HYCC_COMPILE_ARGUMENTS: 
                params = {}
                params["mt"] = mt
                params["a"] = a

                version = "{}_{}_mt-{}_args-{}".format("hycc", name, mt, "".join(a))
                if version not in versions:
                    versions.append((version, params))
                

    # make circuit directories    
    for (version, params) in versions:
        circuit_dir = "{}{}".format(HYCC_CIRCUIT_PATH, version)
        make_dir(circuit_dir)

        compile_version = "compile_{}".format(version)
        compile_log_path = format(
            "{}test_results/log_{}.txt".format(CIRC_BENCHMARK_SOURCE, compile_version))
        
        if not os.path.exists(compile_log_path):
            # compile HyCC benchmark
            os.chdir(circuit_dir)
            compile_hycc_benchmark(compile_version, test_path, params)

        for ss in HYCC_SELECTION_SCHEMES:
            for cm in COST_MODELS:
                params["ss"] = ss
                params["cm"] = cm
                run_version = "{}_ss-{}_cm-{}".format(version, ss, cm)
                log_path = format("test_results/log_{}.txt".format(run_version))
                if not os.path.exists(log_path):
                    # run HyCC benchmark
                    os.chdir(circuit_dir)
                    write_log(DELIMITER, run_version)
                    write_log("LOG: Benchmarking HyCC", run_version)
                    write_log(DELIMITER, run_version)

                    write_log("LOG: TEST PATH: {}".format(test_path), run_version)
                    write_log("LOG: SPEC_FILE: {}".format(spec_file), run_version)
                    write_log("LOG: MINIMIZATION TIME: {}".format(params["mt"]), run_version)
                    write_log("LOG: COST MODEL: {}".format(params["cm"]), run_version)
                    write_log("LOG: ARGUMENTS: {}".format(params["a"]), run_version)

                    run_hycc_benchmark(run_version, params, spec_file)
                else:
                    print("Benchmark already ran: {}".format(log_path))

    os.chdir(CIRC_BENCHMARK_SOURCE)


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
        try:
            run_cmd(cmd, "RERUN {}: {}".format(i, name), version)
        except Exception as e:
            write_log("LOG: Failed to build, exception: {}".format(e), version)


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
        try:
            run_cmds(server_cmd, client_cmd,
                     "RERUN {}: {} ".format(i, name), version)
        except Exception as e:
            write_log("LOG: Failed to run, exception: {}".format(e), version)


def benchmark_circ(name):
    os.chdir(CIRC_SOURCE)

    versions = []
    for ss in CIRC_SELECTION_SCHEMES:
        for np in NUM_PARTS:
            for ml in MUT_LEVELS:
                for mss in MUT_STEP_SIZES:
                    for cm in COST_MODELS:
                        version = "{}_test-{}_ss-{}_np-{}_ml-{}_mss-{}_cm-{}".format(
                            "circ", name, ss, np, ml, mss, cm)
                        params = [ss, np, ml, mss, cm]
                        versions.append((version, params))

    for (version, params) in versions:
        log_path = format(
            "{}test_results/log_{}.txt".format(CIRC_BENCHMARK_SOURCE, version))
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
