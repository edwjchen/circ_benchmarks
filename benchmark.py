from util import *

################################################################################
# Benchmark hycc
################################################################################


def run_aby(spec_file, params, instance_metadata):
    write_log(DELIMITER, params)
    address = instance_metadata.get("address", "127.0.0.1")
    role = instance_metadata["role"]
    assert(role == "0" or role == "1")
    cmd = [ABY_CBMC_GC, "--spec-file", spec_file, "-c", params["ss_file"]]
    cmd = cmd + ["-a", address] + ["-r", role]
    for i in range(RERUN):
        run_cmd(cmd, "RERUN: {}".format(i), params)


def run_aby_local(spec_file, params):
    write_log(DELIMITER, params)
    cmd = [ABY_CBMC_GC, "--spec-file", spec_file, "-c", params["ss_file"]]
    server_cmd = cmd + ["-r", "0"]
    client_cmd = cmd + ["-r", "1"]
    for i in range(RERUN):
        run_cmds(server_cmd, client_cmd, "RERUN: {}".format(i), params)


def run_hycc_benchmark(spec_file, params, instance_metadata):
    print("running: ", params["version"], instance_metadata["setting"])
    args = params["a"]
    ss = params["ss"]
    if not args:
        return

    ss_file = "{}.cmb".format(ss)
    params["ss_file"] = ss_file

    try:
        if os.path.exists(ss_file):
            if "role" in instance_metadata:
                run_aby(spec_file, params, instance_metadata)
            else:
                run_aby_local(spec_file, params)
        else:
            write_log("LOG: Missing: {}".format(ss_file), params)
    except Exception as e:
        write_log("LOG: Failed {} with args: {}, exception: {}".format(
            ss, " ".join(args), e), params)
        log_path = "{}run_test_results_{}/{}_{}/log_{}.txt".format(
                CIRC_BENCHMARK_SOURCE, instance_metadata["setting"], params["system"], params["name"], params["version"])
        failed_path = "{}run_test_results_{}/{}_{}/failed_log_{}.txt".format(
                CIRC_BENCHMARK_SOURCE, instance_metadata["setting"], params["system"], params["name"], params["version"])
        subprocess.call("mv {} {}".format(log_path, failed_path), shell=True)


def compile_hycc_benchmark(test_path, params):
    print("compile: ", params["version"])
    args = params["a"]
    try:
        # compile
        cmd = [CBMC_GC, test_path] + args
        if params["mt"] == 0:
            cmd += ["--no-minimization"]
        else:
            cmd += ["--minimization-time-limit", str(params["mt"])]
        run_cmd(cmd, "MODE: compile", params)

        # bundle modules
        write_log(DELIMITER, params)
        cmd = ["python3", MODULE_BUNDLE, "."]
        run_cmd(cmd, "MODE: bundle", params)
        return True
    except Exception as e:
        write_log("LOG: Failed compiling circuit with args: {}, exception: {}".format(
            " ".join(args), e), params)
        
        log_path = "{}test_results/{}_{}/log_{}.txt".format(
                CIRC_BENCHMARK_SOURCE, params["system"], params["name"], params["version"])
        failed_path = "{}test_results/{}_{}/failed_log_{}.txt".format(
                CIRC_BENCHMARK_SOURCE, params["system"], params["name"], params["version"])
        subprocess.call("mv {} {}".format(log_path, failed_path), shell=True)
        return False

def select_hycc_benchmark(params):
    print("select: ", params["version"])
    args = params["a"]
    try:
        write_log(DELIMITER, params)
        cmd = ["python3", SELECTION, ".", COSTS]  # TODO: update cost model
        run_cmd(cmd, "MODE: selection", params)
        return True
    except Exception as e:
        write_log("LOG: Failed selecting circuit with args: {}, exception: {}".format(
            " ".join(args), e), params)
        
        log_path = "{}test_results/{}_{}/log_{}.txt".format(
                CIRC_BENCHMARK_SOURCE, params["system"], params["name"], params["version"])
        failed_path = "{}test_results/{}_{}/failed_log_{}.txt".format(
                CIRC_BENCHMARK_SOURCE, params["system"], params["name"], params["version"])
        subprocess.call("mv {} {}".format(log_path, failed_path), shell=True)
        return False


