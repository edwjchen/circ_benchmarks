#!/usr/bin/env python3

import os
import argparse
import subprocess

ABY_SOURCE = "./modules/ABY"
HYCC_SOURCE = "./modules/HyCC"
ABY_HYCC = HYCC_SOURCE+"/aby-hycc"
ABY_HYCC_DIR = ABY_SOURCE +"/src/examples/aby-hycc/"
ABY_CMAKE = ABY_SOURCE + "/src/examples/CMakeLists.txt"

def install():
    def verify_path_empty(path) -> bool:
        return not os.path.isdir(path) or (os.path.isdir(path) and not os.listdir(path)) 

    if verify_path_empty(ABY_SOURCE):
        subprocess.run(["git", "submodule", "init", "modules/ABY"])
        subprocess.run(["git", "submodule", "update"])

    if verify_path_empty(HYCC_SOURCE):
        subprocess.run(["git", "submodule", "init", "modules/HyCC"])
        subprocess.run(["git", "submodule", "update"])

    # install python requirements
    subprocess.run(["pip3", "install", "-r", "requirements.txt"])

def build():
    install()

    # build hycc
    subprocess.run(["./scripts/build_hycc.zsh"], check=True)

    # install hycc aby dependency
    if not os.path.isdir(ABY_HYCC_DIR):
        subprocess.run(["cp", "-r", ABY_HYCC, ABY_HYCC_DIR], check=True)
        with open(ABY_CMAKE,'a') as f:
            print("add_subdirectory(aby-hycc)",file=f)

    # build aby
    subprocess.run(["./scripts/build_aby.zsh"], check=True)

def test():
    build()

    # test HyCC biomatch


def benchmark():
    pass

def clean():
    print("cleaning")
    subprocess.run(["./scripts/clean_aby.zsh"], check=True)
    subprocess.run(["./scripts/clean_hycc.zsh"], check=True)

def delete():
    print("fresh install!")
    subprocess.run(["rm", "-rf", "modules/ABY"])
    subprocess.run(["rm", "-rf", "modules/HyCC"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--install", action="store_true", help="install all dependencies")
    parser.add_argument("-b", "--build", action="store_true", help="build depedencies")
    parser.add_argument("-t", "--test", action="store_true", help="test")
    parser.add_argument("--benchmark", action="store_true", help="benchmark hycc")
    parser.add_argument("-c", "--clean", action="store_true", help="remove all generated files")
    parser.add_argument("--delete", action="store_true", help="Reinstall submodules")
    args = parser.parse_args()


    def verify_single_action(args: argparse.Namespace):
        actions = [k for k, v in vars(args).items() if (type(v) is bool or k in ["features"]) and bool(v)]
        if len(actions) != 1:
            parser.error("parser error: only one action can be specified. got: " + " ".join(actions))
    verify_single_action(args)

    if args.install:
        install()

    if args.build:
        build()

    if args.test:
        test()

    if args.benchmark:
        benchmark()

    if args.clean:
        clean()

    if args.delete:
        delete()