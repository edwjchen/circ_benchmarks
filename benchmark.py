from util import *

################################################################################
# Benchmark hycc
################################################################################

def build_mpc_circuit(test_path, args=[]):
    os.chdir(TMP_PATH)
    cmd = [PARENT_DIR+CBMC_GC, test_path, "--minimization-time-limit", str(MINIMIZATION_TIME)] + args
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    os.chdir(PARENT_DIR)
    write_output_to_log(result.stdout)
    write_to_run(result.stdout)

def optimize_selection(costs_path=COSTS):
    os.chdir(TMP_PATH)
    subprocess.run(["python3", PARENT_DIR+MODULE_BUNDLE, "."], check=True)
    subprocess.run(["python3", PARENT_DIR+SELECTION, ".", PARENT_DIR+costs_path], check=True)
    os.chdir(PARENT_DIR)

def run_sim(spec_file):
    for i in range(RERUN):
        write_to_log("Using HyCC CIRCUIT-SIM")
        write_to_log("RERUN: {}".format(i))
        os.chdir(TMP_PATH)
        cmd = [PARENT_DIR+CIRCUIT_SIM, MPC_CIRC, "--spec-file", PARENT_DIR+spec_file]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        os.chdir(PARENT_DIR)

        write_output_to_log(result.stdout)
        write_to_run(result.stdout)
    
def run_aby(spec_file, args=[]):
    for i in range(RERUN):
        write_to_log("Using ABY-HYCC")
        write_to_log("RERUN: {}".format(i))
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

        write_output_to_log(server_out)
        write_to_run(server_out)
        write_output_to_log(client_out)
        write_to_run(client_out)

def run_aby_sim(spec_file):
    run_aby(spec_file, [MPC_CIRC])

def run_yaoonly(spec_file):
    write_to_both(DELIMITER)
    write_to_both("Running HyCC yaonly")
    run_aby(spec_file, ["-c", "yaoonly.cmb"])

def run_yaohybrid(spec_file):
    write_to_both(DELIMITER)
    write_to_both("Running HyCC yaohybrid")
    run_aby(spec_file, ["-c", "yaohybrid.cmb"])

def run_gmwonly(spec_file):
    write_to_both(DELIMITER)
    write_to_both("Running HyCC gmwonly")
    run_aby(spec_file, ["-c", "gmwonly.cmb"])

def run_gmwhyrbid(spec_file):
    write_to_both(DELIMITER)
    write_to_both("Running HyCC gmwhybrid")
    run_aby(spec_file, ["-c", "gmwhybrid.cmb"])

def run_optimized(spec_file):
    write_to_both(DELIMITER)
    write_to_both("Running HyCC ps_optimized")
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
        if os.getcwd().endswith("tmp"):
            os.chdir(PARENT_DIR)
        write_to_both("Compilation of all_benchmarks failed with args: {}".format(args))
    remove_tmp()

def benchmark_hycc_biomatch():
    write_to_both(DELIMITER)
    write_to_both("Benchmarking HyCC")
    write_to_both(DELIMITER)

    test_path = PARENT_DIR + HYCC_SOURCE + "/examples/benchmarks/biomatch/biomatch.c"
    spec_file = "tests/hycc/biomatch_1.spec"

    write_to_both("TEST PATH: {}".format(test_path))
    write_to_both("SPEC_FILE: {}".format(spec_file))
    write_to_both("MINIMIZATION TIME: {}".format(MINIMIZATION_TIME))
    write_to_both(DELIMITER)

    # benchmark cbmc-gc benchmarks 
    run_benchmark(test_path, spec_file)
    write_to_both(DELIMITER)

    # benchmark cbmc-gc benchmarks 
    args=["--all-variants"]
    write_to_both("Running with args: {}".format(args))
    run_all_benchmarks(test_path, spec_file, args)
    write_to_both(DELIMITER)

    args=["--all-variants", "--outline"]
    write_to_both("Running with args: {}".format(args))
    run_all_benchmarks(test_path, spec_file, args)
    write_to_both(DELIMITER)


################################################################################
# Benchmark circ
################################################################################