def compile_hycc(name, path):
    test_path = HYCC_SOURCE + \
        "/examples/benchmarks/{}".format(path)

    versions = []
    for cm in COST_MODELS:
        for mt in MINIMIZATION_TIMES:
            for a in HYCC_COMPILE_ARGUMENTS:
                params = {}
                params["mt"] = mt
                params["a"] = a
                params["cm"] = cm
                version = "{}_{}_mt-{}_args-{}_cm-{}".format(
                    "hycc", name, mt, "".join(a), cm)
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
        failed_log_path = format(
            "{}test_results/{}_{}/failed_log_{}.txt".format(CIRC_BENCHMARK_SOURCE, params["system"], name, compile_version))

        if not os.path.exists(compile_log_path) and not os.path.exists(failed_log_path):
            # compile HyCC benchmark
            os.chdir(circuit_dir)
            params["version"] = compile_version

            write_log(DELIMITER, params)
            write_log("LOG: Benchmarking HyCC", params)
            write_log(DELIMITER, params)

            write_log("LOG: TEST: {}".format(name), params)
            write_log("LOG: MINIMIZATION_TIME: {}".format(
                params["mt"]), params)
            write_log("LOG: COST_MODEL: {}".format(params["cm"]), params)
            write_log("LOG: ARGUMENTS: {}".format(params["a"]), params)
            compile_hycc_benchmark(test_path, params)
    os.chdir(CIRC_BENCHMARK_SOURCE)



def select_hycc(name):
    versions = []
    for cm in COST_MODELS:
        for mt in MINIMIZATION_TIMES:
            for a in HYCC_COMPILE_ARGUMENTS:
                params = {}
                params["mt"] = mt
                params["a"] = a
                params["cm"] = cm
                version = "{}_{}_mt-{}_args-{}_cm-{}".format(
                    "hycc", name, mt, "".join(a), cm)
                if version not in versions:
                    versions.append((version, params))
    
    # make circuit directories
    for (version, params) in versions:
        params["system"] = "hycc"
        params["name"] = name

        circuit_dir = "{}{}".format(HYCC_CIRCUIT_PATH, version)
        make_dir(circuit_dir)

        select_version = "select_{}".format(version)
        select_log_path = format(
            "{}test_results/{}_{}/log_{}.txt".format(CIRC_BENCHMARK_SOURCE, params["system"], name, select_version))
        failed_log_path = format(
            "{}test_results/{}_{}/failed_log_{}.txt".format(CIRC_BENCHMARK_SOURCE, params["system"], name, select_version))

        if not os.path.exists(select_log_path) and not os.path.exists(failed_log_path):
            # select HyCC benchmark
            os.chdir(circuit_dir)
            params["version"] = select_version

            write_log(DELIMITER, params)
            write_log("LOG: Benchmarking HyCC", params)
            write_log(DELIMITER, params)

            write_log("LOG: TEST: {}".format(name), params)
            write_log("LOG: MINIMIZATION_TIME: {}".format(
                params["mt"]), params)
            write_log("LOG: COST_MODEL: {}".format(params["cm"]), params)
            write_log("LOG: ARGUMENTS: {}".format(params["a"]), params)
            select_hycc_benchmark(params)
    os.chdir(CIRC_BENCHMARK_SOURCE)

def benchmark_hycc(name, path, instance_metadata):
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

        for ss in HYCC_SELECTION_SCHEMES:
            params["ss"] = ss
            run_version = "{}_ss-{}_{}".format(version, ss, instance_metadata["setting"])
            params["version"] = run_version
            log_path = format("{}run_test_results_{}/{}_{}/log_{}.txt".format(
                CIRC_BENCHMARK_SOURCE, instance_metadata["setting"], params["system"], name, run_version))
            if not os.path.exists(log_path):
                # run HyCC benchmark
                os.chdir(circuit_dir)
                write_log(DELIMITER, params)
                write_log("LOG: Benchmarking HyCC", params)
                write_log(DELIMITER, params)

                write_log("LOG: TEST: {}".format(name), params)
                write_log("LOG: SELECTION_SCHEME: {}".format(ss), params)
                write_log("LOG: MINIMIZATION_TIME: {}".format(
                    params["mt"]), params)
                write_log("LOG: COST_MODEL: {}".format(params["cm"]), params)
                write_log("LOG: ARGUMENTS: {}".format(params["a"]), params)

                run_hycc_benchmark(spec_file, params, instance_metadata)
            else:
                print("Benchmark already ran: {}".format(log_path))

    os.chdir(CIRC_BENCHMARK_SOURCE)


################################################################################
# Benchmark circ
################################################################################

