
ZERO = 1e-8

def double_cmp(x):
    if (x < -ZERO):
        return -1
    elif (x > ZERO):
        return 1
    else:
        return 0


## define overlap, s1 is contained/overlap/none in s2
MISC, NONE, CONTAINED, OVERLAP = -1, 0, 1, 2
def overlap(s1, s2):
  if (len(s1) != len(s2)):
    return MISC
  conj = ""
  for i in range(0, len(s1)):
    if (s1[i] != s2[i] and s1[i] != '*' and s2[i] != '*'):
      return NONE
    elif (s1[i] == '*'):
      conj = conj + s2[i]
    else:
      conj = conj + s1[i]
  if (s1 == conj):
    return CONTAINED
  else:
    return OVERLAP


## return the join of s1 and s2
def join(s1, s2):
  if (len(s1) != len(s2)):
    return None
  conj = ""
  for i in range(0, len(s1)):
    if (s1[i] != s2[i] and s1[i] != '*' and s2[i] != '*'):
      return None
    elif (s1[i] == '*'):
      conj = conj + s2[i]
    else:
      conj = conj + s1[i]
  return conj


def get_unit(k):
  return 1.0 / (1 << k)

def get_level(str):
  return len(str) - str.count('*')
