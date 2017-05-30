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
#include "test.h"
using namespace std;

void weights_to_vip(double** const &p_weights,
		    int p_nweights,
		    int p_nvips,
		    vector<Vip*>** p_vips) {

  vector<Vip*>* vips = new vector<Vip*>();
  Vip* vip;
  
  for (int i = 0; i < p_nvips; ++i) {
      vip = new Vip();
    for (int j = 0; j < p_nweights; ++j) {
      vip->push_back(Weight(j, p_weights[i][j]));
    }
    vips->push_back(vip);
  }

  (*p_vips) = vips;

}

void random_weights(int p_nvips,
		    int p_nweights,
		    double*** p_weights) {
  const int SEED = 29;
  srand(SEED);

  double **w = new double*[p_nvips];
  
  for (int i = 0; i < p_nvips; ++i) {
    w[i] = new double[p_nweights];

    double sum = 0;
    for (int j = 0; j < p_nweights; ++j) {
      w[i][j] = (rand() % 100) + 1;
      sum += w[i][j];
    }
    if (!double_cmp(sum)) {
      continue;
    }
    for (int j = 0; j < p_nweights; ++j) {
      w[i][j] /= sum;
    }
  }

  (*p_weights) = w;
}


void read_mvip_weights(int p_nvips,
		       int p_nweights,
		       double*** p_weights) {

  double **w = new double*[p_nvips];

  // skip header
  char c[1000];
  cin.getline(c, 1000);
  for (int i = 0; i < p_nvips; ++i) {
    w[i] = new double[p_nweights];

    double sum = 0;
    for (int j = 0; j < p_nweights; ++j) {
      cin >> w[i][j];
      sum += w[i][j];
    }
    if (!double_cmp(sum)) {
      continue;
    }
    for (int j = 0; j < p_nweights; ++j) {
      w[i][j] /= sum;
    }
  }

  (*p_weights) = w;
}


void read_svip_weights(int p_nvips,
		       int p_nweights,
		       double*** p_weights) {

  double **w = new double*[p_nvips];

  // skip header
  char c[1000];
  cin.getline(c, 1000);
  for (int i = 0; i < p_nvips; ++i) {
    w[i] = new double[p_nweights];

    cin.getline(c, 1000);
    double sum = 0;
    for (int j = 0; j < p_nweights; ++j) {
      cin >> w[i][j];
      sum += w[i][j];
    }
    if (!double_cmp(sum)) {
      continue;
    }
    for (int j = 0; j < p_nweights; ++j) {
      w[i][j] /= sum;
    }
    // read the end-of-line
    cin.getline(c, 1000);
  }

  (*p_weights) = w;
}


void uniform_fraction(int p_nvips,
		      double** p_frac) {

  double* frac = new double[p_nvips];
  for (int i = 0; i < p_nvips; ++i) {
    frac[i] = 1.0 / p_nvips;
  }
  (*p_frac) = frac;
}


void skewed_fraction(int p_nvips,
		     double** p_frac) {

  double* frac = new double[p_nvips];
  double frac_total = 0.0;
  for (int i = 0; i < p_nvips; ++i) {
    frac[i] = 100.0 / (i + 1);
    frac_total += frac[i];
  }
  for (int i = 0; i < p_nvips; ++i) {
    frac[i] /= frac_total;
  }
  (*p_frac) = frac;
}


void gen_default_rules(int p_ndefault_rules,
		       int p_ndefault_bits,
		       RuleSet** p_default_rules) {
  if (p_ndefault_rules == 0) {
    (*p_default_rules) = NULL;
    return;
  }
  
  string r;
  RuleSet* default_rules = new RuleSet();
  for (int i = 0; i < p_ndefault_rules; ++i) {
    r = get_root_pattern();
    int k = i;
    for (int j = 0; j < p_ndefault_bits; ++j, k /= 2) {
      if (k % 2) {
	r = pattern_one(r);
      }
      else {
	r = pattern_zero(r);
      }
    }
    default_rules->push_back(Rule(r, i));
  }
  (*p_default_rules) = default_rules;
}

void gen_fraction(const TestArg& p_arg,
	      double** p_frac) {
  if (p_arg.m_skew_frac) {
    skewed_fraction(p_arg.m_nvips, p_frac);
  }
  else {
    uniform_fraction(p_arg.m_nvips, p_frac);
  }
}

void gen_weights(const TestArg& p_arg,
		 double*** p_weights) {
  if (p_arg.m_gen) {
    random_weights(p_arg.m_nvips,
		   p_arg.m_nweights,
		   p_weights);
  }
  else if (p_arg.m_type == 'm' || p_arg.m_type == 'g') {
    read_mvip_weights(p_arg.m_nvips,
		      p_arg.m_nweights,
		      p_weights);
  }
  else if (p_arg.m_type == 's') {
    read_svip_weights(p_arg.m_nvips,
		      p_arg.m_nweights,
		      p_weights);
  }
}

void compute_imbalance(const double** & p_weights,
		       const double* & p_frac,
		       const double** & p_values,
		       int p_nvips,
		       int p_nweights,
		       double* p_imb) {
  double imb = 0.0;
  for (int i = 0; i < p_nvips; ++i) {
    for (int j = 0; j < p_nweights; ++j) {
      imb += fabs(p_weights[i][j] - p_values[i][j]) * p_frac[i];
    }
  }
  (*p_imb) = imb;
}

void print_weights(double** const &p_weights,
		   int p_nweights,
		   int p_nvips) {
  for (int i = 0; i < p_nvips; ++i) {
    for (int j = 0; j < p_nweights; ++j) {
      cout << p_weights[i][j] << " ";
    }
    cout << endl;
  }
}
