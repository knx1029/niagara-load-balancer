#include<cstdio>
#include<string>

#include "utils.h"

using namespace std;

int double_cmp(double x) {
  return x < -EPSILON ? -1 : x > EPSILON;
}

string get_root_pattern() {
  string a;
  for (int i = 0; i < BITS; ++i) {
    a.push_back('*');
  }
  return a;
}

double get_root_weight() {
  return 1.0;
}

string pattern_zero(const string& p_string) {
  int index = p_string.find_last_of('*');
  return p_string.substr(0, index) + "0" + p_string.substr(index + 1);
}

string pattern_one(const string& p_string) {
  int index = p_string.find_last_of('*');
  return p_string.substr(0, index) + "1" + p_string.substr(index + 1);
}

bool pattern_contains(const string& p_wild,
		      const string& p_spec) {

  if (p_wild.size() != p_spec.size()) {
    return false;
  }
  for (int i = 0; i < p_wild.size(); ++i) {
    if (p_wild[i] != '*'&& p_wild[i] != p_spec[i]) {
      return false;
    }
  }
  return true;
}
