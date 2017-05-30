#ifndef __NG_UTILS__

#define __NG_UTILS__

#include<cstdio>
#include<string>
#include<iostream>
#include<vector>

using namespace std;

const double EPSILON = 1e-9;
const int BITS = 32;

int double_cmp(double x);

string get_root_pattern();

double get_root_weight();

string pattern_zero(const string& p_string);

string pattern_one(const string& p_string);

bool pattern_contains(const string& p_wild,
		      const string& p_spec);
		
#endif
