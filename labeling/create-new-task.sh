#!/usr/bin/env bash
# A script for creating new Mindtagger task
# Author: Jaeho Shin <netj@cs.stanford.edu>
# Created: 2015-01-26
set -eu

Here=$(dirname "$0")
cd "$Here"

[[ $# -eq 1 ]] || {
    echo "Usage: $0 TASK_TYPE"
    echo " where TASK_TYPE is one of:"
    ls templates | sed 's/^/  /'
    false
}

if [ -f ../env_local.sh ]; then
  echo "Using env_local.sh"
  source ../env_local.sh
else
  echo "Using env.sh"
  source ../env.sh
fi

TaskType=$1; shift

task=$(date +%Y%m%d)-$TaskType
if [[ -e $task ]]; then
    suffix=2
    while [[ -e $task.$suffix ]]; do
        let ++suffix
    done
    task+=.$suffix
fi

#trap "rm -rf $task" ERR

# clone a task template
echo "Creating Mindtagger task $task from template"
cp -a templates/$TaskType $task

# optionally generate SQL to run for preparing input
if [[ -x $task/input-sql.sh ]]; then
    echo "Generating SQL query for the task..."
    $task/input-sql.sh "$@" >$task/input.sql
fi

# get input items for the task
echo "Running $task/input.sql to get input items from DeepDive database"
psql -h $DBHOST -p $DBPORT -U $DBUSER $DBNAME \
    <$task/input.sql >$task/input.csv

# optionally post-process the input csv
if [[ -x $task/postprocess ]]; then
  echo "Post-processing the input..."
  $task/postprocess $task/input.csv > $task/input_tmp.csv
  mv $task/input_tmp.csv $task/input.csv
fi

echo "Restart labeling/start-gui.sh again and choose task $task."
