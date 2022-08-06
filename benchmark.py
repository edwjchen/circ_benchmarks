from util import *

################################################################################
# Benchmark hycc
################################################################################


# def run_sim(spec_file, version):
#     write_log(DELIMITER, version)
#     cmd = [CIRCUIT_SIM, MPC_CIRC, "--spec-file", spec_file]
#     for i in range(RERUN):
#         run_cmd(cmd, "RERUN {}: CIRCUIT-SIM".format(i), version)


def run_aby(spec_file, params):
    write_log(DELIMITER, params)
    cmd = [ABY_CBMC_GC, "--spec-file", spec_file, "-c", params["ss_file"]]
    server_cmd = cmd + ["-r", "0"]
    client_cmd = cmd + ["-r", "1"]
    for i in range(RERUN):
        run_cmds(server_cmd, client_cmd, "RERUN: {}".format(i), params)


# def run_aby_sim(spec_file, version):
#     run_aby(spec_file, "ABY-SIM", version, [MPC_CIRC])


# def run_simulation(test_path, spec_file, version, args=[]):
#     circuit_dir = "{}{}".format(HYCC_CIRCUIT_PATH, version)
#     make_dir(circuit_dir)

#     try:
#         os.chdir(circuit_dir)
#         # build benchmarks
#         build_mpc_circuit(test_path, version, args)

#         # run benchmarks
#         run_sim(spec_file, version)
#         run_aby_sim(spec_file, version)
#     except Exception as e:
#         write_log("LOG: Failed simulating circuit with args: {}, exception: {}".format(
#             args, e), version)
  

def run_hycc_benchmark(spec_file, params):
    print("running: ", params["version"])
    args = params["a"]
    ss = params["ss"]
    if not args:
        return

    ss_file = "{}.cmb".format(ss)
    params["ss_file"] = ss_file

    try:
        if os.path.exists(ss_file):
            run_aby(spec_file, params)
        else:
            write_log("LOG: Missing: {}".format(ss_file), params)
    except Exception as e:
        write_log("LOG: Failed {} with args: {}, exception: {}".format(
            ss, " ".join(args), e), params)


def compile_hycc_benchmark(test_path, params):
    print("compile: ", params["version"])
    args = params["a"]
    try:
        # compile
        cmd = [CBMC_GC, test_path,
            "--minimization-time-limit", str(params["mt"])] + args
        print(" ".join(cmd))
        run_cmd(cmd, "MODE: compile", params)

        #bundle modules
        write_log(DELIMITER, params)
        cmd = ["python3", MODULE_BUNDLE, "."]
        print(" ".join(cmd))
        run_cmd(cmd, "MODE: bundle", params)

        write_log(DELIMITER, params)
        cmd = ["python3", SELECTION, ".", COSTS] # TODO: update cost model
        print(" ".join(cmd))
        run_cmd(cmd, "MODE: selection", params)
        return True
    except Exception as e:
        write_log("LOG: Failed compiling circuit with args: {}, exception: {}".format(
            " ".join(args), e), params)
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
                params["cm"] = cm
                version = "{}_{}_mt-{}_args-{}_cm-{}".format("hycc", name, mt, "".join(a), cm)
                if version not in versions:
                    versions.append((version, params))
                

    # make circuit directories    
    for (version, params) in versions:
        params["system"] = "hycc"
        params["name"] = name

        circuit_dir = "{}{}".format(HYCC_CIRCUIT_PATH, version)
        make_dir(circuit_dir)

        compile_version = "compile_{}".format(version)
        compile_log_path = format(
            "{}test_results/{}_{}/log_{}.txt".format(CIRC_BENCHMARK_SOURCE, params["system"], name, compile_version))
        
        if not os.path.exists(compile_log_path):
            # compile HyCC benchmark
            os.chdir(circuit_dir)
            params["version"] = compile_version

            write_log(DELIMITER, params)
            write_log("LOG: Benchmarking HyCC", params)
            write_log(DELIMITER, params)

            write_log("LOG: TEST: {}".format(name), params)
            write_log("LOG: MINIMIZATION_TIME: {}".format(params["mt"]), params)
            write_log("LOG: COST_MODEL: {}".format(params["cm"]), params)
            write_log("LOG: ARGUMENTS: {}".format(params["a"]), params)
            compile_hycc_benchmark(test_path, params)

        for ss in HYCC_SELECTION_SCHEMES:
            params["ss"] = ss
            run_version = "{}_ss-{}".format(version, ss)
            params["version"] = run_version
            log_path = format("{}test_results/{}_{}/log_{}.txt".format(CIRC_BENCHMARK_SOURCE, params["system"], name, run_version))
            if not os.path.exists(log_path):
                # run HyCC benchmark
                os.chdir(circuit_dir)
                write_log(DELIMITER, params)
                write_log("LOG: Benchmarking HyCC", params)
                write_log(DELIMITER, params)

                write_log("LOG: TEST: {}".format(name), params)
                write_log("LOG: SELECTION_SCHEME: {}".format(ss), params)
                write_log("LOG: MINIMIZATION_TIME: {}".format(params["mt"]), params)
                write_log("LOG: COST_MODEL: {}".format(params["cm"]), params)
                write_log("LOG: ARGUMENTS: {}".format(params["a"]), params)

                run_hycc_benchmark(spec_file, params)
            else:
                print("Benchmark already ran: {}".format(log_path))

    os.chdir(CIRC_BENCHMARK_SOURCE)