def run_circ_benchmark(params, instance_metadata):
    print("running: ", params["version"])
    name = params["name"]
    bytecode_path = params["bytecode_path"]
    address = instance_metadata.get("address", "127.0.0.1")

    if "role" in instance_metadata:
        role = instance_metadata["role"]
        assert(role == "0" or role == "1")
        write_log(DELIMITER, params)
        cmd = [ABY_INTERPRETER,
               "-m", "mpc",
               "-f", get_circ_test_path(name, bytecode_path),
               "-t", get_circ_input_path(name),
               "--address", address,
               "--role", role]
        for i in range(RERUN):
            try:
                run_cmd(cmd, "RERUN: {}".format(i), params)
            except Exception as e:
                print("Failed to run")
                write_log("LOG: Failed to run, exception: {}".format(e), params)
                log_path = "{}test_results/{}_{}/log_{}.txt".format(
                        CIRC_BENCHMARK_SOURCE, params["system"], params["name"], params["version"])
                failed_path = "{}test_results/{}_{}/failed_log_{}.txt".format(
                        CIRC_BENCHMARK_SOURCE, params["system"], params["name"], params["version"])
                subprocess.call("mv {} {}".format(log_path, failed_path), shell=True)
    else:
        print("Running test locally")
        write_log(DELIMITER, params)
        cmd = [ABY_INTERPRETER,
               "-m", "mpc",
               "-f", get_circ_test_path(name, bytecode_path),
               "-t", get_circ_input_path(name),
               "--address", address]
        server_cmd = cmd + ["-r", "0"]
        client_cmd = cmd + ["-r", "1"]
        for i in range(RERUN):
            try:
                run_cmds(server_cmd, client_cmd, "RERUN: {}".format(i), params)
            except Exception as e:
                print("Failed to run locally")
                write_log("LOG: Failed to run, exception: {}".format(e), params)

                log_path = "{}test_results/{}_{}/log_{}.txt".format(
                        CIRC_BENCHMARK_SOURCE, params["system"], params["name"], params["version"])
                failed_path = "{}test_results/{}_{}/failed_log_{}.txt".format(
                        CIRC_BENCHMARK_SOURCE, params["system"], params["name"], params["version"])
                subprocess.call("mv {} {}".format(log_path, failed_path), shell=True)


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

    # partition scheme
    if "ps" in params:
        cmd += ["--part-size", str(params["ps"])]
    if "ml" in params:
        cmd += ["--mut-level", str(params["ml"])]
    if "mss" in params:
        cmd += ["--mut-step-size", str(params["mss"])]
    if "gt" in params:
        cmd += ["--graph-type", str(params["gt"])]

    try:
        run_cmd(cmd, "MODE: compile", params)

        # copy file to test directory
        compile_path = CIRC_CIRCUIT_PATH+params["bytecode_path"]
        make_dir(compile_path)

        bytecode_path = get_circ_bytecode_path(name)
        subprocess.call("mv {} {}".format(bytecode_path,
                        compile_path), shell=True)

    except Exception as e:
        print("Failed to compile")
        write_log("LOG: Failed to build, exception: {}".format(e), params)
        log_path = "{}test_results/{}_{}/log_{}.txt".format(
                CIRC_BENCHMARK_SOURCE, params["system"], params["name"], params["version"])
        failed_path = "{}test_results/{}_{}/failed_log_{}.txt".format(
                CIRC_BENCHMARK_SOURCE, params["system"], params["name"], params["version"])
        subprocess.call("mv {} {}".format(log_path, failed_path), shell=True)


