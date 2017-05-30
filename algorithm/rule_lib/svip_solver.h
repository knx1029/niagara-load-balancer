#ifndef __NG_SVIP_SOLVER__

#define __NG_SVIP_SOLVER__


#include<string>
#include<vector>
#include<cmath>
#include<iostream>

#include "utils.h"
using namespace std;

struct Weight {
  int m_id;
  double m_value;

  Weight(int p_id, double p_value) : m_id(p_id),
				     m_value(p_value)
  {}
  
  void print() const {
    cout << m_id << "," << m_value << endl;
  }
};
  
struct Rule {
  string m_pattern;
  int m_action;

  Rule(string p_pattern, int p_action): m_pattern(p_pattern), 
					m_action(p_action)
  {}
  
  void print() const {
	cout << m_pattern << "," << m_action << endl;
  }
};

struct StringItem {
  string m_item;
  double m_value;

  StringItem(string p_item, double p_value):
    m_item(p_item),
    m_value(p_value)
  {}
  
  StringItem() {}
  
  void print() const {
    cout << m_item << "," << m_value << endl;
  }
};

bool operator<(const StringItem &i1, const StringItem &i2);

bool operator==(const Rule &r1, const Rule &r2);

bool operator!=(const Rule &r1, const Rule &r2);

typedef vector<Weight> Vip;
typedef vector<Rule> RuleSet;
typedef vector<double> DeltaImb;
typedef vector<StringItem> StringHeap;

bool operator<(const StringItem &i1, const StringItem &i2);

class BitEval {
 public:
  virtual double value(string p_pattern) const = 0;
};

struct SVipInput {
  const Vip* m_vip;
  const RuleSet* m_default_rules;
  double m_eps;
  const BitEval* m_eval;
  
  SVipInput(const Vip* p_vip,
            const RuleSet* p_default_rules,
            double p_eps,
			const BitEval* p_eval):
    m_vip(p_vip),
	m_default_rules(p_default_rules),
	m_eps(p_eps),
	m_eval(p_eval)
	{}
	
  ~SVipInput() {
    // do not remove input
  }
  
  void print() const;
};

struct SVipOutput {
  const RuleSet* m_rules;
  const Vip* m_values;
  const DeltaImb* m_imb;
  
  SVipOutput(RuleSet *p_rules, Vip* p_values, DeltaImb* p_imb):
    m_rules(p_rules), m_values(p_values), m_imb(p_imb)
  {}
  
  ~SVipOutput() {
    if (m_rules) {
      delete m_rules;
    }
    if (m_values) {
      delete m_values;
    }
    
    if (m_imb) {
      delete m_imb;
    }
  }
  
  void print() const;
};

void print_vip(const Vip& p_vip);

void print_rules(const RuleSet& p_rules);

void print_string_heap(const StringHeap& p_heap);

void print_delta_imb(const DeltaImb& p_imb);

class SVipSolver {

 public:
  bool solve(const SVipInput& p_input, SVipOutput** p_output);

 private:
  bool init_output(const SVipInput& p_input,
		   RuleSet** p_rules,
		   Vip** p_values,
		   DeltaImb** p_imb,
		   StringHeap** p_heaps,
		   int* p_heap_size);

  bool update_heap(StringHeap& p_heap, 
                   double p_a,
		   double p_b,
		   const BitEval &p_eval,
		   double* p_fall);
  
  bool one_more_rule(const SVipInput& p_input,
                     Vip& p_values,
                     StringHeap* const& p_heaps,
		     RuleSet& p_rules,
		     DeltaImb& p_imb);
								 
  static bool check_within_eps(const Vip& p_input,
			       const Vip& p_output,
			       double p_eps);
};


class BitEvalP : public BitEval {
 private:
  double m_zero;
  double m_one;

 public:
  BitEvalP(double p_zero) {
    m_zero = p_zero;
	m_one = 1.0 - p_zero;
  }
   
  virtual double value(string p_pattern) const {
	double v = 1.0;
    for (int i = 0; i < p_pattern.size(); ++i) {
	  if (p_pattern[i] == '0') {
	    v *= m_zero;
	  }
	  else if (p_pattern[i] == '1') {
	    v *= m_one;
	  }
    }
	return v;
  }   
 };

#endif
