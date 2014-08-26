#! /bin/sh
#
# Load a TSV file into a table using PostgreSQL COPY FROM command
#
# First argument is the database name
# Second argument is the table name
# Third argument is the path to the TSV file

abs_real_path () { 
	case "$1" in 
		/*) TSV_FILE_ABS_PATH=`readlink -f $1`
			;;
		*)  TSV_FILE_ABS_PATH=`readlink -f $PWD/$1`
			;;
	esac; 
}

if [ $# -ne 3 ]; then
	echo "$0: ERROR: wrong number of arguments" >&2
	echo "$0: USAGE: $0 DB TABLE FILE" >&2
	exit 1
fi

if [ ! -r $3 ]; then
	echo "$0: ERROR: TSV file not readable" >&2
	exit 1
fi

SQL_COMMAND_FILE=`mktemp /tmp/ctff.XXXXX` || exit 1
abs_real_path $3
echo "COPY $2 FROM '${TSV_FILE_ABS_PATH}';" > ${SQL_COMMAND_FILE}
psql -X --set ON_ERROR_STOP=1 -d $1 -f ${SQL_COMMAND_FILE} || exit 1
rm ${SQL_COMMAND_FILE}

