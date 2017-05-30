#include<algorithm>

#include "mvip_solver.h"

using namespace std;


bool operator<(const ItrItem& i1, const ItrItem& i2) {
  return i1.m_value < i2.m_value;
}

void print_svip_result(const SVipResult& p_result) {
  for (SVipResult::const_iterator itr = p_result.begin();
       itr != p_result.end(); ++itr) {
    (*itr)->print();
    cout << endl;
  }
}

void print_mvip(const MVip& p_svip) {
  for (MVip::const_iterator itr = p_svip.begin();
       itr != p_svip.end(); ++itr) {
    itr->print();
    cout << endl;
  }
}

void print_mrules(const MRuleSet& p_mrules) {
  for (MRuleSet::const_iterator itr = p_mrules.begin();
       itr != p_mrules.end(); ++itr) {
    (*itr)->print();
    cout << endl;
  }
}

void print_itr_heap(const ItrHeap& p_heap) {
  for (ItrHeap::const_iterator itr = p_heap.begin();
       itr != p_heap.end(); ++itr) {
    itr->print();
    cout << endl;
  }
}

// init
bool MVipSolver::init(const MVip& p_mvip, 
                      const RuleSet* p_default_rules,
 	              double p_eps,
                      SVipResult** p_result) {
		  
  SVipResult* result = new SVipResult();
  SVipSolver svip_solver;

  SVipInput* input;
  SVipOutput* output;

  for (MVip::const_iterator itr = p_mvip.begin();
       itr != p_mvip.end(); ++itr) {

    input = new SVipInput(itr->m_vip, 
			  p_default_rules,
			  p_eps,
			  itr->m_eval);
    
    if (!svip_solver.solve(*input, &output) ||
        !output ||
	!output->m_rules ||
	!output->m_imb ||
	!output->m_values) {
      // clear everything
      for (SVipResult::iterator jtr = result->begin();
	   jtr != result->end(); ++jtr) {
	delete (*jtr);
      }
      result->clear();

      if (output) {
        delete output;
      }

      delete input;
      return false;
    }
    /*
    cout << "vip_id:" << itr->m_id << endl;
    cout << "result\n";
    output->print();
    cout << "-----------------\n";
    */
    
    result->push_back(output);
    delete input;
  }

  (*p_result) = result;
  return true;
}

// create heap, get the next candidate rule from each vip
bool MVipSolver::create_heap(const MVip& p_mvips,
                             const SVipResult& p_svip_result,
                             const RuleSet* p_default_rules,
                             MRuleSet** p_mrules,
                             ItrHeap** p_heap,
                             int* p_num_rules) {
  MRuleSet *mrules = new MRuleSet();

  int start_index = 0;
  int num_rules = 0;
  ItrHeap* heap = new ItrHeap();
  if (p_default_rules == NULL) {
    for (vector<SVipOutput*>::const_iterator itr = p_svip_result.begin();
	 itr != p_svip_result.end(); ++itr) {

      const MVip::const_iterator jtr = (itr - p_svip_result.begin()) + p_mvips.begin();
      const RuleSet &full_rules = *((*itr)->m_rules);
      const DeltaImb &delta_imb = *((*itr)->m_imb);
      // create the new rule block
      RuleSet* rules = new RuleSet();
      rules->push_back(full_rules[start_index]);
      ++num_rules;
      mrules->push_back(new SRuleSet(rules, jtr->m_id));

      if (full_rules.size() > start_index + 1) {
	double imb = delta_imb[start_index + 1] * jtr->m_fraction;
	heap->push_back(ItrItem(jtr,
				full_rules.begin() + start_index + 1,
				imb));
      }
    }
  }
  else {
    start_index = p_default_rules->size();
    num_rules = p_default_rules->size();
    for (vector<SVipOutput*>::const_iterator itr = p_svip_result.begin();
	 itr != p_svip_result.end(); ++itr) {
      const MVip::const_iterator jtr = (itr - p_svip_result.begin()) + p_mvips.begin();
      const RuleSet &full_rules = *((*itr)->m_rules);
      const DeltaImb &delta_imb = *((*itr)->m_imb);

      // create the new rule block
      RuleSet* rules = new RuleSet();
      mrules->push_back(new SRuleSet(rules, jtr->m_id));
      
      if (full_rules.size() > start_index) {
	double imb = delta_imb[start_index] * jtr->m_fraction;
	heap->push_back(ItrItem(jtr,
				full_rules.begin() + start_index,
				imb));
      }
    }
    RuleSet* default_rules = new RuleSet(*p_default_rules);
    mrules->push_back(new SRuleSet(default_rules, DEFAULT_RULE_ID));
  }
  make_heap(heap->begin(), heap->end());
  
  (*p_mrules) = mrules;
  (*p_heap) = heap;
  (*p_num_rules) = num_rules;
  return true;
}

