#! /usr/bin/env python3

import re
from Extractor import RelationExtractor
from dstruct.RelationMention import RelationMention
from helper.easierlife import BASE_DIR

GENEHPOTERM_DICT_FILENAME = "/dicts/genes_to_hpo_terms_with_synonyms.tsv"

class RelationExtractor_GeneHPOterm(RelationExtractor):
    def __init__(self):
        # Load the gene to HPO term map dictionary
        # Actually a set of pairs
        self.genehpoterm_dict = set()
        with open(BASE_DIR + GENEHPOTERM_DICT_FILENAME, 'rt') as genehpoterm_dict_file:
            for line in genehpoterm_dict_file:
                gene, term, unused = line.strip().split("\t")
                self.genehpoterm_dict.add(frozenset(gene, term))

    # Perform the distant supervision
    def supervise(self, sentence, gene, hpoterm, relation):
        relation.is_correct = True


    # Extract the relation mentions
    def extract(self, sentence, gene, hpoterm):
        relation = RelationMention("GENEHPOTERM", gene, hpoterm)

        self.supervise(sentence, gene, hpoterm, relation)

        # Add features
        gene_start = int(gene.id.split("_")[4])
        hpoterm_start = int(hpoterm.id.split("_")[4])
        gene_end = int(gene.id.split("_")[5])
        hpoterm_end = int(hpoterm.id.split("_")[5])
        start = min(gene_start, hpoterm_start)
        end = max(gene_end, hpoterm_end)
        sent_words_between = " ".join([w.lemma for w in sentence.words[start:end]])

        # Present in the existing HPO mapping
        relation.add_features(["in_gene_hpoterm_map={}".format(int(frozenset((gene.symbol,
            gene.term)) in self.genehpoterm_dict))])

        # Verb between the two words, if present
        for word in sent_words_between:
                if re.search('VB\w*', word.pos):
                        relation.add_features(["verb="+word.lemma])
        # Word sequence between words
        relation.add_features(["word_seq="+"_".join(sent_words_between)])
        # Left and right windows
        if start > 0:
            relation.add_features(["window_left_1={}".format(sentence.words[start-1])])
        if end < len(sentence.words) - 1:
            relation.add_features(["window_right_1={}".format(sentence.words[end])])
        # Shortest dependency path between the two mentions
        gene_symbol = gene.symbol
        hpoterm_term = hpoterm.name.lower()
        relation.add_features([sentence.dep_path(gene_symbol, hpoterm_term),])

        return relation
