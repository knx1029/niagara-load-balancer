#ifndef __NG_UNIT_TEST__

#define __NG_UNIT_TEST__


#include<string>
#include<vector>
#include<cmath>
#include<iostream>

#include "utils.h"
#include "svip_solver.h"
#include "mvip_solver.h"

using namespace std;

class UnitTest {

 public:
  bool check_svip(const SVipInput& p_input, const SVipOutput& p_output);
  
  bool check_mvip(const MVipInput& p_input,
		  const MVipOutput& p_output,
		  double** &p_values);

  void compute_imbalance(double** const & p_weights,
			 double* const & p_frac,
			 double** const & p_values,
			 int p_nweights,
			 int p_nvips,
			 double* p_imb);


  void compute_group_imbalance(double** const & p_weights,
			       double* const & p_frac,
			       double** const & p_values,
			       int* const & p_group_id,
			       int p_nweights,
			       int p_nvips,
			       int p_ngroups,
			       double* p_imb);


 private:
  bool compute_value(const RuleSet& p_rule,
		     const BitEval& p_eval,
		     int p_action_id,
		     double* p_value);

};

#endif
