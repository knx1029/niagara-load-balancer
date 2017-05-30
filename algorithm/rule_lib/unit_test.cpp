#include "unit_test.h"

using namespace std;


bool UnitTest::check_mvip(const MVipInput& p_input,
			  const MVipOutput& p_output,
			  double** &p_values) {
  if (!p_input.m_mvip || !p_output.m_mrules) {
    return false;
  }
  
  const MVip& mvip = *(p_input.m_mvip);
  const MRuleSet& mrules = *(p_output.m_mrules);
  const RuleSet* default_rules = p_input.m_default_rules;  
  
  for (MVip::const_iterator itr = mvip.begin(); itr != mvip.end(); ++itr) {
    MRuleSet::const_iterator jtr = itr - mvip.begin() + mrules.begin();
    if (itr->m_id != (*jtr)->m_id) {
      return false;
    }
    if (!itr->m_vip || !itr->m_eval) {
      return false;
    }
	
    const Vip& vip = *(itr->m_vip);
    const BitEval& eval = *(itr->m_eval);
    const RuleSet& vip_rules = *((*jtr)->m_rules);
    RuleSet rules;
    // construct rules
    if (default_rules) {
      rules.insert(rules.begin(), default_rules->begin(), default_rules->end());
    }
    rules.insert(rules.end(), vip_rules.begin(), vip_rules.end());

    for (Vip::const_iterator ktr = vip.begin(); ktr != vip.end(); ++ktr) {
      double value;
      if (!compute_value(rules, eval, ktr->m_id, &value)) {
	return false;
      }
      p_values[itr - mvip.begin()][ktr - vip.begin()] = value;
    }
  }
  return true;
}

bool UnitTest::check_svip(const SVipInput& p_input,
                          const SVipOutput& p_output) {
  if (p_input.m_vip == NULL || p_output.m_values == NULL || 
      p_input.m_eval == NULL || p_output.m_rules == NULL) {
    return false;
  }
  const Vip &input = *p_input.m_vip;
  const BitEval &eval = *p_input.m_eval;
  const Vip &output = *p_output.m_values;
  const RuleSet &rules = *p_output.m_rules;

  if (input.size() != output.size()) {
    return false;
  }
  if (p_input.m_default_rules) {
    const RuleSet &default_rules = *p_input.m_default_rules;
    for (RuleSet::const_iterator itr = default_rules.begin();
	 itr != default_rules.end(); ++itr) {
      RuleSet::const_iterator jtr = rules.begin() + (itr - default_rules.begin());
      if (*itr != *jtr) {
	    return false;
      }
    }
  }

  
  for (Vip::const_iterator itr = input.begin(); itr != input.end(); ++itr) {

    Vip::const_iterator jtr = output.begin() + (itr - input.begin());
    if (itr->m_id != jtr->m_id) {
      return false;
    }
    if (double_cmp(fabs(itr->m_value - jtr->m_value) - p_input.m_eps) > 0) {
      return false;
    }
	
    double value;
    compute_value(rules, eval, jtr->m_id, &value);
    if (double_cmp(jtr->m_value - value)) {
      cout << jtr->m_id  << " " << jtr->m_value << " " << value << endl;
      return false;
    }
  }
  return true; 
}

bool UnitTest::compute_value(const RuleSet& p_rule,
                             const BitEval& p_eval,
                             int p_action_id,
			     double* p_value) {
  
  double value = 0.0;
  for (RuleSet::const_reverse_iterator tr1 = p_rule.rbegin();
       tr1 != p_rule.rend(); ++tr1) {
    if (tr1->m_action == p_action_id) {
	  value += p_eval.value(tr1->m_pattern);
	  continue;
    }
    for (RuleSet::const_reverse_iterator tr2 = tr1 + 1;
	 tr2 != p_rule.rend(); ++tr2) {
      if (pattern_contains(tr2->m_pattern, tr1->m_pattern)) {
	if (tr2->m_action == p_action_id) {
	  value -= p_eval.value(tr1->m_pattern);
	}
	break;
      }
    }
  }
  (*p_value) = value;
  return true;
}


void UnitTest::compute_imbalance(double** const & p_weights,
				 double* const & p_frac,
				 double** const & p_values,
				 int p_nweights,
				 int p_nvips,
				 double* p_imb) {
  double imb = 0.0;
  for (int i = 0; i < p_nvips; ++i) {
    for (int j = 0; j < p_nweights; ++j) {
      imb += fabs(p_weights[i][j] - p_values[i][j]) * p_frac[i];
    }
  }
  imb /= 2;
  (*p_imb) = imb;
}


void UnitTest::compute_group_imbalance(double** const & p_weights,
				       double* const & p_frac,
				       double** const & p_values,
				       int* const & p_group_id,
				       int p_nweights,
				       int p_nvips,
				       int p_ngroups,
				       double* p_imb) {
  double imb = 0.0;
  for (int i = 0; i < p_nvips; ++i) {
    int gid = p_group_id[i];
    for (int j = 0; j < p_nweights; ++j) {
      imb += fabs(p_weights[i][j] - p_values[gid][j]) * p_frac[i];
    }
  }
  imb /= 2;
  (*p_imb) = imb;
}
