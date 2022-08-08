from util import *
import pandas as pd


def standardize_time(t):
    if t.endswith("ms"):
        return float(t[:-2]) / 1000
    if t.endswith("µs"):
        return float(t[:-2]) / (1000 * 1000)
    else:
        return float(t[:-1])


def parse_time_memory(tm):
    seconds = float(tm.split()[0])
    memory = float(tm.split()[2]) / 1000000
    return seconds, memory


def get_log_paths(system):
    assert system == "circ" or system == "hycc"
    test_results_path = "{}test_results/".format(CIRC_BENCHMARK_SOURCE)
    circ_paths = [os.path.join(test_results_path, f) for f in os.listdir(
        test_results_path) if f.startswith(system)]
    log_paths = []
    for p in circ_paths:
        if os.path.isdir(p):
            test_dir_path = p
            log_paths += [os.path.join(test_dir_path, f)
                          for f in os.listdir(test_dir_path) if f.startswith("log")]
        else:
            # parsing total time
            pass
    return log_paths


def clean_log(log):
    log = log.replace("LOG: ", "")
    log = log.replace("====================================", "")
    log = "\n".join([l for l in log.split(
        "\n") if not l.startswith("Benchmarking") and l])
    return log


def parse_hycc_log(log):
    log = clean_log(log)
    data = {}
    run = 0
    phase = ""
    for line in log.split("\n"):
        line = line.split(":")
        assert(len(line) == 2)

        line[0] = line[0].strip()
        line[1] = line[1].strip()

        if line[0] == "TEST":
            data[line[0]] = line[1]
        elif line[0] == "SELECTION_SCHEME":
            data[line[0]] = line[1]
            phase = "running"
        elif line[0] == "MINIMIZATION_TIME":
            data[line[0]] = int(line[1])
        elif line[0] == "ARGUMENTS":
            data[line[0]] = [l for l in line[1].replace(
                "['", " ").replace("']", " ").replace(",", " ").split() if l]
        elif line[0] == "COST_MODEL":
            data[line[0]] = line[1]
        elif line[0] == "MODE":
            phase = line[1]
        elif line[0] == "RERUN":
            # requires phase
            line[0] = "{} {}".format(line[0], phase)
            data[line[0]] = int(line[1])
            run = int(line[1])
        elif line[0] == "Time / Memory":
            # requires phase
            seconds, memory = parse_time_memory(line[1])
            data["Total_time_{}_{}".format(run, phase)] = seconds
            data["Total_memory_{}_{}".format(run, phase)] = memory
        elif line[0].endswith("time"):
            phase = "compile" if "Compile" in line[0] else "running"
            data[line[0]] = standardize_time(line[1])
        else:
            raise RuntimeError("Unknown key: {}".format(line[0]))
    return data


def parse_circ_log(log):
    log = clean_log(log)
    data = {}
    phase = "compile"
    run = 0
    for line in log.split("\n"):
        line = line.split(":")
        assert(len(line) == 2)

        line[0] = line[0].strip()
        line[1] = line[1].strip()

        if line[0] == "TEST":
            data[line[0]] = line[1]
        elif line[0] == "SELECTION_SCHEME":
            data[line[0]] = line[1]
        elif line[0] == "NUM_PARTS":
            data[line[0]] = line[1]
        elif line[0] == "MUTATION_LEVEL":
            data[line[0]] = line[1]
        elif line[0] == "MUTATION_STEP_SIZE":
            data[line[0]] = line[1]
        elif line[0] == "COST_MODEL":
            data[line[0]] = line[1]
        elif line[0] == "RERUN":
            # requires phase
            line[0] = "{} {}".format(line[0], phase)
            data[line[0]] = int(line[1])
            run = int(line[1])
        elif line[0] == "Frontend":
            data[line[0]] = standardize_time(line[1])
        elif line[0] == "Optimizations":
            data[line[0]] = standardize_time(line[1])
        elif "Assignment" in line[0]:
            if "Assignment" not in data:
                data["Assignment"] = {}
            assignment = line[0].split()
            if len(assignment) == 1:
                data["Assignment"]["total_"] = standardize_time(line[1])
            elif len(assignment) == 2:
                fname = assignment[1]
                data["Assignment"][fname] = standardize_time(line[1])
            else:
                raise RuntimeError("Assignment mismatch: {}".format(line[0]))
        elif line[0] == "Time / Memory":
            # requires phase
            seconds, memory = parse_time_memory(line[1])
            data["Total_time_{}_{}".format(run, phase)] = seconds
            data["Total_memory_{}_{}".format(run, phase)] = memory
        elif line[0] == "Lowering":
            data[line[0]] = standardize_time(line[1])
        elif line[0] == "Compile":
            data[line[0]] = standardize_time(line[1])
        elif line[0].endswith("time"):
            phase = "running"
            data[line[0]] = standardize_time(line[1])
        else:
            raise RuntimeError("Unknown key: {}".format(line[0]))

    return data


def write_csv(df, log_path):
    header = "{}csvs/".format(CIRC_BENCHMARK_SOURCE)
    log_path = log_path.split("/")
    dir_path = os.path.join(header, log_path[-2])
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

    version = log_path[-1].split(".")[0]+".csv"
    csv_path = os.path.join(dir_path, version)
    df.to_csv(csv_path)


def parse_hycc_logs():
    log_paths = get_log_paths("hycc")
    datas = []
    compile_path = ""
    run_path = ""
    for log_path in log_paths:
        if "log_compile" in log_path:
            compile_path = log_path
        else:
            run_path = log_path
        with open(log_path, "r") as f:
            log = f.read()
            data = parse_hycc_log(log)
            datas.append(data)

    # write compile data
    compile_data = [d for d in datas if "SELECTION_SCHEME" not in d][0]
    write_csv(pd.DataFrame(compile_data), compile_path)

    # clean run_path
    run_data = [d for d in datas if "SELECTION_SCHEME" in d]
    run_path = "/".join(run_path.split("/")[:-1]) + "/" + \
        run_path.split("/")[-1].split("_ss-")[0] + ".txt"
    merged_data = {}
    for d in run_data:
        for (k, v) in d.items():
            if k not in merged_data:
                merged_data[k] = []
            merged_data[k].append(v)
    write_csv(pd.DataFrame(merged_data), run_path)


def parse_circ_logs():
    log_paths = get_log_paths("circ")
    datas = []
    for log_path in log_paths:
        with open(log_path, "r") as f:
            log = f.read()
            data = parse_circ_log(log)
            datas.append(data)

    merged_data = {}
    for d in datas:
        for (k, v) in d.items():
            if k not in merged_data:
                merged_data[k] = []
            merged_data[k].append(v)

    run_path = "/".join(log_path.split("/")[:-1]) + "/" + log_path.split("/")[-1].split("_ss-")[
        0] + "_" + "_".join(log_path.split("/")[-1].split("_ss-")[1].split("_")[1:]) + ".txt"
    write_csv(pd.DataFrame(merged_data), run_path)