bool MVipSolver::one_more_rule(const MVip& p_vips,
			       const SVipResult& p_results,
			       ItrHeap& p_heap,
                               MRuleSet& p_mrules) {
	
  if (!p_heap.size()) {

    return false;
  }
  // retrive two iterators
  ItrItem &item = p_heap.front();
  MVip::const_iterator vip_itr = item.m_vip_itr;
  RuleSet::const_iterator rule_itr = item.m_rule_itr;

  // use vip_itr to get the related the selected rules
  // select the new rule
  int vip_index = item.m_vip_itr - p_vips.begin();
  MRuleSet::const_iterator ruleset_itr = p_mrules.begin() + vip_index;  
  (*ruleset_itr)->m_rules->push_back(*rule_itr);

  // use vip_itr to get the related svip result
  // add the next rule to heap
  SVipResult::const_iterator res_itr = p_results.begin() + vip_index;
  const RuleSet *svip_rules = (*res_itr)->m_rules;
  pop_heap(p_heap.begin(), p_heap.end());
  p_heap.pop_back();
  ++rule_itr;
  if (rule_itr != svip_rules->end()) {
    int rule_index = rule_itr - svip_rules->begin();
    DeltaImb::const_iterator imb_itr = (*res_itr)->m_imb->begin() + rule_index;
    double imb = (*imb_itr) * vip_itr->m_fraction;
    p_heap.push_back(ItrItem(vip_itr,
			     rule_itr,
			     imb));
    push_heap(p_heap.begin(), p_heap.end());
  }
  return true;
}

bool MVipSolver::solve(const MVipInput& p_input, MVipOutput ** p_output) {
  if (p_input.m_mvip == NULL) {
    return false;
  }
  
  const MVip &mvip = *(p_input.m_mvip);
  const RuleSet *default_rules = p_input.m_default_rules;
  double eps = p_input.m_eps;

  //  cout << "init\n";
  SVipResult* result;
  if (!init(mvip, default_rules, eps, &result)) {
    return false;
  }

  //  cout << "create\n";
  MRuleSet* mrules = NULL;
  ItrHeap* heap = NULL;
  int num_rules;
  if (!create_heap(mvip,
                   *result,
		   default_rules,
		   &mrules,
		   &heap,
		   &num_rules)) {
    return false;			   
  }

  if (num_rules > p_input.m_max_num_rules) {
    return false;
  }

  //  cout << "one more rule\n";
  while (num_rules < p_input.m_max_num_rules && heap->size()) {
    if (!one_more_rule(mvip,
		       *result,
		       *heap,
		       *mrules)) {
      return false;
    }
    num_rules += 1;
  }

  heap->clear();
  delete heap;
  heap = NULL;
  
  for (SVipResult::iterator itr = result->begin();
       itr != result->end(); ++itr) {
    delete (*itr);
  }
  result->clear();
  delete result;
  result = NULL;

  MVipOutput* output = new MVipOutput(mrules, num_rules);
  (*p_output) = output;
  m_mrules = mrules;
  m_num_rules = num_rules;
  
  return true;
}



bool MVipSolver::start(const MVipInput& p_input){
  
  if (p_input.m_mvip == NULL) {
    return false;
  }
  
  const MVip &mvip = *(p_input.m_mvip);
  const RuleSet *default_rules = p_input.m_default_rules;
  double eps = p_input.m_eps;

  //  cout << "init\n";
  SVipResult* result;
  if (!init(mvip, default_rules, eps, &result)) {
    return false;
  }

  //  cout << "create\n";
  MRuleSet* mrules = NULL;
  ItrHeap* heap = NULL;
  int num_rules;
  if (!create_heap(mvip,
                   *result,
		   default_rules,
		   &mrules,
		   &heap,
		   &num_rules)) {
    return false;			   
  }

  if (num_rules > p_input.m_max_num_rules) {
    return false;
  }

  m_mrules = mrules;
  m_heap = heap;
  m_num_rules = num_rules;
  m_result = result;

}

bool MVipSolver::get_more_rules(const MVipInput& p_input) {
  const MVip &mvip = *(p_input.m_mvip);
  //  cout << "one more rule\n";


  SVipResult* result = m_result;
  MRuleSet* mrules = m_mrules;
  ItrHeap* heap = m_heap;
  int num_rules = m_num_rules;
  while (num_rules < p_input.m_max_num_rules && heap->size()) {
    if (!one_more_rule(mvip,
		       *result,
		       *heap,
		       *mrules)) {
      return false;
    }
    num_rules += 1;
  }
  
  m_mrules = mrules;
  m_heap = heap;
  m_num_rules = num_rules;
  m_result = result;
}

bool MVipSolver::get_output(MVipOutput** p_output) {
  if (!m_mrules || m_num_rules == 0) {
    return false;
  }
  MVipOutput* output = new MVipOutput(m_mrules, m_num_rules);
  (*p_output) = output;
  return true;

}


void MVipSolver::cleanup() {

  if (m_heap) {
    m_heap->clear();
    delete m_heap;
    m_heap = NULL;
  }

  if (m_result) {
    for (SVipResult::iterator itr = m_result->begin();
	 itr != m_result->end(); ++itr) {
      delete (*itr);
    }
    m_result->clear();
    delete m_result;
    m_result = NULL;
  }
  
  if (m_mrules) {
    for (MRuleSet::iterator itr = m_mrules->begin();
	 itr != m_mrules->end(); ++itr) {
      delete (*itr);
    }
    m_mrules->clear();
    delete m_mrules;
    m_mrules = NULL;
  }

  m_num_rules = 0;
}