def compile_circ(name):
    os.chdir(CIRC_SOURCE)

    versions = []
    for ss in CIRC_NO_PARTITION_SELECTION_SCHEMES:
        for cm in COST_MODELS:
            version = "compile_{}_test-{}_ss-{}_cm-{}".format(
                "circ", name, ss, cm)
            bytecode_path = "{}_test-{}_ss-{}_cm-{}".format(
                "circ", name, ss, cm)
            params = {}
            params["ss"] = ss
            params["cm"] = cm
            params["bytecode_path"] = bytecode_path
            versions.append((version, params))
    for ss in CIRC_PARTITION_SELECTION_SCHEMES:
        for ps in PARTITION_SIZES:
            for ml in MUT_LEVELS:
                for mss in MUT_STEP_SIZES:
                    for gt in PARTITIONERS:
                        for cm in COST_MODELS:
                            version = "compile_{}_test-{}_ss-{}_ps-{}_ml-{}_mss-{}_gt-{}_cm-{}".format(
                                "circ", name, ss, ps, ml, mss, gt, cm)
                            bytecode_path = "{}_test-{}_ss-{}_ps-{}_ml-{}_mss-{}_gt-{}_cm-{}".format(
                                "circ", name, ss, ps, ml, mss, gt, cm)
                            params = {}
                            params["ss"] = ss
                            params["ps"] = ps
                            params["ml"] = ml
                            params["mss"] = mss
                            params["gt"] = gt
                            params["cm"] = cm
                            params["bytecode_path"] = bytecode_path
                            versions.append((version, params))

    for (version, params) in versions:
        params["system"] = "circ"
        params["name"] = name
        params["version"] = version

        log_path = format(
            "{}test_results/circ_{}/log_{}.txt".format(CIRC_BENCHMARK_SOURCE, name, version))
        failed_path = format(
            "{}test_results/circ_{}/failed_log_{}.txt".format(CIRC_BENCHMARK_SOURCE, name, version))
        if os.path.exists(log_path) or os.path.exists(failed_path):
            print("Benchmark already ran: {}".format(log_path))
            continue

        # write header
        write_log(DELIMITER, params)
        write_log("LOG: Benchmarking CirC", params)
        write_log(DELIMITER, params)
        write_log("LOG: TEST: {}".format(name), params)
        write_log("LOG: SELECTION_SCHEME: {}".format(params["ss"]), params)
        write_log("LOG: COST_MODEL: {}".format(params["cm"]), params)
        if "ps" in params:
            write_log("LOG: PARTITION_SIZE: {}".format(params["ps"]), params)
        if "ml" in params:
            write_log("LOG: MUTATION_LEVEL: {}".format(params["ml"]), params)
        if "mss" in params:
            write_log("LOG: MUTATION_STEP_SIZE: {}".format(
                params["mss"]), params)
        if "gt" in params:
            write_log("LOG: GRAPH_TYPE: {}".format(
                "KaHIP" if not params["gt"] else "KaHyPar"), params)

        # compile benchmark
        compile_circ_benchmarks(params)


def benchmark_circ(name, instance_metadata):
    os.chdir(CIRC_SOURCE)

    versions = []
    for ss in CIRC_PARTITION_SELECTION_SCHEMES:
        for ps in PARTITION_SIZES:
            for ml in MUT_LEVELS:
                for mss in MUT_STEP_SIZES:
                    for gt in PARTITIONERS:
                        for cm in COST_MODELS:
                            version = "run_{}_test-{}_ss-{}_ps-{}_ml-{}_mss-{}_gt-{}_cm-{}".format(
                                "circ", name, ss, ps, ml, mss, gt, cm)
                            bytecode_path = "{}_test-{}_ss-{}_ps-{}_ml-{}_mss-{}_gt-{}_cm-{}".format(
                                "circ", name, ss, ps, ml, mss, gt, cm)
                            params = {}
                            params["ss"] = ss
                            params["ps"] = ps
                            params["ml"] = ml
                            params["mss"] = mss
                            params["gt"] = gt
                            params["cm"] = cm
                            params["bytecode_path"] = bytecode_path
                            versions.append((version, params))
    for ss in CIRC_NO_PARTITION_SELECTION_SCHEMES:
        for cm in COST_MODELS:
            version = "run_{}_test-{}_ss-{}_cm-{}".format(
                "circ", name, ss, cm)
            bytecode_path = "{}_test-{}_ss-{}_cm-{}".format(
                "circ", name, ss, cm)
            params = {}
            params["ss"] = ss
            params["cm"] = cm
            params["bytecode_path"] = bytecode_path
            versions.append((version, params))

    for (version, params) in versions:
        params["system"] = "circ"
        params["name"] = name
        params["version"] = version

        log_path = format(
            "{}test_results/circ_{}/log_{}.txt".format(CIRC_BENCHMARK_SOURCE, name, version))
        failed_path = format(
            "{}test_results/circ_{}/failed_log_{}.txt".format(CIRC_BENCHMARK_SOURCE, name, version))
        if os.path.exists(log_path) or os.path.exists(failed_path):
            print("Benchmark already ran: {}".format(log_path))
            continue

        # write header
        write_log(DELIMITER, params)
        write_log("LOG: Benchmarking CirC", params)
        write_log(DELIMITER, params)
        write_log("LOG: TEST: {}".format(name), params)
        write_log("LOG: SELECTION_SCHEME: {}".format(params["ss"]), params)
        write_log("LOG: COST_MODEL: {}".format(params["cm"]), params)
        if "ps" in params:
            write_log("LOG: PARTITION_SIZE: {}".format(params["ps"]), params)
        if "ml" in params:
            write_log("LOG: MUTATION_LEVEL: {}".format(params["ml"]), params)
        if "mss" in params:
            write_log("LOG: MUTATION_STEP_SIZE: {}".format(
                params["mss"]), params)
        if "gt" in params:
            write_log("LOG: GRAPH_TYPE: {}".format(
                "KaHIP" if not params["gt"] else "KaHyPar"), params)

        # run benchmarks
        run_circ_benchmark(params, instance_metadata)
