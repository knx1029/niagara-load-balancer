import math


#####rules_per_w = floor(ceiling(log2(1/ne)) * 2/3) + 1
#rules_per_w = ceiling(ceiling(log2(1/ne)) / 2) + 1
#total_rules = rules_per_w * (n - 1) + 1
def total_rules(w, n):
  exp_f = int(math.log(w/e, 2.0))
  exp_w = int(exp_f)  # + 1 - 1e-6)
  r_per_w = int(exp_w / 3.0  + 0.5 - 1e-6) * 2+ 1
  p = n * r_per_w 

  print exp_w, exp_f, r_per_w

  return p


e = 0.00098 #1.0/1024
t = 2.0 / 3

for N in [3, 4]: #5, 6, 7, 9, 10, 11, 12, 20]:
#for N in [17]:
  print "#clusters = ", N,

  w = 1.0 / N
  p = total_rules(w, N - 1) + 1

  print "no ecmp, #rules = ", p

  K = 1 << int(math.log(N, 2.0))
#  w2 = 1.0 / K
  w2 = 1.0 / K - 1.0 / N

  if False:
#  for a in range(1, N):
    b = N - a
    if (b > K):
      continue
    y = b * 1.0 / a
    x = a * math.log(y, 2.0)
    print "a = ", a,
    w1 = b * w2 / a
    z = 0
    if (w1 > w2):
      z = 1 + total_rules(w1, a - 1) + total_rules(w2, b)
    else:
      z = 1 + total_rules(w1, a) + total_rules(w2, b - 1)
    print "#rules = ", z+K, " +w = ", w1, ", -w = ", w2



