#include<cstdio>
#include<cstdlib>
#include<iostream>
#include<string>
#include<vector>
#include<cmath>
#include<algorithm>
#include<ctime>

#include "utils.h"
#include "svip_solver.h"
#include "unit_test.h"
#include "mvip_solver.h"
#include "grouper.h"
#include "test.h"

using namespace std;


int svip(const TestArg &p_arg) {
  if (p_arg.m_nvips == 0 || p_arg.m_nweights == 0) {
    return 1;
  }

  // Initialize everything    
  BitEval* eval = new BitEvalP(p_arg.m_balance_arg);

  double** weights;
  gen_weights(p_arg, &weights);

  vector<Vip*>* vips;
  weights_to_vip(weights,
		 p_arg.m_nweights,
		 p_arg.m_nvips,
		 &vips);

  RuleSet* default_rules;
  gen_default_rules(p_arg.m_ndefault_rules,
		    p_arg.m_ndefault_bits,
		    &default_rules);



  // solve
  SVipOutput* output = NULL;
  SVipSolver solver;


  for (vector<Vip*>::iterator itr = vips->begin();
       itr != vips->end(); ++itr) {
  
    double sum = 0;
    SVipInput input(*itr, default_rules, p_arg.m_eps, eval);
    bool result = solver.solve(input, &output);
    
    
    UnitTest test;
    result = test.check_svip(input, *output);
    
    if (!result || p_arg.m_print) {
      cout << "Correct? " << result << endl;
      cout << "input\n";
      input.print();
      cout << "output\n";
      output->print();
    }
    
    int kth = itr - vips->begin();    
    printf("%d,%d,%d,%lf,%lf\n",
	   kth,
	   output->m_rules->size(),
	   p_arg.m_nweights,
	   p_arg.m_eps,
	   p_arg.m_balance_arg);
    delete output;
  }


  // clean up
  for (int i = 0; i < p_arg.m_nvips; ++i) {
    delete [] weights[i];
  }
  delete [] weights;
  delete eval;
  for (vector<Vip*>::iterator itr = vips->begin();
       itr != vips->end(); ++itr) {
    delete (*itr);
  }
  delete vips;

  if (default_rules) {
    delete default_rules;
  }

  return 0;
}

int mvip(const TestArg& p_arg) {
  if (p_arg.m_nvips <= 0 ||
      p_arg.m_nweights <= 0 ||
      p_arg.m_min_nrules <= 0 ||
      p_arg.m_max_nrules <= p_arg.m_min_nrules) {
    return 1;
  }
  // Initialize everything    
  BitEval* eval = new BitEvalP(p_arg.m_balance_arg);

  double** weights = NULL;
  gen_weights(p_arg, &weights);

  double* frac = NULL;
  gen_fraction(p_arg, &frac);


  vector<Vip*>* vips = NULL;
  weights_to_vip(weights,
		 p_arg.m_nweights,
		 p_arg.m_nvips,
		 &vips);

  RuleSet* default_rules = NULL;
  gen_default_rules(p_arg.m_ndefault_rules,
		    p_arg.m_ndefault_bits,
		    &default_rules);


  // solve
  MVip* mvip = new MVip();
  for (vector<Vip*>::iterator itr = vips->begin();
       itr != vips->end(); ++itr) {
    int index = itr - vips->begin();
    mvip->push_back(SVip(*itr, eval, frac[index], index));
  }


  MVipInput input(mvip, default_rules, p_arg.m_eps, 0);

  // set nrules
  vector<int> nrules_array;
  int nrules_start = p_arg.m_nvips;
  if (default_rules) {
    nrules_start = p_arg.m_ndefault_rules;
  }
  nrules_array.push_back(nrules_start);
  for (int nrules = p_arg.m_min_nrules;
       nrules <= p_arg.m_max_nrules;
       nrules += p_arg.m_inc_nrules) {
    if (nrules > nrules_start) {
      nrules_array.push_back(nrules);
    }
  }

  double** values = new double*[p_arg.m_nvips];
  for (int i = 0; i < p_arg.m_nvips; ++i) {
    values[i] = new double[p_arg.m_nweights];
  }


  if (p_arg.m_print) {
    cout << "input\n";
    input.print();
  }
  
  // solve
  MVipSolver solver;
  MVipOutput* output = NULL;
  for (int i = 0; i < nrules_array.size(); ++i) {
    int nrules = nrules_array[i];
    input.m_max_num_rules = nrules;


    //    bool result = solver.solve(input, &output);
    
    if (i == 0) {
      solver.start(input);
    }
    solver.get_more_rules(input);
    bool result = solver.get_output(&output);

        
    if (p_arg.m_print) {
      cout << "output\n";
      output->print();
    }

    if (!result) {
      break;
    }
    UnitTest test;
    double imb;
    result = test.check_mvip(input, *output, values);

    if (p_arg.m_print) {
      cout << "values\n";
      print_weights(values,
		    p_arg.m_nweights,
		    p_arg.m_nvips);
    }

    test.compute_imbalance(weights,
			   frac,
			   values, 
			   p_arg.m_nweights,
			   p_arg.m_nvips,
			   &imb);
    if (result) {
      printf("%d,%lf,%d,%d\n",
	     nrules,
	     imb,
	     p_arg.m_nweights,
	     p_arg.m_nvips);
    }
    delete output;
    
    //solver.cleanup();
  }
  solver.cleanup();
  
  // clean up
  for (int i = 0; i < p_arg.m_nvips; ++i) {
    delete [] weights[i];
    delete [] values[i];
  }
  delete [] weights;
  delete [] values;
  delete eval;
  delete [] frac;
  delete mvip;
  for (vector<Vip*>::iterator itr = vips->begin();
       itr != vips->end(); ++itr) {
    delete (*itr);
  }
  delete vips;

  if (default_rules) {
    delete default_rules;
  }
  
  return 0;
}


