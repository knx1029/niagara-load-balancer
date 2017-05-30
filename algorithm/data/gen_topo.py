def phase(K, L, D, N):
    ## phase 1
    p = N / K
#    p = min(D / L, N / K)
    omega_p1 = D - L * p
    omega_p = L - omega_p1
    omega = min(omega_p1, omega_p)
    pi_p1 = N - K * p
    pi_p = K - pi_p1
    pi = min(pi_p, pi_p1)

    if (omega < 0) or (pi < 0):
        return None

    if (omega == 0):
        Q = 1
    elif (L % omega == 0):
        Q = L / omega
    else:
        Q = L / omega - 1

    if omega == omega_p1:
        R = map(lambda(x): [p] * x, [K] * L)
    else:
        R = map(lambda(x): [p + 1] * x, [K] * L)

#    print "omega", omega, omega_p, omega_p1
#    print "pi", pi, pi_p, pi_p1
    for i in range(Q):
        for l in range(i * omega, (i + 1) * omega):
#            for k in range(K):
            for k in range(i * pi, (i + 1) * pi):
                if (l >= L) or (k >= K):
                    continue
#                    return None
                if omega == omega_p1:
                    R[l][k] = p + 1
                else:
                    R[l][k] = p

#    print pi_p, pi_p1
#    for l in range(L):
#        for k in range(K):
#            print R[l][k],
#        print ""
    ## phase 2
    if (K - Q * pi == 0):
        return R

    shift = 0
    for l in range(Q * omega, L):
        for offset in range(pi):
            k = pi * Q + ((offset + shift) % (K - Q * pi))
            if (k >= K):
                continue
#                return None
            if omega == omega_p1:
                R[l][k] = p + 1
            else:
                R[l][k] = p
        shift = shift + N / D

    return R

def weight(K, L, D, N, R):
    for l in range(L):
        if (sum(R[l]) > N):
#            print K, L, D, N
#            print "Up", l, sum(R[l]), N
            return None

    for k in range (K):
        r = map(lambda(x): x[k], R)
        if (sum(r) > D):
#            print K, L, D, N
#            print "Down", r , sum(r), D
            return None

    s = 0
    num_rules = 0
    total_num_rules = 0
    p = N / K
    ws_list = []
    for d in range(1, L):
        c1 = 0
        c_pop1 = 0
        w = [0] * K
        frac_p = False
        frac_p1 = False
        for k in range(K):
            if (R[s][k] <= R[d][k]):
                frac_p1 = True
                w[k] = p + 1
            else:
                frac_p = True
                w[k] = p
        if (not frac_p) or (not frac_p1):
            w = [1] * K

        sumw = sum(w)
        total_num_rules = total_num_rules + sumw

        found = False
        for wl in ws_list:
            if (w == wl):
                found = True
        if (found):
            continue
        num_rules = num_rules + sumw
        ws_list.append(w)

    return num_rules, ws_list, total_num_rules


#K, L, D, N = 8, 8, 64, 64
#K, L, D, N = 55, 19, 32, 96
K, L, D, N = 53, 19, 64, 192

#K, L, D, N = 5, 5, 64, 192
#R = phase(K, L, D, N)

for L in range (4, 65):
#if False:
    max_num_rules = 0
    max_K = 0
    max_ws_list = None
    max_total_num_rules = 0
    for K in range(1, N):
#    for K in range(1, L + 1):
        R = phase(K, L, D, N)

        if (R == None):
            continue

        res = weight(K, L, D, N, R)
        if (res == None):
            continue

        num_rules, ws_list, total_num_rules  = weight(K, L, D, N, R)
        if (num_rules > max_num_rules):
#        if (True):
            max_num_rules = num_rules
            max_K = K
            max_ws_list = ws_list
            max_total_num_rules = total_num_rules

    if (max_ws_list == None):
        continue
    print "L{0}-K{1}-N{2}-D{3}".format(str(L), str(max_K), str(N), str(D)),
    print ",", max_num_rules, ",", max_total_num_rules
    print max_K
    print len(max_ws_list)
    for wl in max_ws_list:
        sumw = sum(wl)
        print " ".join(str(ww * 1.0 / sumw) for ww in wl)
