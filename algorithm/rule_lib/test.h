#ifndef __NG_TEST__
#define __NG_TEST__

#include<cstring>

#include "svip_solver.h"
#include "mvip_solver.h"

struct TestArg {
  int m_nvips;
  int m_nweights;
  
  double m_eps;
  double m_balance_arg;
  
  int m_ndefault_rules;
  int m_ndefault_bits;

  bool m_skew_frac;
  int m_ngroups;
  bool m_gen;

  char m_type;
  
  bool m_valid;
  bool m_print;

  int m_min_nrules;
  int m_max_nrules;
  int m_inc_nrules;

  void print() {
    printf("type=%c, valid? %d print? %d\n",
	   m_type,
	   m_valid,
	   m_print);
    printf("nweights=%d, nvips=%d, ngroups=%d\n",
	   m_nweights,
	   m_nvips,
	   m_ngroups);
    printf("eps=%lf, balance_arg=%lf\n",
	   m_eps,
	   m_balance_arg);
    printf("default_rules=%d, %d\n",
	   m_ndefault_rules,
	   m_ndefault_bits);
    printf("skew_frac? %d, m_gen? %d\n",
	   m_skew_frac,
	   m_gen);
    printf("nrules: %d -> %d, +%d\n",
	   m_min_nrules,
	   m_max_nrules,
	   m_inc_nrules);

  }
  

  TestArg(int argc, char** argv) {

    m_nvips = 0;
    m_nweights = 0;
    m_eps = 1e-3;
    m_balance_arg = 0.5;
    m_ndefault_rules = 0;
    m_ndefault_bits = 0;
    m_skew_frac = true;
    m_ngroups = 0;
    m_gen = true;
    m_type = 'n';
    m_valid = true;
    m_print = false;
    m_min_nrules = 0;
    m_max_nrules = 0;
    m_inc_nrules = 0;

    for (int i = 1; i < argc; ) {
      if (!strcmp(argv[i], "-v") && i + 1 < argc) {
	sscanf(argv[i + 1], "%d", &m_nvips);
	i += 2;
      }
      else if (!strcmp(argv[i], "-w") && i + 1 < argc) {
	sscanf(argv[i + 1], "%d", &m_nweights);
	i += 2;
      }
      else if (!strcmp(argv[i], "-e") && i + 1 < argc) {
	sscanf(argv[i + 1], "%lf", &m_eps);
	i += 2;
      }
      else if (!strcmp(argv[i], "-b") && i + 1 < argc) {
	sscanf(argv[i + 1], "%d", &m_balance_arg);
	i += 2;	
      }
      else if (!strcmp(argv[i], "-d") && i + 2 < argc) {
	sscanf(argv[i + 1], "%d", &m_ndefault_rules);
	sscanf(argv[i + 2], "%d", &m_ndefault_bits);
	i += 3;
      }
      else if (!strcmp(argv[i], "-f") && i + 1 < argc) {
	char c;
	sscanf(argv[i + 1], "%c", &c);
	m_skew_frac = (c == 's');
	i += 2;
      }
      else if (!strcmp(argv[i], "-g") && i + 1 < argc) {
	sscanf(argv[i + 1], "%d", &m_ngroups);
	i += 2;
      }
      else if (!strcmp(argv[i], "-i") && i + 1 < argc) {
	char c;
	sscanf(argv[i + 1], "%c", &c);
	m_gen = (c == 'g');
	i += 2;
      }
      else if (!strcmp(argv[i], "-t") && i + 1 < argc) {
	sscanf(argv[i + 1], "%c", &m_type);
	i += 2;
      }
      else if (!strcmp(argv[i], "-p")) {
	m_print = true;
	i += 1;
      }
      else if (!strcmp(argv[i], "-r") && i + 3 < argc) {
	sscanf(argv[i + 1], "%d", &m_min_nrules);
	sscanf(argv[i + 2], "%d", &m_max_nrules);
	sscanf(argv[i + 3], "%d", &m_inc_nrules);
	i += 4;
      }
      else {
	m_valid = false;
	break;
      }
    }

    if (m_type != 's' && m_type != 'm' && m_type != 'g') {
      m_valid = false;
    }

    if (!m_valid) {
      cout << "main -t {s|m|g} -v $nvips -w $nweights -g $ngroups -d $default_rules $ndefault_dbits -e $eps -f (s|u) -b {$balanace_arg} -i {g|r} -r $min_nrules $max_nrules $inc_nrules -p" << endl;
    }
  }
};

void read_svip_weights(int p_nvips,
		       int p_nweights,
		       double*** p_weights);


void read_mvip_weights(int p_nvips,
		       int p_nweights,
		       double*** p_weights);


void random_weights(int p_nvips,
		    int p_nweights,
		    double*** p_weights);



void weights_to_vip(double** const &p_weights,
		    int p_nweights,
		    int p_nvips,
		    vector<Vip*>** p_vips);


void uniform_fraction(int p_nvips,
		      double** p_frac);

void skewed_fraction(int p_nvips,
		     double** p_frac);

void gen_default_rules(int p_ndefault_rules,
		       int p_ndefault_bits,
		       RuleSet** p_default_rules);

void gen_fraction(const TestArg& p_arg,
		  double** p_frac);

void gen_weights(const TestArg& p_arg,
		 double*** p_weights);


void print_weights(double** const &p_weights,
		   int p_nweights,
		   int p_nvips);

#endif
