#include<string>
#include<vector>
#include<cmath>
#include<algorithm>

#include "utils.h"
#include "svip_solver.h"

using namespace std;

double delta_imbalance(double p_a, double p_b, double p_x) {
  return min(p_a, p_x) + min(p_b, p_x) - p_x;
}

bool operator==(const Rule& r1, const Rule& r2) {
  return r1.m_pattern == r2.m_pattern && r1.m_action == r2.m_action;
}

bool operator!=(const Rule& r1, const Rule& r2) {
  return r1.m_pattern != r2.m_pattern && r1.m_action != r2.m_action;
}

bool operator<(const StringItem& i1, const StringItem& i2) {
  return i1.m_value < i2.m_value;
}

void print_vip(const Vip& p_vip) {
  for (Vip::const_iterator itr = p_vip.begin(); itr != p_vip.end(); ++itr) {
    itr->print();
  }
}

void print_rules(const RuleSet& p_rules) {
  for (RuleSet::const_iterator itr = p_rules.begin(); itr != p_rules.end(); ++itr) {
    itr->print();
  }
}

void print_string_heap(const StringHeap& p_heap) {
 for (StringHeap::const_iterator itr = p_heap.begin(); itr != p_heap.end(); ++itr) {
    itr->print();
  }
}

void print_delta_imb(const DeltaImb& p_imb) {
  for (DeltaImb::const_iterator itr = p_imb.begin(); itr != p_imb.end(); ++itr) {
    cout << (*itr) << " ";
  }
  cout << endl;
}

void SVipInput::print() const {
  if (m_vip) {
    print_vip(*m_vip);
  }
  if (m_default_rules) {
    print_rules(*m_default_rules);
  }
  cout << m_eps << endl;
}

void SVipOutput::print() const {
  if (m_values) {
    print_vip(*m_values);
  }
  if (m_rules) {
    print_rules(*m_rules);
  }
  if (m_imb) {
    print_delta_imb(*m_imb);
  }
}


bool SVipSolver::update_heap(StringHeap& p_heap,
                             double p_a,
			     double p_b,
			     const BitEval& p_eval,
			     double* p_fall) {
  StringHeap temp;
  double last_imb = -1;
  double x, y = 0.0, z = 0.0;
  double fall_x, fall_y;
  
  while (p_heap.size() > 0) {
    pop_heap(p_heap.begin(), p_heap.end());
    StringItem item = p_heap.back();
    p_heap.pop_back();
    temp.push_back(item);
    
    x = item.m_value;
    fall_x = delta_imbalance(p_a, p_b, x);
    
    if (p_heap.size() > 0) {
      y = p_heap.front().m_value;
    }
    else {
      y = -1;
    }
    z = max(z, max(p_eval.value(pattern_zero(item.m_item)),
                   p_eval.value(pattern_one(item.m_item))));
    y = max(z, y);
    
    if (double_cmp(x - y) == 0) {
      continue;
    }
    
    fall_y = delta_imbalance(p_a, p_b, y);
    if (double_cmp(fall_y - fall_x) <= 0 && double_cmp(y - x) <= 0) {
      while(temp.size() > 0) {
	p_heap.push_back(temp.back());
	push_heap(p_heap.begin(), p_heap.end());
	temp.pop_back();
      }
      break;
    }
    else {
      StringItem item;
      string pattern;
      double value;
      while(temp.size() > 0) {
	item = temp.back();
	temp.pop_back();
	// add "0"+pattern
	pattern = pattern_zero(item.m_item);
	value = p_eval.value(pattern);
	p_heap.push_back(StringItem(pattern, value));
	push_heap(p_heap.begin(), p_heap.end());
	// add "1"+pattern
	pattern = pattern_one(item.m_item);
	value = p_eval.value(pattern);
	p_heap.push_back(StringItem(pattern, value));
	push_heap(p_heap.begin(), p_heap.end());
      }
      z = 0.0;
    }
  }
  (*p_fall) = fall_x;
  return true;
}