int group(const TestArg &p_arg) {
  if (p_arg.m_nvips <= 0 || 
      p_arg.m_ngroups <= 0 || 
      p_arg.m_nweights <= 0 ||
      p_arg.m_min_nrules <= 0 ||
      p_arg.m_max_nrules <= p_arg.m_min_nrules) {
    return 1;
  }
  
  // Initialize everything    
  BitEval* eval = new BitEvalP(p_arg.m_balance_arg);

  double** weights = NULL;
  gen_weights(p_arg, &weights);

  double* frac = NULL;
  gen_fraction(p_arg, &frac);

  if (p_arg.m_print) {
    cout << "vips\n";
    print_weights(weights,
		  p_arg.m_nweights,
		  p_arg.m_nvips);
  }
  
  Grouper grouper;
  double** groups = NULL;
  double* group_frac = NULL;
  int* group_id;
  double group_imb;
  if (!grouper.group(weights,
		     frac,
		     p_arg.m_nweights,
		     p_arg.m_nvips,
		     p_arg.m_ngroups,
		     &groups,
		     &group_frac,
		     &group_id,
		     &group_imb)) {
    return 1;
  }

  
  vector<Vip*>* vips = NULL;
  weights_to_vip(groups,
		 p_arg.m_nweights,
		 p_arg.m_ngroups,
		 &vips);

  RuleSet* default_rules = NULL;
  gen_default_rules(p_arg.m_ndefault_rules,
		    p_arg.m_ndefault_bits,
		    &default_rules);


  // create mvip
  MVip* mvip = new MVip();
  for (vector<Vip*>::iterator itr = vips->begin();
       itr != vips->end(); ++itr) {
    int index = itr - vips->begin();
    mvip->push_back(SVip(*itr, eval, group_frac[index], index));
  }


  MVipInput input(mvip, default_rules, p_arg.m_eps, 0);
  
  // set nrules
  vector<int> nrules_array;
  int nrules_start = p_arg.m_ngroups;
  if (default_rules) {
    nrules_start = p_arg.m_ndefault_rules;
  }
  nrules_array.push_back(nrules_start);
  for (int nrules = p_arg.m_min_nrules;
       nrules <= p_arg.m_max_nrules;
       nrules += p_arg.m_inc_nrules) {
    if (nrules > nrules_start) {
      nrules_array.push_back(nrules);
    }
  }

  double** values = new double*[p_arg.m_ngroups];
  for (int i = 0; i < p_arg.m_ngroups; ++i) {
    values[i] = new double[p_arg.m_nweights];
  }

  if (p_arg.m_print) {
    cout << "groups\n";
    input.print();
  }

  // solve
  MVipOutput* output = NULL;
  MVipSolver solver;
  for (int i = 0; i < nrules_array.size(); ++i) {
    int nrules = nrules_array[i];
    input.m_max_num_rules = nrules;

    //    bool result = solver.solve(input, &output);

    if (i == 0) {
      solver.start(input);
    }
    solver.get_more_rules(input);
    bool result = solver.get_output(&output);

    if (!result || p_arg.m_print) {
      cout << "result " << result << endl;
      cout << "output\n";
      output->print();
    }

    UnitTest test;
    double imb;
    result = test.check_mvip(input, *output, values);

    if (p_arg.m_print) {
      cout << "values\n";
      print_weights(values,
		    p_arg.m_nweights,
		    p_arg.m_ngroups);
    }
    test.compute_imbalance(groups,
			   group_frac,
			   values,
			   p_arg.m_nweights,
			   p_arg.m_ngroups,
			   &imb);
    /*

    test.compute_group_imbalance(weights,
				 frac,
				 groups,
				 group_id,
				 p_arg.m_nweights,
				 p_arg.m_nvips,
				 p_arg.m_ngroups,
				 &imb);
    */
    
    test.compute_group_imbalance(weights,
				 frac,
				 values,
				 group_id,
				 p_arg.m_nweights,
				 p_arg.m_nvips,
				 p_arg.m_ngroups,
				 &imb);

    if (result) {
      printf("%d,%lf,%d,%d,%d,%lf\n",
	     nrules,
	     imb,
	     p_arg.m_nweights,
	     p_arg.m_nvips,
	     p_arg.m_ngroups,
	     group_imb);
    }

    delete output;
    // solver.cleanup();
  }
  solver.cleanup();
  
  // clean up
  for (int i = 0; i < p_arg.m_nvips; ++i) {
    delete [] weights[i];
  }
  delete [] weights;
  for (int i = 0 ; i < p_arg.m_ngroups; ++i) {
    delete [] values[i];
    delete [] groups[i];
  }
  delete [] groups;
  delete [] values;
  delete eval;
  delete [] frac;
  delete [] group_frac;
  delete [] group_id;
  delete mvip;
  for (vector<Vip*>::iterator itr = vips->begin();
       itr != vips->end(); ++itr) {
    delete (*itr);
  }
  delete vips;

  if (default_rules) {
    delete default_rules;
  }
  

  return 0;
}



int main(int argc, char ** argv) {
  TestArg arg(argc, argv);

  if (arg.m_print) {
    arg.print();
  }
  
  
  if (!arg.m_valid) {
    return 1;
  }
  
  if (arg.m_type == 's') {
    return  svip(arg);
  }
  else if (arg.m_type == 'm') {
    return mvip(arg);
  }
  else if (arg.m_type == 'g') {
    return group(arg);
  }


}
