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
        write_to_both("Using HyCC CIRCUIT-SIM")
        write_to_both("RERUN: {}".format(i))
        os.chdir(TMP_PATH)
        cmd = [PARENT_DIR+CIRCUIT_SIM, MPC_CIRC, "--spec-file", PARENT_DIR+spec_file]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        os.chdir(PARENT_DIR)

        write_output_to_log(result.stdout)
        write_to_run(result.stdout)
    
def run_aby(spec_file, args=[]):
    for i in range(RERUN):
        write_to_both("Using ABY-HYCC")
        write_to_both("RERUN: {}".format(i))
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


def run_circ_benchmark(name):
    print("Running CirC {}".format(name))
    write_to_both("Running CirC {}".format(name))
    for i in range(RERUN):
        write_to_both("RERUN: {}".format(i))
        os.chdir(CIRC_SOURCE)
        result = subprocess.run(["./scripts/build_mpc_c_benchmark.zsh", COST_MODEL, name], check=True, capture_output=True, text=True)
        os.chdir(PARENT_DIR+PARENT_DIR)
        write_output_to_log(result.stdout)
        write_to_run(result.stdout)

        os.chdir(CIRC_SOURCE)
        result = subprocess.run(["python3", "./scripts/aby_tests/c_benchmark_aby.py"], check=True, capture_output=True, text=True)
        os.chdir(PARENT_DIR+PARENT_DIR)
        write_output_to_log(result.stdout)
        write_to_run(result.stdout)
    write_to_both("\n")


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

def benchmark_glp():
    # benchmark global LP
    run_circ_benchmark("glp")

def benchmark_circ_biomatch():    
    write_to_both(DELIMITER)
    write_to_both("Benchmarking CirC")
    write_to_both(DELIMITER)

    # build benchmarks
    os.environ['ABY_SOURCE'] = "../ABY"
    os.chdir(CIRC_SOURCE)
    subprocess.run(["python3", "driver.py", "-F", "aby", "c", "lp"], check=True)
    subprocess.run(["python3", "driver.py", "--benchmark"], check=True)
    os.chdir(PARENT_DIR+PARENT_DIR)

    # run benchmarks
    benchmark_boolean_only()
    benchmark_yao_only()
    benchmark_arithmetic_and_boolean()
    benchmark_arithmetic_and_yao()
    benchmark_greedy()
    benchmark_lp()
    benchmark_glp()

    write_to_both(DELIMITER)