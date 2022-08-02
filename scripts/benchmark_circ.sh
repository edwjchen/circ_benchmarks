#!/bin/bash 

disable -r time

case "$OSTYPE" in 
    darwin*)
        alias measure_time="gtime --format='LOG: Time / Memory: %e seconds %M kB'"
    ;;
    linux*)
        alias measure_time="time --format='LOG: Time / Memory: %e seconds %M kB'"
    ;;
esac

# biomatch
measure_time ./ABY/build/bin/aby_interpreter -m mpc -f ./circ/scripts/aby_tests/tests/biomatch_c -t ./circ/scripts/aby_tests/test_inputs/biomatch_1.txt --address $1 -r $2

# kmeans 
measure_time ./ABY/build/bin/aby_interpreter -m mpc -f ./circ/scripts/aby_tests/tests/2pc_kmeans__c -t ./circ/scripts/aby_tests/test_inputs/kmeans.txt --address $1 -r $2

# gauss
measure_time ./ABY/build/bin/aby_interpreter -m mpc -f ./circ/scripts/aby_tests/tests/2pc_gauss_inline_c -t ./circ/scripts/aby_tests/test_inputs/gauss.txt --address $1 -r $2

# db
measure_time ./ABY/build/bin/aby_interpreter -m mpc -f ./circ/scripts/aby_tests/tests/db_join_c -t ./circ/scripts/aby_tests/test_inputs/db_join.txt --address $1 -r $2
measure_time ./ABY/build/bin/aby_interpreter -m mpc -f ./circ/scripts/aby_tests/tests/db_join2_c -t ./circ/scripts/aby_tests/test_inputs/join2.txt --address $1 -r $2
measure_time ./ABY/build/bin/aby_interpreter -m mpc -f ./circ/scripts/aby_tests/tests/db_merge_c -t ./circ/scripts/aby_tests/test_inputs/merge.txt --address $1 -r $2

# mnist
measure_time ./ABY/build/bin/aby_interpreter -m mpc -f ./circ/scripts/aby_tests/tests/mnist_c -t ./circ/scripts/aby_tests/test_inputs/mnist.txt --address $1 -r $2

# cryptonets 
measure_time ./ABY/build/bin/aby_interpreter -m mpc -f ./circ/scripts/aby_tests/tests/cryptonets_c -t ./circ/scripts/aby_tests/test_inputs/cryptonets.txt --address $1 -r $2

# histogram
measure_time ./ABY/build/bin/aby_interpreter -m mpc -f ./circ/scripts/aby_tests/tests/histogram_c -t ./circ/scripts/aby_tests/test_inputs/histogram.txt --address $1 -r $2