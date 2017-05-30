#ifndef __NG_GROUPER__
#define __NG_GROUPER__

class Grouper {

 public:

  Grouper(): GROUP_THRESHOLD(1e-6) {}
  
  double GROUP_THRESHOLD;
  
  bool group(double** const &p_vips,
	     double* const &p_frac,
	     int p_num_weight,
	     int p_num_vip,
	     int p_num_group,
	     double***p_groups,
	     double** p_group_frac,
	     int** p_group_id,
	     double* p_group_imb);  

  
  
};


#endif
