#ifndef __NG_MVIP_SOLVER__

#define __NG_MVIP_SOLVER__


#include<string>
#include<vector>
#include<cmath>
#include<iostream>

#include "utils.h"
#include "svip_solver.h"

using namespace std;


const int DEFAULT_RULE_ID = -1;

//SVip for MVip
struct SVip {
  Vip* m_vip;
  BitEval* m_eval;
  double m_fraction;
  int m_id;
  
  SVip(Vip* p_vip, BitEval* p_eval, double p_fraction, int p_id):
    m_vip(p_vip),
    m_eval(p_eval),
    m_fraction(p_fraction),
    m_id(p_id)
  {}

  ~SVip() {
    // do not remove input
  }
  
  void print() const {
    cout << m_id << " " << m_fraction << endl;
    if (m_vip) {
      print_vip(*m_vip);
    }
  }
};

struct SRuleSet {
  RuleSet* m_rules;
  int m_id;
   
  SRuleSet(RuleSet* p_rules, int p_id):
    m_rules(p_rules),
	m_id(p_id)
  {}

  ~SRuleSet() {
    if (m_rules) {
      delete m_rules;
    }
  }
  
  void print() const {
    cout << m_id << endl;
    if (m_rules) {
      print_rules(*m_rules);
    }
  }
};

typedef vector<SVipOutput*> SVipResult;

typedef vector<SVip> MVip;

typedef vector<SRuleSet*> MRuleSet;

struct ItrItem {
  MVip::const_iterator m_vip_itr;
  RuleSet::const_iterator m_rule_itr;
  double m_value;

  ItrItem(MVip::const_iterator p_vip_itr,
          RuleSet::const_iterator p_rule_itr, 
          double p_value):
    m_vip_itr(p_vip_itr),
	m_rule_itr(p_rule_itr),
    m_value(p_value)
  {}
  
  ItrItem() {}

  void print() const {
    cout << m_vip_itr->m_id << " " << m_value << endl;
    m_rule_itr->print();
  }
};

bool operator<(const ItrItem& i1, const ItrItem& i2);

typedef vector<ItrItem> ItrHeap;

void print_svip_result(const SVipResult& p_result);

void print_mvip(const MVip& p_svip);

void print_mrules(const MRuleSet& p_mrules);

void print_itr_heap(const ItrHeap& p_heap);


struct MVipInput {
  MVip* m_mvip;
  RuleSet* m_default_rules;  
  double m_eps;
  int m_max_num_rules;
  
  MVipInput(MVip *p_mvip,
            RuleSet* p_default_rules,
	    double p_eps,
	    int p_max_num_rules):
    m_mvip(p_mvip),
    m_default_rules(p_default_rules),
    m_eps(p_eps),
    m_max_num_rules(p_max_num_rules)
  {}

  ~MVipInput() { 
    // do not delete input
  }
  
  void print() const {
    cout << m_eps << " " << m_max_num_rules << endl;
    print_mvip(*m_mvip);
	if (m_default_rules) {
	  print_rules(*m_default_rules);
	}
  }
};

struct MVipOutput {
  MRuleSet* m_mrules;
  int m_num_rules;
  
  MVipOutput(MRuleSet* p_mrules, int p_num_rules):
    m_mrules(p_mrules),
    m_num_rules(p_num_rules)
  {}

  ~MVipOutput() {
    // do nothing
  }
  
  void print() const {
    cout << m_num_rules << endl;
    print_mrules(*m_mrules);
  }

};



class MVipSolver {

 public:

  MVipSolver() {
    m_result = NULL;
    m_mrules = NULL;
    m_heap = NULL;
    m_num_rules = 0;
  }

  ~MVipSolver() {
    cleanup();
  }

  bool solve(const MVipInput& p_input, MVipOutput** p_output);


  bool start(const MVipInput& p_input);

  bool get_more_rules(const MVipInput& p_input);

  bool get_output(MVipOutput** p_output);

  void cleanup();
  
 private:
  SVipResult* m_result;
  MRuleSet* m_mrules;
  ItrHeap* m_heap;
  int m_num_rules;
  
  bool init(const MVip& p_mvip, 
            const RuleSet* p_default_rules,
	    double p_eps,
            SVipResult** p_output);
			
  bool create_heap(const MVip& p_mvips,
                   const SVipResult& p_svip_result,
                   const RuleSet* p_default_rules,
                   MRuleSet** p_mrules,
                   ItrHeap** p_heap,
                   int* p_num_rules);


  bool one_more_rule(const MVip& p_vips,
		     const SVipResult& p_results,
		     ItrHeap& p_heap,
		     MRuleSet& p_mrules);

};


#endif

