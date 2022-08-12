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


def clean_data(data):
    merged_data = {}
    all_keys = []
    for d in data:
        for k in d.keys():
            if k not in all_keys:
                all_keys.append(k)

    for k in all_keys:
        for d in data:
            if k not in merged_data:
                merged_data[k] = []
            if k in d:
                merged_data[k].append(d[k])
            else:
                merged_data[k].append("")
    return merged_data


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
    for line in log.split("\n"):
        line = line.split(":")

        line[0] = line[0].strip()
        line[1] = line[1].strip()

        if line[0] == "TEST":
            data[line[0]] = line[1]
        elif line[0] == "SELECTION_SCHEME":
            data[line[0]] = line[1]
        elif line[0] == "MINIMIZATION_TIME":
            data[line[0]] = int(line[1])
        elif line[0] == "ARGUMENTS":
            data[line[0]] = [l for l in line[1].replace(
                "['", " ").replace("']", " ").replace(",", " ").split() if l]
        elif line[0] == "COST_MODEL":
            data[line[0]] = line[1]
        elif line[0] == "MODE":
            if line[0] not in data:
                data[line[0]] = []
            data[line[0]].append(line[1])
        elif line[0] == "RERUN":
            if line[0] not in data:
                data[line[0]] = []
            data[line[0]].append(int(line[1]))
        elif line[0] == "Time / Memory":
            seconds, memory = parse_time_memory(line[1])
            if "Total_time" not in data:
                data["Total_time"] = []
            if "Total_memory" not in data:
                data["Total_memory"] = []
            data["Total_time"].append(seconds)
            data["Total_memory"].append(memory)
        elif line[0].endswith("time"):
            data[line[0]] = standardize_time(line[1])
        elif line[0] == "Missing":
            data["MISSING"] = "missing"
        elif "Error" in line[0]:
            if "ERROR" not in data:
                data["ERROR"] = []
            data["ERROR"].append(" ".join(line[1:]))
        elif "Failed" in line[0]:
            if "FAIL" not in data:
                data["FAIL"] = []
            data["FAIL"].append(" ".join(line[1:]))
        else:
            print(line)
            raise RuntimeError("Unknown key")
    return data


def parse_circ_log(log):
    log = clean_log(log)
    data = {}
    for line in log.split("\n"):
        line = line.split(":")
        assert(len(line) == 2)

        line[0] = line[0].strip()
        line[1] = line[1].strip()

        if line[0] == "TEST":
            data[line[0]] = line[1]
        elif line[0] == "SELECTION_SCHEME":
            data[line[0]] = line[1]
        elif line[0] == "PARTITION_SIZE":
            data[line[0]] = line[1]
        elif line[0] == "MUTATION_LEVEL":
            data[line[0]] = line[1]
        elif line[0] == "MUTATION_STEP_SIZE":
            data[line[0]] = line[1]
        elif line[0] == "GRAPH_TYPE":
            data[line[0]] = "KaHIP" if line[1].strip() == "0" else "KaHyPar"
        elif line[0] == "COST_MODEL":
            data[line[0]] = line[1]
        elif line[0] == "Number of Partitions":
            data["NUM_PARTS"] = line[1]
        elif line[0] == "MODE":
            continue
        elif line[0] == "RERUN":
            if line[0] not in data:
                data[line[0]] = []
            data[line[0]].append(int(line[1]))
        elif line[0] == "Frontend":
            data[line[0]] = standardize_time(line[1])
        elif line[0] == "Optimizations":
            data[line[0]] = standardize_time(line[1])
        elif "Assignment" in line[0]:
            if line[0] == "Assignment cost of partition":
                # cost per partition ilp
                if "assignment_cost" not in data:
                    data["assignment_cost"] = []
                data["assignment_cost"].append(float(line[1]))
            elif line[0] == "Assignment time":
                # total solving time 
                data["assignment_time"] = standardize_time(line[1])
            else:
                raise RuntimeError("Assignment mismatch: {}".format(line[0]))
        elif line[0] == "Time / Memory":
            # requires phase
            seconds, memory = parse_time_memory(line[1])
            if "Total_time" not in data:
                data["Total_time"] = []
            if "Total_memory" not in data:
                data["Total_memory"] = []
            data["Total_time"].append(seconds)
            data["Total_memory"].append(memory)
        elif line[0] == "Lowering":
            data[line[0]] = standardize_time(line[1])
        elif line[0] == "Compile":
            data[line[0]] = standardize_time(line[1])
        elif line[0].endswith("time"):
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
    print(csv_path)
    df.to_csv(csv_path)

def clean_data(data):
    merged_data = {}
    all_keys = []
    for d in data:
        for k in d.keys():
            if k not in all_keys:
                all_keys.append(k)

    for k in all_keys:
        for d in data:
            if k not in merged_data:
                merged_data[k] = []
            if k in d:
                merged_data[k].append(d[k])
            else:
                merged_data[k].append("")
    return merged_data


def parse_hycc_logs():
    log_paths = get_log_paths("hycc")
    compile_datas = []
    run_datas = []
    for log_path in log_paths:
        data = {}
        with open(log_path, "r") as f:
            log = f.read()
            data = parse_hycc_log(log)
        if "log_compile" in log_path:
            compile_datas.append(data)
        else:
            run_datas.append(data)

    # clean compile data
    compile_data = clean_data(compile_datas)

    # write compile data
    compile_path = CIRC_BENCHMARK_SOURCE + "csvs/hycc/compile_data.txt"
    write_csv(pd.DataFrame(compile_data), compile_path)

    # clean run data
    run_data = clean_data(run_datas)

    # clean run_path
    run_path = CIRC_BENCHMARK_SOURCE + "csvs/hycc/run_data.txt"
    write_csv(pd.DataFrame(run_data), run_path)
    

def parse_circ_logs():
    log_paths = get_log_paths("circ")
    compile_datas = []
    run_datas = []
    for log_path in log_paths:
        with open(log_path, "r") as f:
            data = {}
            with open(log_path, "r") as f:
                log = f.read()
                data = parse_circ_log(log)

            if "log_compile" in log_path:
                compile_datas.append(data)
            else:
                run_datas.append(data)

   # clean compile data
    compile_data = clean_data(compile_datas)

    # write compile data
    compile_path = CIRC_BENCHMARK_SOURCE + "csvs/circ/compile_data.txt"
    write_csv(pd.DataFrame(compile_data), compile_path)

    # clean run data
    run_data = clean_data(run_datas)

    # clean run_path
    run_path = CIRC_BENCHMARK_SOURCE + "csvs/circ/run_data.txt"
    write_csv(pd.DataFrame(run_data), run_path)
