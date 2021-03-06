#!/usr/bin/env bash
# Author: Alex Ratner <ajratner@stanford.edu>
# Created: 2015-01-25

# CREATE TABLE doc_source (doc_id TEXT, source TEXT) DISTRIBUTED BY (doc_id);
# COPY doc_source (doc_id, source) FROM '/lfs/local/0/ajratner/Genomics_docid2journal.tsv' DELIMITER '\t';

set -eu

# TODO(alex): switch to new table names!
case $1 in
gene_mentions)
  m="mention"
  ;;
hpoterm_mentions)
  m="mention"
  ;;
gene_hpoterm_relations)
  m="relation"
  ;;
esac

# Generate the SQL for this task
echo "
  COPY (
    SELECT
      ds.source,
      count(m.*) as total_count,
      count(case when m.is_correct then 1 end) as labeled_true,
      count(case when not m.is_correct then 1 end) as labeled_false,
      count(case when m.is_correct is null and ib.bucket = 0 then 1 end) as bucket_0,
      count(case when m.is_correct is null and ib.bucket = 1 then 1 end) as bucket_1,
      count(case when m.is_correct is null and ib.bucket = 2 then 1 end) as bucket_2,
      count(case when m.is_correct is null and ib.bucket = 3 then 1 end) as bucket_3,
      count(case when m.is_correct is null and ib.bucket = 4 then 1 end) as bucket_4,
      count(case when m.is_correct is null and ib.bucket = 5 then 1 end) as bucket_5,
      count(case when m.is_correct is null and ib.bucket = 6 then 1 end) as bucket_6,
      count(case when m.is_correct is null and ib.bucket = 7 then 1 end) as bucket_7,
      count(case when m.is_correct is null and ib.bucket = 8 then 1 end) as bucket_8,
      count(case when m.is_correct is null and ib.bucket = 9 then 1 end) as bucket_9
    FROM
      ${1} m
    LEFT JOIN
      doc_source ds ON m.doc_id = ds.doc_id
    LEFT JOIN
      ${1}_is_correct_inference_bucketed ib ON m.doc_id = ib.doc_id
    WHERE
      m.${m}_id = ib.${m}_id
    GROUP BY
      ds.source
  ) TO STDOUT WITH CSV HEADER;
"