def benchmark_boolean_only():
    # benchmark boolean only
    print("Running CirC boolean only")
    write_to_both("Running CirC boolean only")
    os.chdir(CIRC_SOURCE)
    subprocess.run(["python3", "driver.py", "-F", "aby", "c"], check=True)
    result = subprocess.run(["python3", "driver.py", "--benchmark", str(RERUN), COST_MODEL, "b"], check=True, capture_output=True, text=True)
    os.chdir(PARENT_DIR+PARENT_DIR)
    write_output_to_log(result.stdout)
    write_to_run(result.stdout)


def benchmark_yao_only():
    # benchmark yao only
    print("Running CirC yao only")
    write_to_both("Running CirC yao only")
    os.chdir(CIRC_SOURCE)
    subprocess.run(["python3", "driver.py", "-F", "aby", "c"], check=True)
    result = subprocess.run(["python3", "driver.py", "--benchmark", str(RERUN), COST_MODEL, "y"], check=True, capture_output=True, text=True)
    os.chdir(PARENT_DIR+PARENT_DIR)
    write_output_to_log(result.stdout)
    write_to_run(result.stdout)

def benchmark_arithmetic_and_boolean():
    # benchmark a+b 
    print("Running CirC a+b")
    write_to_both("Running CirC a+b")
    os.chdir(CIRC_SOURCE)
    subprocess.run(["python3", "driver.py", "-F", "aby", "c"], check=True)
    result = subprocess.run(["python3", "driver.py", "--benchmark", str(RERUN), COST_MODEL, "a+b"], check=True, capture_output=True, text=True)
    os.chdir(PARENT_DIR+PARENT_DIR)
    write_output_to_log(result.stdout)
    write_to_run(result.stdout)

def benchmark_arithmetic_and_yao():
    # benchmark a+y
    print("Running CirC a+y")
    write_to_both("Running CirC a+y")
    os.chdir(CIRC_SOURCE)
    subprocess.run(["python3", "driver.py", "-F", "aby", "c"], check=True)
    result = subprocess.run(["python3", "driver.py", "--benchmark", str(RERUN), COST_MODEL, "a+y"], check=True, capture_output=True, text=True)
    os.chdir(PARENT_DIR+PARENT_DIR)
    write_output_to_log(result.stdout)
    write_to_run(result.stdout)

def benchmark_greedy():
    # benchmark greedy
    print("Running CirC greedy")
    write_to_both("Running CirC greedy")
    os.chdir(CIRC_SOURCE)
    subprocess.run(["python3", "driver.py", "-F", "aby", "c"], check=True)
    result = subprocess.run(["python3", "driver.py", "--benchmark", str(RERUN), COST_MODEL, "greedy"], check=True, capture_output=True, text=True)
    os.chdir(PARENT_DIR+PARENT_DIR)
    write_output_to_log(result.stdout)
    write_to_run(result.stdout)

def benchmark_lp():
    # benchmark LP
    print("Running CirC LP")
    write_to_both("Running CirC LP")
    os.chdir(CIRC_SOURCE)
    subprocess.run(["python3", "driver.py", "-F", "aby", "c", "lp"], check=True)
    result = subprocess.run(["python3", "driver.py", "--benchmark", str(RERUN), COST_MODEL, "lp"], check=True, capture_output=True, text=True)
    os.chdir(PARENT_DIR+PARENT_DIR)
    write_output_to_log(result.stdout)
    write_to_run(result.stdout)

def benchmark_glp():
    # benchmark global LP
    print("Running CirC global LP")
    write_to_both("Running CirC global LP")
    os.chdir(CIRC_SOURCE)
    subprocess.run(["python3", "driver.py", "-F", "aby", "c", "lp"], check=True)
    result = subprocess.run(["python3", "driver.py", "--benchmark", str(RERUN), COST_MODEL, "glp"], check=True, capture_output=True, text=True)
    os.chdir(PARENT_DIR+PARENT_DIR)
    write_output_to_log(result.stdout)
    write_to_run(result.stdout)

def benchmark_circ_biomatch():    
    write_to_both(DELIMITER)
    write_to_both("Benchmarking CirC")
    write_to_both(DELIMITER)

    # TODO: modularize test path 

    # run benchmarks
    benchmark_boolean_only()
    benchmark_yao_only()
    benchmark_arithmetic_and_boolean()
    benchmark_arithmetic_and_yao()
    benchmark_greedy()
    benchmark_lp()
    benchmark_glp()

    write_to_both(DELIMITER)