################################################################################
# Benchmark circ
################################################################################

def run_circ_benchmark(params):
    print("running: ", params["version"])
    name = params["name"]
    address = params.get("address", "127.0.0.1")

    write_log(DELIMITER, params)
    cmd = [ABY_INTERPRETER,
           "-m", "mpc",
           "-f", get_circ_test_path(name),
           "-t", get_circ_input_path(name),
           "--address", address]
    server_cmd = cmd + ["-r", "0"]
    client_cmd = cmd + ["-r", "1"]
    for i in range(RERUN):
        try:
            run_cmds(server_cmd, client_cmd, "RERUN: {}".format(i), params)
        except Exception as e:
            write_log("LOG: Failed to run, exception: {}".format(e), params)


def compile_circ_benchmarks(params):
    print("compile: ", params["version"])
    ss = params["ss"]
    cm = params["cm"]
    name = params["name"]

    write_log(DELIMITER, params)
    cmd = [CIRC_TARGET,
           "--parties", "2",
           get_circ_build_path(name), "mpc",
           "--cost-model", cm,
           "--selection-scheme", ss]
    for i in range(RERUN):
        try:
            run_cmd(cmd, "RERUN: {}".format(i), params)
        except Exception as e: 
            write_log("LOG: Failed to build, exception: {}".format(e), params)


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
                        params = {}
                        params["ss"] = ss
                        params["np"] = np
                        params["ml"] = ml
                        params["mss"] = mss
                        params["cm"] = cm
                        versions.append((version, params))

    for (version, params) in versions:
        params["system"] = "circ"
        params["name"] = name
        params["version"] = version

        log_path = format(
            "{}test_results/circ_{}/log_{}.txt".format(CIRC_BENCHMARK_SOURCE, name, version))
        if os.path.exists(log_path):
            print("Benchmark already ran: {}".format(log_path))
            continue

        # write header
        write_log(DELIMITER, params)
        write_log("LOG: Benchmarking CirC", params)
        write_log(DELIMITER, params)
        write_log("LOG: TEST: {}".format(name), params)
        write_log("LOG: SELECTION_SCHEME: {}".format(params["ss"]), params)
        write_log("LOG: NUM_PARTS: {}".format(params["np"]), params)
        write_log("LOG: MUTATION_LEVEL: {}".format(params["ml"]), params)
        write_log("LOG: MUTATION_STEP_SIZE: {}".format(params["mss"]), params)
        write_log("LOG: COST_MODEL: {}".format(params["cm"]), params)

        # compile benchmark
        compile_circ_benchmarks(params)

        # run benchmarks
        run_circ_benchmark(params)