bool SVipSolver::one_more_rule(const SVipInput& p_input,
                               Vip& p_values,
                               StringHeap* const& p_heaps,
			       RuleSet& p_rules,
			       DeltaImb& p_imb) {
  const Vip* weights = p_input.m_vip;
  const BitEval* eval = p_input.m_eval;
  
  // find max weight - value
  double max_pos_error = 0.0;
  Vip::iterator best_pos_itr = p_values.begin();
  for (Vip::iterator itr = p_values.begin(); itr != p_values.end(); ++itr) {
    Vip::const_iterator jtr = weights->begin() + (itr - p_values.begin());
    double error = jtr->m_value - itr->m_value;
    if (error > max_pos_error) {
      max_pos_error = error;
      best_pos_itr = itr;
    }
  }
  
  // find max imbalance reduction from (value > weight)
  double best_fall = 0.0;
  Vip::iterator best_neg_itr = p_values.begin();
  for (Vip::iterator itr = p_values.begin(); itr != p_values.end(); ++itr) {
    int index = (itr - p_values.begin());
    Vip::const_iterator jtr = weights->begin() + index;
    double error = itr->m_value - jtr->m_value;
    double fall;
    if (error > 0) {
      update_heap(p_heaps[index], max_pos_error, error, *eval, &fall);
      if (fall > best_fall) {
	best_fall = fall;
	best_neg_itr = itr;
      }
    }
  }
  
  // generate a new rule
  int best_pos_idx = best_pos_itr - p_values.begin();
  int best_neg_idx = best_neg_itr - p_values.begin();

  // retrieve
  StringItem &best_item = p_heaps[best_neg_idx].front();
  // rule
  p_rules.push_back(Rule(best_item.m_item, best_pos_itr->m_id));
  p_imb.push_back(best_fall);
  // add  
  best_pos_itr->m_value += best_item.m_value;
  p_heaps[best_pos_idx].push_back(best_item);
  push_heap(p_heaps[best_pos_idx].begin(), p_heaps[best_pos_idx].end());
  // remove
  best_neg_itr->m_value -= best_item.m_value;
  pop_heap(p_heaps[best_neg_idx].begin(), p_heaps[best_neg_idx].end());
  p_heaps[best_neg_idx].pop_back();
  
  return true;
}

bool SVipSolver::solve(const SVipInput& p_input,
		       SVipOutput** p_output) {
  if (double_cmp(p_input.m_eps) <= 0) {
    return false;
  }
  
  const Vip* weights = p_input.m_vip;
  Vip* values;
  RuleSet* rules;
  StringHeap* heaps;
  DeltaImb* imb;
  int heap_size;
    
  if (!init_output(p_input, &rules, &values, &imb, &heaps, &heap_size)) {
    return false;
  }
//  for (int i = 0; i < 7; ++i) {
  while (!check_within_eps(*weights, *values, p_input.m_eps)) {
    // cout <<"~!~@!~!@~!@~!@~!@~!@\n";
    // print_vip(*values);
    // print_rules(*rules);
    if (!one_more_rule(p_input, *values, heaps, *rules, *imb)) {
      return false;
    }
  }

  delete [] heaps;

  SVipOutput* output = new SVipOutput(rules, values, imb);

  (*p_output) = output;
  return true;
}

bool SVipSolver::init_output(const SVipInput& p_input,
			     RuleSet** p_rules,
			     Vip** p_values,
			     DeltaImb** p_imb,
			     StringHeap** p_heaps,
			     int* p_heap_size)
{
  const Vip* weights = p_input.m_vip;
  const BitEval* eval = p_input.m_eval;
  RuleSet* rules = NULL;
  Vip* values = NULL;
  StringHeap* heaps = NULL;
  DeltaImb* imb = NULL;
  int heap_size = 0;
  
  if (!p_input.m_default_rules || p_input.m_default_rules->size() == 0) {
    rules = new RuleSet();      
    Vip::const_iterator pool = weights->begin();
    for (Vip::const_iterator itr = weights->begin(); 
	 itr != weights->end(); ++itr) {
      if (itr->m_value > pool->m_value) {
	    pool = itr;
      }
    }
    
    string root = get_root_pattern();
    rules->push_back(Rule(root, pool->m_id));
  }
  else {
    rules = new RuleSet(*p_input.m_default_rules);
  }

  imb = new DeltaImb();
  for (int i = 0; i < rules->size(); ++i) {
    imb->push_back(-1);
  }

  values = new Vip();
  heap_size = weights->size();
  heaps = new StringHeap[heap_size];
  for (Vip::const_iterator itr = weights->begin();
       itr != weights->end(); ++itr) {
    values->push_back(Weight(itr->m_id, 0));
  }

  for (RuleSet::iterator itr = rules->begin(); 
       itr != rules->end(); ++itr) {
    for (Vip::iterator jtr = values->begin();
	 jtr != values->end(); ++jtr) {
      if (jtr->m_id == itr->m_action) {
	double pattern_value = eval->value(itr->m_pattern);
	jtr->m_value += pattern_value; 
	heaps[jtr - values->begin()].push_back(StringItem(itr->m_pattern,
						   pattern_value));
      }
    }
  }

  for (int i = 0; i < heap_size; ++i) {
    if (heaps[i].size() > 0) {
      make_heap(heaps[i].begin(), heaps[i].end());
    }
  }

  (*p_rules) = rules;
  (*p_values) = values;
  (*p_heaps) = heaps;
  (*p_heap_size) = heap_size;
  (*p_imb) = imb;
  
  return true;
}

bool SVipSolver::check_within_eps(const Vip& p_input,
				  const Vip& p_output,
				  double p_eps) {
  if (p_input.size() != p_output.size()) {
    return false;
  }
  for (Vip::const_iterator itr = p_input.begin();
       itr != p_input.end(); ++itr) {
    Vip::const_iterator jtr = p_output.begin() + (itr - p_input.begin());
    if (itr->m_id != jtr->m_id) {
      return false;
    }
    if (double_cmp(fabs(itr->m_value - jtr->m_value) - p_eps) > 0) {
      return false;
    }
  }
  
  return true; 
}
