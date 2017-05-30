// #include "mvip_solver.h"
#include<cmath>
#include<cstring>
#include<algorithm>

#include "grouper.h"
#include "unit_test.h"
#include "utils.h"

using namespace std;

bool Grouper::group(double** const &p_vips,
		    double* const &p_frac,
		    int p_num_weight,
		    int p_num_vip,
		    int p_num_group,
		    double*** p_groups,
		    double** p_group_frac,
		    int** p_group_id,
		    double* p_group_imb) {

  if (p_num_group <= 0 || p_num_group > p_num_vip) {
    return false;
  }
  
  double** groups = new double*[p_num_group];
  int* group_id = new int[p_num_vip];
  double* group_frac = new double[p_num_group];

  for (int k = 0; k < p_num_group; ++k) {
    groups[k] = new double[p_num_weight];
    for (int j = 0; j < p_num_weight; ++j) {
      groups[k][j] = p_vips[k][j];
    }
  }
  for (int i = 0; i < p_num_vip; ++i) {
    group_id[i] = -1;
  }
  
  double total_diff = 0, last_diff = 1;
  bool change = true;
  //  while (double_cmp(last_diff - total_diff - GROUP_THRESHOLD) > 0) {
  //    while (double_cmp(last_diff - total_diff) > 0) {
  while (change) {
    last_diff = total_diff;
    total_diff = 0.0;
    change = false;

    //    cout << "--------------------\n";
    for (int i = 0; i < p_num_vip; ++i) {
      double min_diff = -1;
      int min_index = -1;
      for (int k = 0; k < p_num_group; ++k) {
	double diff = 0.0;
	
	for (int j = 0; j < p_num_weight; ++j) {
	  diff += (p_vips[i][j] - groups[k][j]) * (p_vips[i][j] - groups[k][j]);
	}
	
	// update group
	if (min_diff < 0 || diff < min_diff) {
	  min_diff = diff;
	  min_index = k;
	}
      }

      //      cout << i <<" " << min_index << endl;
      if (group_id[i] != min_index) {
	group_id[i] = min_index;
	change = true;
      }

      // sum difference
      total_diff += min_diff * p_frac[i];
    }


    // update grouping
    for (int k = 0; k < p_num_group; ++k) {
      group_frac[k] = 0.0;
      for (int j = 0; j < p_num_weight; ++j) {
	groups[k][j] = 0.0;
      }
    }
    for (int i = 0; i < p_num_vip; ++i) {
      int k = group_id[i];
      group_frac[k] += p_frac[i];
      for (int j = 0; j < p_num_weight; ++j) {
	groups[k][j] += p_vips[i][j] * p_frac[i];
      }
    }
    for (int k = 0; k < p_num_group; ++k) {
      //      cout << k << " : ";
      for (int j = 0; j < p_num_weight; ++j) {
	groups[k][j] /= group_frac[k];
	//	cout << groups[k][j] << " ";
      }
      //      cout << endl;
    }

    //    cout << total_diff << endl;
  }


  double group_imb = 0.0;
  for (int i = 0; i < p_num_vip; ++i) {
    int k = group_id[i];
    for (int j = 0; j < p_num_weight; ++j) {
      group_imb += fabs(p_vips[i][j] - groups[k][j]) * p_frac[i];
    }
  }
  group_imb /= 2;
  
  (*p_groups) = groups;
  (*p_group_id) = group_id;
  (*p_group_frac) = group_frac;
  (*p_group_imb) = group_imb;
  return true;
  
}
