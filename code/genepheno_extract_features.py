#!/usr/bin/env python
import extractor_util as util
from collections import namedtuple
import os
import sys
import ddlib
from treedlib import corenlp_to_xmltree, get_relation_features, get_relation_binning_features

parser = util.RowParser([
          ('relation_id', 'text'),
          ('doc_id', 'text'),
          ('section_id', 'text'),
          ('sent_id', 'int'),
          ('gene_mention_id', 'text'),
          ('gene_wordidxs', 'int[]'),
          ('pheno_mention_id', 'text'),
          ('pheno_wordidxs', 'int[]'),
          ('words', 'text[]'),
          ('lemmas', 'text[]'),
          ('poses', 'text[]'),
          ('ners', 'text[]'),
          ('dep_paths', 'text[]'),
          ('dep_parents', 'int[]'),
          ('num_gene_candidates', 'int'),
          ('num_pheno_candidates', 'int')])


Feature = namedtuple('Feature', ['doc_id', 'section_id', 'relation_id', 'name'])

CoreNLPSentence = namedtuple('CoreNLPSentence', 'words, lemmas, poses, ners, dep_labels, dep_parents')

onto_path = lambda p : '%s/onto/%s' % (os.environ['GDD_HOME'], p)

# Compile the feature generator
GENES = [line.split('\t')[1] for line in open(onto_path('data/ensembl_genes.tsv'))]
PHENOS = [line.split('\t')[1] for line in open(onto_path('manual/pheno_terms.tsv'), 'rb')] + [line.split('\t')[1] for line in open(onto_path('manual/disease_terms.tsv'), 'rb')]

generate_features = compile_relation_feature_generator(dictionaries={
  'GENE'  : GENES,
  'PHENO' : PHENOS
})

def get_features_for_candidate_treedlib(r):
  """Extract features using treedlib"""
  features = []
  f = Feature(doc_id=r.doc_id, section_id=r.section_id, relation_id=r.relation_id, name=None)
  s = CoreNLPSentence(words=r.words, lemmas=r.lemmas, poses=r.poses, ners=r.ners, dep_labels=r.dep_paths, dep_parents=r.dep_parents)

  # Create XMLTree representation of sentence
  xt = corenlp_to_xmltree(s)

  # Get features
  for feature in get_relation_features(xt.root, r.gene_wordidxs, r.pheno_wordidxs):
    yield f._replace(name=feature)

if __name__ == '__main__':
  util.run_main_tsv(row_parser=parser.parse_tsv_row, row_fn=get_features_for_candidate_treedlib)
