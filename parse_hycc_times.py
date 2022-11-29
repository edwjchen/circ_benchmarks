from util import *
import pandas as pd
import numpy as np


def standardize_time(t):
    if t.endswith("ms"):
        return float(t[:-2]) * 1000
    if t.endswith("µs"):
        return float(t[:-2]) * (1000 * 1000)
    else:
        return float(t[:-1]) * 1000


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


def get_log_paths(system, role):
    assert system == "circ" or system == "hycc"
    test_results_path = "{}/{}/run_test_results/".format(
        CIRC_BENCHMARK_SOURCE, role)
    paths = [os.path.join(test_results_path, f) for f in os.listdir(
        test_results_path) if f.startswith(system)]
    log_paths = []
    for p in paths:
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


def parse_hycc_log(log, setting):
    log = clean_log(log)
    data = {}
    for line in log.split("\n"):
        line = line.split(":")

        line[0] = line[0].strip()
        line[1] = line[1].strip()

        if line[0] == 'retry':
            continue

        if line[0] == "TEST":
            data[line[0]] = line[1]
        elif line[0] == "SELECTION_SCHEME":
            data[line[0]] = line[1]+"_"+setting
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
            if line[0] not in data:
                data[line[0]] = []
            data[line[0]].append(standardize_time(line[1]))
        elif line[0] == "Total number of gates":
            data[line[0]] = int(line[1])
        elif line[0] == "Total depth":
            data[line[0]] = int(line[1])
        elif "Timing" in line[0]:
            key = line[0].split()[1] + " Time"
            data[key] = standardize_time(line[1])
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


def parse_hycc_logs(role):
    log_paths = get_log_paths("hycc", role)
    run_datas = []
    setting = ""
    for log_path in log_paths:
        setting = ""
        if log_path.endswith("LAN.txt"):
            setting = "lan"
        elif log_path.endswith("WAN.txt"):
            setting = "wan"
        else:
            print(log_path)
            raise RuntimeError("Unknown setting")

        data = {}
        print(log_path)
        with open(log_path, "r") as f:
            log = f.read()
            data = parse_hycc_log(log, setting)
            run_datas.append(data)
    run_data = clean_data(run_datas)
    df = pd.DataFrame(run_data)

    tests = df["TEST"].unique()
    selection_schemes = df["SELECTION_SCHEME"].unique()
    best_results = {}
    for test in run_tests:
        best_results[test] = {}
        min_optimized_lan = 1000000
        min_optimized_scheme_lan = ""
        min_optimized_lan_times = []

        min_optimized_wan = 1000000
        min_optimized_scheme_wan = ""
        min_optimized_wan_times = []

        min_lan = 1000000
        min_scheme_lan = ""
        min_lan_times = []

        min_wan = 1000000
        min_scheme_wan = ""
        min_wan_times = []

        for ss in selection_schemes:
            exec_times = "Server exec time" if "Server exec time" in df.columns else "Client exec time"
            server_exec_times = list(df[(df["TEST"] == test) & (
                df["SELECTION_SCHEME"] == ss)][exec_times])
            if len(server_exec_times) >= 1:
                times = server_exec_times[0]
                if times:
                    print(test, ss)
                    t = np.min(server_exec_times[0])
                    print(t)

                    if "optimized" in ss and "lan" in ss and t < min_optimized_lan and "hycc" not in ss:
                        min_optimized_lan = t
                        min_optimized_scheme_lan = ss
                        min_optimized_lan_times = times

                    if "optimized" in ss and "wan" in ss and t < min_optimized_wan and "hycc" not in ss:
                        min_optimized_wan = t
                        min_optimized_scheme_wan = ss
                        min_optimized_wan_times = times

                    if "optimized" not in ss and "lan" in ss and t < min_lan:
                        min_lan = t
                        min_scheme_lan = ss
                        min_lan_times = times

                    if "optimized" not in ss and "wan" in ss and t < min_wan:
                        min_wan = t
                        min_scheme_wan = ss
                        min_wan_times = times

                best_results[test][ss] = times

        print()
        print("==== results ====")
        if min_scheme_lan:
            print(test)
            print("min lan:", min_scheme_lan)
            print("min lan time:", min_lan)
            print()
            best_results[test][min_scheme_lan] = min_lan_times

        if min_optimized_scheme_lan:
            print(test)
            print("min opt lan:", min_optimized_scheme_lan)
            print("min opt lan time:", min_optimized_lan)
            print()
            best_results[test][min_optimized_scheme_lan] = min_optimized_lan_times

        if min_scheme_wan:
            print(test)
            print("min wan:", min_scheme_wan)
            print("min wan time:", min_wan)
            print()
            best_results[test][min_scheme_wan] = min_wan_times

        if min_optimized_scheme_wan:
            print(test)
            print("min opt wan:", min_optimized_scheme_wan)
            print("min opt wan time:", min_optimized_wan)
            print()
            best_results[test][min_optimized_scheme_wan] = min_optimized_wan_times

        print()
        print("=========================================")
        print()
    print(tests)
    best_results_df = pd.DataFrame(best_results)
    best_results_df.to_csv(f"analysis/hycc_res_{role}.csv")


run_tests = [
    'biomatch',
    'kmeans',
    'gcd',
    'histogram',
    'db_merge',
    'db_join2',
    'gauss',
    'mnist',
    'cryptonets',
]
parse_hycc_logs("server")
parse_hycc_logs("client")
