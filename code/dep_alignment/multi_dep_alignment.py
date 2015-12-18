#! /usr/bin/env python

import numpy as np
from alignment_util import AlignmentMixin, MatchCell
import sys
import copy

class MultiDepAlignment(AlignmentMixin):

  word_match_score = 5
  dict_match_score = 5
  lemma_match_score = 5
  pos_tag_match_score = -4
  skip_score = -3
  mismatch_score = -5
  cand_match_score = 15
  
  short_words = set([',', '.', '-lrb-', '-rrb-', 'is', 'the', 'of', 'for', 'with', 'on', 'to', 'from', 'in', 'a', 'an', 'at', 'and', 'by', 'be', 'we'])
  
  def __init__(self, mt_root1, match_tree1, mt_root2, match_tree2, num_cands, dicts):
    self.match_tree1 = match_tree1
    self.match_tree2 = match_tree2
    self.dicts = dicts
    self.num_cands = num_cands
    
    self.empty_cell1 = MatchCell(match_tree1[0].size)
    self.empty_cell2 = MatchCell(match_tree2[0].size)
    
    self.score_matrix = np.empty((len(match_tree1)+1, len(match_tree2)+1))
    self.score_matrix[:] = np.inf
    self.path_matrix = [[('_', 0) for _ in xrange(len(match_tree2)+1)] for _ in xrange(len(match_tree1)+1)]
    for d in dicts:
      assert isinstance(d, set)

    self.mt_root1 = mt_root1
    self.mt_root2 = mt_root2

    # 0 is implicitly root of a match tree
    self._h(self.mt_root1, self.mt_root2, forbidden=set())
    
  def get_match_cell1(self, mt_node1):
    if mt_node1 == 0:
      return self.empty_cell1
    else:
      return self.match_tree1[mt_node1 - 1]
    
  def get_match_cell2(self, mt_node2):
    if mt_node2 == 0:
      return self.empty_cell2
    else:
      return self.match_tree2[mt_node2 - 1]
    
  def _match_score(self, mt_node1, mt_node2):
    mc1 = self.get_match_cell1(mt_node1)
    mc2 = self.get_match_cell2(mt_node2)

    sum_score = 0
    match_type = ''
    for i in xrange(len(mc1.words)):
      for j in xrange(len(mc2.words)):
        if mc1.words[i] is None and mc2.words[j] is None:
          match_type += '[gaps%d,%d];' % (i, j)
          continue
        if mc1.words[i] is None and mc2.words[j] is not None:
          sum_score += self.skip_score
          match_type += '[gap1%d,%d];' % (i, j)
          continue
        if mc1.words[i] is not None and mc2.words[j] is None:
          sum_score += self.skip_score
          match_type += '[gap2%d,%d];' % (i, j)
          continue
        broken = False
        for k in xrange(self.num_cands):
          if mc1.cands[i] == k and mc2.cands[j] == k:
            sum_score += self.cand_match_score
            match_type += '[cand%d,%d_%d];' % (i, j, k)
            broken = True 
            break
        if broken:
          continue
        if mc1.pos_tags[i] == mc2.pos_tags[j] \
            and mc1.lemmas[i] in self.short_words and mc2.lemmas[i] in self.short_words:
          match_type += '[short_word%d,%d]' % (i, j)
          continue
        if mc1.pos_tags[i] == mc2.pos_tags[j] and mc1.words[i] == mc2.words[j]:
          match_type += '[word%d,%d];' % (i, j) 
          sum_score += self.word_match_score
          continue
        if mc1.pos_tags[i] == mc2.pos_tags[j] and mc1.lemmas[i] == mc2.lemmas[j]:
          match_type += '[lemma%d,%d];' % (i, j) 
          sum_score += self.lemma_match_score
          continue
        if self.in_dicts(mc1.words[i], mc2.words[j], self.dicts):
          match_type += '[word_dict%d,%d];' % (i, j) 
          sum_score += self.dict_match_score
          continue
        if self.in_dicts(mc1.lemmas[i], mc2.lemmas[j], self.dicts):
          match_type += '[lemma_dict%d,%d];' % (i, j) 
          sum_score += self.dict_match_score
          continue
        if mc1.pos_tags[i] == mc2.pos_tags[j]:
          match_type += '[pos_tags%d,%d];' % (i, j) 
          sum_score += self.pos_tag_match_score
          continue
        match_type += '[mis%d,%d];' % (i, j) 
        sum_score += self.mismatch_score
    return sum_score, match_type + '_match'
  
  def _balance_lists(self, lists1, lists2):
    fake_guy_number = 0
    while len(lists1) < len(lists2):
      new_guy = 'fake_' + str(fake_guy_number)
      fake_guy_number += 1
      lists1[new_guy] = []
      for girl in lists2:
        lists1[new_guy].append((0, girl))
        lists2[girl].append((-1000, new_guy))
  
  def _sort_lists(self, lists):
    for guy in lists:
      sorted_list = sorted(lists[guy])[::-1] # sort in reverse score order
      lists[guy] = sorted_list
  
  def _stable_marriage(self, men_pref_lists, women_pref_lists):
    self._balance_lists(men_pref_lists, women_pref_lists)
    self._balance_lists(women_pref_lists, men_pref_lists)
    assert len(women_pref_lists) == len(men_pref_lists)
    self._sort_lists(men_pref_lists)
    self._sort_lists(women_pref_lists)
    proposal_order = copy.deepcopy(men_pref_lists)
    unmatched_guys = set([guy for guy in men_pref_lists])
    matching = {}
    while unmatched_guys:
      guy = iter(unmatched_guys).next()
      girl = proposal_order[guy][0][1]
      proposal_order[guy] = proposal_order[guy][1:]
      if girl not in matching:
        unmatched_guys -= set([guy])
        matching[girl] = guy
      else:
        current_guy = matching[girl]
        prefer_new_guy = None
        for (_, m) in women_pref_lists[girl]:
          if m == current_guy:
            prefer_new_guy = False
            break
          if m == guy:
            prefer_new_guy = True
            break
        assert prefer_new_guy is not None, (current_guy, guy, women_pref_lists[girl])
        if prefer_new_guy:
          unmatched_guys.add(current_guy)
          unmatched_guys -= set([guy])
          matching[girl] = guy
        else:
          pass
  
    rv = []
    assert len(matching) == len(women_pref_lists)
    matched_guys = set()
    for girl in matching:
      guy = matching[girl]
      assert guy not in matched_guys, (guy, matched_guys)
      matched_guys.add(guy)
      if isinstance(guy, int) and isinstance(girl, int):
        rv.append((guy, girl))
      elif isinstance(guy, int) and not isinstance(girl, int):
        rv.append((guy, None))
      elif not isinstance(guy, int) and isinstance(girl, int):
        rv.append((None, girl))
      else:
        assert False
        
    return rv
  
  def _match(self, mt_node1, mt_node2, forbidden):
    if mt_node1 == 0 and mt_node2 == 0:
      return 0, 'end', []
    if mt_node1 == 0 and mt_node2 != 0:
      return -1000, 'assert_false', []
    if mt_node1 != 0 and mt_node2 == 0:
      return -1000, 'assert_false', []
  
    mc1 = self.get_match_cell1(mt_node1)
    c1 = set(mc1.children)
    assert mt_node1 not in c1, (mt_node1, c1)
    mc2 = self.get_match_cell2(mt_node2)
    c2 = set(mc2.children)
    assert mt_node2 not in c2, (mt_node2, c2)
  
    men_pref_lists = {}
    women_pref_lists = {}
    for i in c1:
      men_pref_lists[i] = []
    for j in c2:
      women_pref_lists[j] = []
    for i in c1:
      for j in c2:
        self._h(i, j, forbidden)
        men_pref_lists[i].append((self.score_matrix[i, j], j))
        women_pref_lists[j].append((self.score_matrix[i, j], i))
    outgoing = self._stable_marriage(men_pref_lists, women_pref_lists)
    sum_score = 0
    for (i,j) in outgoing:
      # assert False, 'TODO test this! should we use the skip score for unassigned branches?'
      if i is not None and j is not None:
        sum_score += self.score_matrix[i, j]
      elif i is not None or j is not None:
        sum_score += self.skip_score
      else:
        assert False, (i, j)
    
    direct_match_score, match_type = self._match_score(mt_node1, mt_node2)
    assert len([a[0] for a in outgoing if a[0] is not None]) == len(set([a[0] for a in outgoing if a[0] is not None]))
    assert len([a[1] for a in outgoing if a[1] is not None]) == len(set([a[1] for a in outgoing if a[1] is not None]))
    assert len(outgoing) >= min(len(mc1.children), len(mc2.children))
    # assert len(outgoing) >= len(mc2.children)
    for o1, o2 in outgoing:
      assert mt_node1 != o1, (mt_node1, o1, match_type, mc1.children)
      assert mt_node2 != o2, (mt_node2, o2, match_type, mc2.children)

    return direct_match_score + sum_score, match_type, outgoing
  
  def _skip1(self, mt_node1, mt_node2, forbidden):
    if mt_node1 == 0:
      return -1000, 'assert_false', []
    score_list = []
    mc1 = self.get_match_cell1(mt_node1)
  
    for i in mc1.children:
      assert i != mt_node1
      self._h(i, mt_node2, forbidden)
      score_list.append((self.score_matrix[i, mt_node2], i))
    score_list = sorted(score_list)[::-1]
    
    mc2 = self.get_match_cell2(mt_node2)
    sum_score = 0
    skip_type = ''
    for j, word in enumerate(mc2.words):
      if word is not None:
        skip_type += '[skip%d]' % j
        sum_score += self.skip_score
      else:
        skip_type += '[zero%d]' % j

    assert score_list[0][1] != mt_node1, str((score_list[0][1], mt_node1))
    return sum_score + score_list[0][0], skip_type + '_skip1', [(score_list[0][1], mt_node2)]
  
  def _skip2(self, mt_node1, mt_node2, forbidden):
    if mt_node2 == 0:
      return -1000, 'assert_false', []
    score_list = []
    mc2 = self.get_match_cell2(mt_node2)
  
    for j in mc2.children:
      print >>sys.stderr, "%d -> %s" % (mt_node2, str(mc2.children))
      assert j != mt_node2
      print >>sys.stderr, j
      self._h(mt_node1, j, forbidden)
      score_list.append((self.score_matrix[mt_node1, j], j))
    score_list = sorted(score_list)[::-1]
    
    mc1 = self.get_match_cell1(mt_node1)
    sum_score = 0
    skip_type = ''
    for i, word in enumerate(mc1.words):
      if word is not None:
        skip_type += '[skip%d]' % i
        sum_score += self.skip_score
      else:
        skip_type += '[zero%d]' % i
    
    assert score_list[0][1] != mt_node2, str((mt_node2, score_list[0][1]))
    return sum_score + score_list[0][0], skip_type + '_skip2', [(mt_node1, score_list[0][1])]
  
  def _h(self, mt_node1, mt_node2, forbidden):
    forbidden = forbidden.copy()
    forbidden.add((mt_node1, mt_node2))
    print >>sys.stderr, (mt_node1, mt_node2)
    if self.score_matrix[mt_node1, mt_node2] != np.inf:
      return self.score_matrix[mt_node1, mt_node2]
  
    m, match_type, cont_match = self._match(mt_node1, mt_node2, forbidden)
    assert mt_node1 not in [c[0] for c in cont_match]
    assert mt_node2 not in [c[1] for c in cont_match]
    l1, skip_type1, cont_skip1 = self._skip1(mt_node1, mt_node2, forbidden)
    assert (mt_node1, mt_node2) not in cont_skip1, (mt_node1, mt_node2, cont_skip1)
    l2, skip_type2, cont_skip2 = self._skip2(mt_node1, mt_node2, forbidden)
    assert (mt_node1, mt_node2) not in cont_skip2, (mt_node1, mt_node2, cont_skip2)
    
    score = max([m, l1, l2])
    
    self.score_matrix[mt_node1, mt_node2] = score
    if score == m:
      self.path_matrix[mt_node1][mt_node2] = match_type, cont_match
    elif score == l1:
      self.path_matrix[mt_node1][mt_node2] = skip_type1, cont_skip1
    elif score == l2:
      self.path_matrix[mt_node1][mt_node2] = skip_type2, cont_skip2
    else:
      assert False
    
    for (o1, o2) in self.path_matrix[mt_node1][mt_node2][1]:
      assert (o1, o2) not in forbidden
      
  def print_match_path(self, stream=sys.stdout, mt_node1=None, mt_node2=None, indent=0):
    if mt_node1 == None:
      mt_node1 = self.mt_root1
    if mt_node2 == None:
      mt_node2 = self.mt_root2
    mc1 = self.get_match_cell1(mt_node1)
    mc2 = self.get_match_cell2(mt_node2)
    
    instr, succ = self.path_matrix[mt_node1][mt_node2]
    if mt_node1 >= 1:
      mt_words1 = mc1.words
    else:
      mt_words1 = ['.'] * mc1.size
    if mt_node2 >= 1:
      mt_words2 = mc2.words
    else:
      mt_words2 = '.' * mc2.size
      
    if instr.endswith('match'):
      print >>stream, " " * indent + "%d,%d: %s: %s (%d)" % (mt_node1, mt_node2, instr, str(mt_words1 + mt_words2), self.score_matrix[mt_node1, mt_node2])
    elif instr.endswith('skip1'):
      print >>stream, " " * indent + "%d,%d: %s: %s (%d)" % (mt_node1, mt_node2, instr, str(mt_words1), self.score_matrix[mt_node1, mt_node2])
    elif instr.endswith('skip2'):
      print >>stream, " " * indent + "%d,%d: %s: %s (%d)" % (mt_node1, mt_node2, instr, str(mt_words2), self.score_matrix[mt_node1, mt_node2])
    elif instr == 'end':
      pass
    else:
      assert False, instr
    for o1, o2 in succ:
      assert (o1, o2) != (mt_node1, mt_node2), str(succ)
      self.print_match_path(stream, o1, o2, indent+4)
  
  def get_match_tree(self, match_tree=None, folded=None, node1=None, node2=None, forbidden=None):
    if node1 == None:
      node1 = self.mt_root1
    if node2 == None:
      node2 = self.mt_root2
    
    if folded is not None and (node1, node2) in folded:
      if folded[(node1, node2)] == 0:
        return 0, None
      else:
        return folded[(node1, node2)], match_tree[folded[(node1, node2)] - 1]
  
    mc1 = self.get_match_cell1(node1)
    mc2 = self.get_match_cell2(node2)
    size1 = mc1.size
    size2 = mc2.size
    
    if match_tree is None:
      match_tree = []
    if folded is None:
      assert len(match_tree) == 0
      folded = {}
      folded[(0, 0)] = 0

    mc = MatchCell(size1 + size2)
    mc.cands[0:size1] = mc1.cands
    mc.cands[size1:size1+size2] = mc2.cands
    mc.pos_tags[0:size1] = mc1.pos_tags
    mc.pos_tags[size1:size1+size2] = mc2.pos_tags
    mc.words[0:size1] = mc1.words
    mc.words[size1:size1+size2] = mc2.words
    mc.lemmas[0:size1] = mc1.lemmas
    mc.lemmas[size1:size1+size2] = mc2.lemmas
    
    instr, succ = self.path_matrix[node1][node2]
    mc.match_type = instr
    match_tree.append(mc)
    index = len(match_tree)
    folded[(node1, node2)] = index
    
    if forbidden is  None:
      forbidden = []
    forbidden = [i for i in forbidden]
    forbidden.append((node1, node2))

    for o1, o2 in succ:
      if (o1, o2) in forbidden:
        for i in xrange(0, len(self.path_matrix)):
          print >>sys.stderr, '  '.join([str(succ) for (instr, succ) in self.path_matrix[i]])
        
        for i, mc in enumerate(self.match_tree1):
          print >>sys.stderr, str(i+1) + ": " + str(mc)
        for i, mc in enumerate(self.match_tree2):
          print >>sys.stderr, str(i+1) + ": " + str(mc)
      assert (o1, o2) not in forbidden, (o1, o2, forbidden)
      child_root, _ = self.get_match_tree(match_tree, folded, o1, o2, forbidden)
      assert child_root >= 0
      mc.children.append(child_root)
    assert mc.children
    return index, match_tree
  
  def print_matched_lemmas(self, stream=sys.stdout, node1=None, node2=None, folded=None):
    if node1 is None:
      node1 = self.mt_root1
    if node2 is None:
      node2 = self.mt_root2
    if folded is None:
      folded = set()
    
    if (node1, node2) in folded or node1 == 0 or node2 == 0:
      return
    folded.add((node1, node2))
    
    mc1 = self.get_match_cell1(node1)
    mc2 = self.get_match_cell2(node2)
    instr, succ = self.path_matrix[node1][node2]
    if instr.endswith('_match'):
      print >>stream, "%s\t%s" % ('\t'.join(mc1.lemmas), '\t'.join(mc2.lemmas))
    
    for (o1, o2) in succ:
      self.print_matched_lemmas(stream, o1, o2, folded)
  
  def overall_score(self):
    return self.score_matrix[self.mt_root1, self.mt_root2]
  
  def rescore(self, unscore_list, folded=None, node1=None, node2=None):
    if node1 is None:
      node1 = self.mt_root1
    if node2 is None:
      node2 = self.mt_root2
    if folded is None:
      folded = set()
    
    if (node1, node2) in folded or node1 == 0 or node2 == 0:
      return 0
    folded.add((node1, node2))
    
    mc1 = self.get_match_cell1(node1)
    mc2 = self.get_match_cell2(node2)
    lemmas1 = mc1.lemmas
    lemmas2 = mc2.lemmas
    instr, succ = self.path_matrix[node1][node2]
    rv = 0
    if instr.endswith('_match'):
      for s1, s2, penalty in unscore_list:
        for l1 in s1:
          for l2 in s2:
            if l1 in lemmas1 and l2 in lemmas2:
              rv += penalty
    
    for (o1, o2) in succ:
      rv += self.rescore(unscore_list, folded, o1, o2)
    
    return rv
      