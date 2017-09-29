from scipy import misc
from collections import deque
import numpy as np

'''
    Level 1 with patterns defined by the sign of vertex gradient: modified core algorithm of levels 1 + 2.

    Pixel comparison in 2D forms lateral and vertical derivatives: 2 matches and 2 differences per pixel. 
    They are formed on the same level because average lateral match ~ average vertical match.
    
    Pixels are discrete samples of continuous image, so rightward and downward derivatives per pixel are 
    equally representative samples of continuous 0-90 degree gradient: minimal unique unit of 2D gradient 
    Hence, such vertex gradient is computed as average of these two orthogonally diverging derivatives.
   
    2D patterns are blobs of same-sign vertex gradient, of value for vP or difference for dP.
    Level 1 has 5 steps of encoding, incremental per line defined by vertical coordinate y:

    y:   comp(p_):  lateral comp -> tuple t,
    y-1: ycomp (t_): vertical comp -> vertex t2,
    y-1: form_P(t2_): lateral combination -> 1D pattern P,
    y-2: form_P2 (P_): vertical comb | comp -> 2D pattern P2,
    y-2: term_P2 (P2_): P2s are terminated and evaluated for recursion
    
    I prefer unpacked arguments for visibility, will optimize for speed latter
'''

def comp(p_):  # comparison of consecutive pixels within line forms tuples: pixel, match, difference

    t_ = []  # complete fuzzy tuples: summation range = rng
    it_ = []  # incomplete fuzzy tuples: summation range < rng
    d, m = 0, 0  # no d, m at x = 0

    for p in p_:

        for it in it_:  # incomplete tuples with summation range from 0 to rng
            pri_p, fd, fm = it

            d = p - pri_p  # difference between pixels
            m = min(p, pri_p)  # match between pixels

            fd += d  # fuzzy d: sum of ds between p and all prior ps within it_
            fm += m  # fuzzy m: sum of ms between p and all prior ps within it_

        if len(it_) == rng:

            t = pri_p, fd, fm
            t_.append(t)
            del it_[0]  # completed tuple is transferred from it_ to t_

        it = p, d, m
        it_.append(it)  # new prior tuple

    t_ += it_  # last number = rng of tuples remain incomplete
    return t_

# my conventions: postfix '_' denotes array vs. element, prefix '_' denotes higher-line variable


def ycomp(t_, _t_, _vP_, _dP_):  # vertical comparison between pixels, forms t2: p, fd, fdy, fm, fmy

    vP_, dP_, valt_, dalt_ = [],[],[],[]  # append by form_P, alt_ -> alt2_, packed in scan_higher?

    vP = 0,0,0,0,0,0,0,0,[]  # pri_s, I, D, Dy, M, My, G, rdn_olp, e_
    dP = 0,0,0,0,0,0,0,0,[]  # pri_s, I, D, Dy, M, My, G, rdn_olp, e_

    olp = 0,0,0  # olp_len, olp_vG, olp_dG: common for current vP and dP
    x = 0

    for t, _t in zip(t_, _t_):  # compares vertically consecutive pixels, forms vertex gradients

        x += 1
        p, d, m = t
        _p, _d, _m = _t

        # non-fuzzy pixel comparison:

        dy = p - _p  # vertical difference between pixels, summed -> Dy
        dg = _d + dy  # gradient of difference, formed at prior-line pixel _p, -> dG: variation eval?

        my = min(p, _p)   # vertical match between pixels, summed -> My
        vg = _m + my - ave  # gradient of predictive value (relative match) at prior-line _p, -> vG

        t2 = p, d, dy, m, my  # 2D tuple, + fd, fv -> type-specific g, _g; all accumulated in P:

        # form 1D value pattern vP: horizontal span of same-sign vg s with associated vars:

        sv, olp, valt_, dalt_, vP, dP, vP_, _vP_ = \
        form_P(0, t2, vg, dg, olp, valt_, dalt_, vP, dP, vP_, _vP_, x)

        # form 1D difference pattern dP: horizontal span of same-sign dg s + associated vars:

        sd, olp, dalt_, valt_, dP, vP, dP_, _dP_ = \
        form_P(1, t2, dg, vg, olp, dalt_, valt_, dP, vP, dP_, _dP_, x)

    # line ends, olp term, vP term, dP term, no init, inclusion per incomplete lateral fd and fm:

    dalt_.append(olp); valt_.append(olp)  # if any?
    olp_len, olp_vG, olp_dG = olp  # same for vP and dP;     incomplete vg - ave / (rng / X-x)?

    if olp_vG > olp_dG:  # comp of olp_vG to olp_dG, == goes to alt_P or to vP: primary?
       vP[7] += olp_len  # olp_len is added to redundant overlap of lesser-oG-  vP or dP
    else:
       dP[7] += olp_len  # no P[8] /= P[7]: rolp = rdn_olp / len(e_): P to alt_Ps rdn ratio

    if y+1 > rng:

        vP_, _vP_ = scan_higher(0, vP, valt_, vP_, _vP_, x)  # empty _vP_?
        dP_, _dP_ = scan_higher(1, dP, dalt_, dP_, _dP_, x)  # empty _dP_?

    return vP_, dP_  # converted to arguments _vP_, _dP_


def form_P(typ, t2, g, alt_g, olp, alt_, _alt_, P, alt_P, P_, _P_, x):  # forms 1D Ps

    p, d, dy, m, my = t2  # 2D tuple of quarter-vertex per pixel
    pri_s, I, D, Dy, M, My, G, rdn_olp, e_ = P

    if typ == 0:
        olp_len, oG, alt_oG = olp  # overlap between current vP and dP, accumulated in ycomp,
    else:
        olp_len, alt_oG, oG = olp  # -> P2 rdn_olp2, generic 1D ave *= 2: low variation?

    s = 1 if g > 0 else 0
    if s != pri_s and x > rng + 2:  # P (span of same-sign gs) is terminated

        if alt_oG > oG:  # comp of olp_vG to olp_dG, == goes to alt_P or to vP: primary pattern?
            rdn_olp += olp_len  
        else:
            alt_P[7] += olp_len  # redundant overlap in weaker-oG- vP or dP, at either-P term

        P = pri_s, I, D, Dy, M, My, G, rdn_olp, e_ # -> rdn_olp2, no A = ave * rdn_olp / e_: dA < cost?
        P_, _P_ = scan_higher(typ, P, alt_, P_, _P_, x)  # continuity scan over higher-line _Ps

        alt = alt_P, olp_len, oG, alt_oG  # or P index len(P_): faster than P?  for P eval in form_blob
        alt_.append(alt)

        _alt = P, olp_len, alt_oG, oG  # redundant olp repr in concurrent alt_P, formed by terminated P
        _alt_.append(_alt)

        I, D, Dy, M, My, G, rdn_olp, e_, alt_ = 0,0,0,0,0,0,0,[],[]
        olp = 0,0,0  # P, alt_, olp are initialized

    # continued or initialized P vars are accumulated:

    olp_len += 1  # alt P overlap: olp_len, oG, alt_oG are accumulated till either P or _P is terminated
    oG += g; alt_oG += alt_g

    I += p    # p s summed within P
    D += d    # lateral D, for P comp and P2 normalization
    Dy += dy  # vertical D, for P2 normalization
    M += m    # lateral D, for P comp and P2 normalization
    My += my  # vertical M, for P2 normalization
    G += g    # d or v gradient summed to define P value, or V = M - 2a * W?

    if typ == 0:
        pri = p, g, alt_g  # g = v gradient
        e_.append(pri)  # pattern element: prior same-line vertex, for selective incremental range
    else:
        e_.append(g)  # g = d gradient and pattern element, for selective incremental derivation

    P = s, I, D, Dy, M, My, G, rdn_olp, e_  # incomplete P
    olp = olp, oG, alt_oG

    return s, olp, alt_, _alt_, P, alt_P, P_, _P_  # alt_ and _alt_ accumulated in ycomp per line


def scan_higher(typ, P, alt_, P_, _P_, x):  # P scans overlapping _Ps for inclusion, _P termination

    A = ave  # initialization before accumulation

    fork_ = deque()  # higher-line matches per P, to assign redundancy and move term _P to next _P
    root_, blob_, buff_ = deque(), deque(), deque()

    vPP_, dPP_, _vPP_, _dPP_ = [],[],[],[]
    _ix = 0  # initial x of _P displaced from _P_ by last comp_P

    s, I, D, Dy, M, My, G, rdn_alt, e_ = P
    ix = x - len(e_)  # initial x of P

    while x >= _ix:  # P to _P connection eval, while horizontal overlap between P and _P:

        fork_oG = 0  # fork overlap gradient: oG += g, approx: oG = G * mw / len(e_)
        ex = x  # x coordinate of current P element
        _P = _P_.popleft()

        # _P = _P, _alt_, lower: root_, blob, blob_, vPP_, dPP_, + higher: fork_, _vPP_, _dPP_?
        # _P = _s, _ix, _x, _I, _D, _Dy, _M, _My, _G, _rdn_alt, _e_

        if P[0] == _P[0][0]:  # if s == _s: v or d sign match

            while ex > _P[0][1]: # _ix = _P[0][1]
        
                for e in e_:  # oG accumulation per P (PM, PD from comp_P only)

                    if typ == 0: fork_oG += e[1]  # if vP: e = p, g, alt_g
                    else: fork_oG += e  # if dP: e = g
                    ex += 1

            fork = fork_oG, _P  # or PM, PD in comp_P, vs. re-packing _P, rdn = sort order
            fork_.append(fork)  # _P inclusion in P

            _P[3].append(P)  # root_.append(P), to track continuing roots in form_PP

        if _P[0][2] > ix:  # if _x > ix:

            buff_.append(_P)  # _P with updated root_ is buffered for next-P comp

        else:  # no horizontal overlap between _P and next P, _P is evaluated for termination:

            if (root_ == 0 and y > rng + 3) or y == Y - 1:  # _P or frame is terminated

                for blob in blob_:  # blob += root blob, root_-> blob_: terminated P conv per fork

                    blob, _vPP, _dPP = blob  # <= one _vPP and _dPP per higher-line blob
                    term_P2(blob, A)  # eval for 2D P re-orient and re-scan, no direct recursion

                    if _vPP: term_P2(_vPP, A)  # if comp_P in fork_eval(blob)
                    if _dPP: term_P2(_dPP, A)  # not for _dPP in _dPP_: only to eval for rdn?

            buff_ += _P_  # for scan_higher(next P)

    # no more horizontal overlap between P and _P:

    if fork_: # if len(fork_) > 0: P is evaluated for inclusion into its fork _Ps:

        bA = A  # base-case P eval for _P blob inclusion and comp_P
        fork_, bA = fork_eval(2, P, fork_, bA)  # bA *= blob rdn

        if vPP_:  # = lateral len(dPP_): from comp_P over same forks, during fork_eval of blob_

            vA = bA  # eval for inclusion in vPPs (2D value patterns), rdn alt_ = blobs:
            vPP_, vA = fork_eval(0, P, vPP_, vA)

            dA = vA  # eval for inclusion in dPPs (2D difference patterns), rdn alt_ = vPPs:
            dPP_, dA = fork_eval(1, P, dPP_, dA)

            # individual vPPs and dPPs are also modified in their fork

    P = P, alt_, fork_, vPP_, dPP_  # next-line ycomp adds root_: lower-line inclusions
    P_.append(P)  #  for P_ to _P_ conversion in next-line ycomp arguments

    _P_ = buff_
    return P_, _P_


def fork_eval(typ, P, fork_, A):  # A was accumulated, _Ps eval for form_blob, comp_P, form_PP

    # from scan_higher(): fork = crit, _P:
    # _P = _P, _alt_ + lower-line root_, blob, blob_, _vPP_, _dPP_
    # _P = _s, _ix, _x, _I, _D, _Dy, _M, _My, _G, rdn_alt, _e_

    ini = 1; select_ = []
    fork_.sort(key = lambda fork: fork[0])  # or sort and select at once?

    while fork_ and (crit > A or ini == 1):  # fork[0]: oG if fork | PM if vPP | PD if dPP

        fork = fork_.pop()
        crit, fork = fork  # then criterion is packed in _G, rdn_alt is packed in rdn?

        if typ == 2:  # fork = blob, same min oG for blob inclusion and comp_P?

            fork = form_blob(P, fork)
            vPP, dPP = comp_P(P, fork)  # adding PM | PD to fork
            fork = fork, vPP, dPP

        else:
            fork = form_PP(typ, P, fork)  # fork = vPP or dPP

        # merges vertically contiguous and horizontally overlapping same-type and sign Ps in P2s
        # P2: blob | vPP | dPP, alt_ -> rolp and alt2_, -> rolp2: area overlap?

        A += A  # rdn++, formed per eval: a * rolp * rdn.?  no rolp alone: adjustment < cost?
        ini = 0

        select_.append(fork)  # not-selected forks are out of fork_, don't increment their root_

    return select_, A  # A is specific to fork


def form_blob(P, fork):  # P inclusion into selected fork's blob, initialized or continuing

    # _P = _P, _alt_, root_, blob, blob_, _vPP_, _dPP_
    # _P = _s, _ix, _x, _I, _D, _Dy, _M, _My, _G, rdn, _e_

    s, I, D, Dy, M, My, G, e_, alt_, rdn = P  # rdn includes rdn_alt?

    if fork[1][9] > 0:  # rdn > 0: new blob initialization, then terminated unless max fork?

        I2 = I
        D2 = D; Dy2 = Dy
        M2 = M; My2 = My
        G2 = G
        area = len(e_)  # no separate e2_: Py_( P( e_?
        alt2_ = alt_  # or replaced by alt_blob_?
        rdn2 = rdn
        Py_ = P  # vertical array of patterns within a blob

        blob = I2, D2, Dy2, M2, My2, G2, area, alt2_, rdn2, Py_
        fork[4].append(blob) # blob_.append?

    else:  # increments axis: max _fork's blob in blob_ of max fork: first or separate?

        I2, D2, Dy2, M2, My2, G2, area, alt2_, Py_ = fork[1]  # blob @ axis or first fork?

        I2 += I
        D2 += D; Dy2 += Dy
        M2 += M; My2 += My
        G2 += G
        area += len(e_)  # no separate e2_: Py_( P( e_?
        alt2_ += alt_  # or replaced by alt_blob_?
        rdn2 =+ rdn
        Py_.append(fork[0])  # vertical array of patterns within a blob

        fork[1] = I2, D2, Dy2, M2, My2, G2, area, alt2_, rdn2, Py_

    return fork


def comp_P(P, P_, _P, _P_, x):  # forms 2D derivatives of 1D P vars to define vPP and dPP:

    ddx = 0  # optional;

    s, I, D, Dy, M, My, G, e_, oG, rdn, alt_ = P  # select alt_ per fork, no olp: = mx?
    _s, _ix, _x, _I, _D, _Dy, _M, _My, _G, _e_, _rdn, _alt_, blob_ = _P  # fork = P, _alt_, blob_?

    ix = x - len(e_)  # len(e_) or w: P width, initial coordinate of P, for output only?

    dx = x - len(e_)/2 - _x - len(_e_)/2  # Dx? comp(dx), ddx = Ddx / h? dS *= cos(ddx), mS /= cos(ddx)?
    mx = x - _ix
    if ix > _ix: mx -= ix - _ix  # x overlap, mx - a_mx, form_P(vxP), vs. discont: mx = -(a_dx - dx)?

    dw = len(e_) - len(_e_)  # -> dwP: higher dim? Ddx + Dw triggers adjustment of derivatives or _vars?
    mw = min(len(e_), len(_e_))  # w: P width = len(e_), relative overlap: mx / w, similarity: mw?

    # ddx and dw signs correlate, dx (position) and dw (dimension) signs don't correlate?
    # full input CLIDV comp, or comp(S| aS(L rdn norm) in positive eM = mx+mw, more predictive than eD?

    dI = I - _I; mI = min(I, _I)  # eval of MI vs. Mh rdn at term PP | var_P, not per slice?
    dD = D - _D; mD = min(D, _D)
    dM = M - _M; mM = min(M, _M)  # no G comp: y-derivatives are incomplete. also len(alt_) comp?

    PD = ddx + dw + dI + dD + dM  # defines dPP; var_P form if PP form, term if var_P or PP term;
    PM = mx + mw + mI + mD + mM   # defines vPP; comb rep value = PM * 2 + PD?  group by y_ders?

    # vPP and dPP included in selected forks, rdn assign and form_PP eval after fork_ term in form_blob?

    blob= 0,0,0,0,0,0,0,0,0,0,[],[]  # crit, rdn, W, I2, D2, Dy2, M2, My2, G2, rdn2, alt2_, Py_
    vPP = 0,0,0,0,0,0,0,0,0,0,[],[]
    dPP = 0,0,0,0,0,0,0,0,0,0,[],[]  # P2s are initialized at non-matching P transfer to _P_?

    ''' np.array for direct accumulation, or simply iterator of initialization?

    P2_ = np.array([blob, vPP, dPP],
        dtype=[('crit', 'i4'), ('rdn', 'i4'), ('W', 'i4'), ('I2', 'i4'), ('D2', 'i4'), ('Dy2', 'i4'),
        ('M2', 'i4'), ('My2', 'i4'), ('G2', 'i4'), ('rdn2', 'i4'), ('alt2_', list), ('Py_', list)])
    '''

    P = s, I, D, Dy, M, My, G, e_, alt_, blob_  # _fork_ is empty, similar to tuple declaration?
    # returned Ps also include current derivatives per var?

    P_.append(P)  # _P_ = P_ for next-line comp, if no horizontal overlap between P and next _P

    return P_, _P_


def form_PP(PP, fork, root_, blob_, _P_, _P2_, _x, A):  # forms vPPs, dPPs, and their var Ps

    if fork[1] > 0:  # rdn > 0: new PP initialization?

    else:  # increments PP of max fork, cached by fork_eval(), also sums all terminated PPs?

        crit, rdn, W, I2, D2, Dy2, M2, My2, G2, rdn2, alt2_, Py_ = PP  # initialized at P re-input in comp_P

        W += len(alt_); I2 += I; D2 += D; Dy2 += Dy; M2 += M; My2 += My; G2 += G; alt2_ += alt_
        Py_.append(P)

    # _P = _P, blob, _alt_, root_, blob_, _vPP_, _dPP_
    # _P = _s, _ix, _x, _I, _D, _Dy, _M, _My, _G, _e_

    # dimensionally reduced axis: vP'PP or contour: dP'PP; dxP is direction pattern

    a_mx = 2; a_mw = 2; a_mI = 256; a_mD = 128; a_mM = 128  # feedback to define var_vPs (variable value patterns)
    # a_PM = a_mx + a_mw + a_mI + a_mD + a_mM  or A * n_vars, rdn accum per var_P, alt eval per vertical overlap?


    mx, dx, mw, dw, mI, dI, mD, dD, mM, dM, P, _P = fork  # current derivatives, to be included if match
    s, ix, x, I, D, Dy, M, My, G, r, e_, alt_ = P  # input P or _P: no inclusion of last input?

    # criterion eval, P inclusion in PP, then all connected PPs in CP, unique tracing of max_crit PPs:

    if crit > A * 5 * rdn:  # PP vars increment, else empty fork ref?

        W += len(alt_); I2 = I; D2 = D; Dy2 = Dy; M2 = M; My2 = My; G2 = G; alt2_ = alt_; Py_ = P
        # also var_P form: LIDV per dx, w, I, D, M? select per term?

        PP = W, I2, D2, Dy2, M2, My2, G2, alt2_, Py_  # alt2_: fork_ alt_ concat, to re-compute redundancy per PP

        fork = len(_P_), PP
        blob_.append(fork)  # _P index and PP per fork, possibly multiple forks per P

        root_.append(P)  # connected Ps in future blob_ and _P2_

    return PP


def term_P2(P2, A):  # blob | vPP | dPP eval for rotation, re-scan, re-comp, recursion, accumulation

    P2_ = []
    ''' 
    conversion of root to term, sum into wider fork, also sum per frame?
    
    mean_dx = 1  # fractional?
    dx = Dx / H
    if dx > a: comp(abs(dx))  # or if dxP Dx: fixed ddx cost?  comp of same-sign dx only

    vx = mean_dx - dx  # normalized compression of distance: min. cost decrease, not min. benefit?
    
    
    eval of d,m adjust | _var adjust | x,y adjust if projected dS-, mS+ for min.1D Ps over max.2D

        if dw sign == ddx sign and min(dw, ddx) > a: _S /= cos (ddx)  # to angle-normalize S vars for comp

    if dw > a: div_comp (w): rw = w / _w, to width-normalize S vars for comp: 

        if rw > a: pn = I/w; dn = D/w; vn = V/w; 

            comp (_n) # or default norm for redun assign, but comp (S) if low rw?

            if d_n > a: div_comp (_n) -> r_n # or if d_n * rw > a: combined div_comp eval: ext, int co-variance?

        comp Dy and My, /=cos at PP term?  default div and overlap eval per PP? not per CP: sparse coverage?
        
    rrdn = 1 + rdn_w / len(e_)  # redundancy rate / w, -> P Sum value, orthogonal but predictive
    
    S = 1 if abs(D) + V + a * len(e_) > rrdn * aS else 0  # rep M = a*w, bi v!V, rdn I?
    '''


def level_1(f):

    # my conventions: postfix '_' denotes array vs. element, prefix '_' denotes higher-line variable

    global rng; rng = 1
    global ave; ave = 127  # filters, ultimately set by separate feedback, then ave *= rng

    global Y; global X
    Y, X = f.shape  # Y: frame height, X: frame width

    global _vP2_; _vP2_ = []
    global _dP2_; _dP2_ = []  # 2D Ps terminated on line y-3

    _vP_, _dP_, frame_ = [], [], []

    global y; y = 0

    p_ = f[0, :]   # first line of pixels
    _t_= comp(p_)  # _t_ includes ycomp() results and Dy, My, dG, vG = 0

    for y in range(1, Y):  # vertical coordinate y is index of new line p_

        p_ = f[y, :]
        t_ = comp(p_)  # lateral pixel comp
        _vP_, _dP_ = ycomp(t_, _t_, _vP_, _dP_) # vertical pixel comp, P and P2 form
        _t_ = t_

        P2_ = _vP2_, _dP2_  # arrays of blobs terminated per line, adjusted by term_P2
        frame_.append(P2_)  # line of patterns is added to frame of patterns
        _vP2_, _dP2_ = [],[]

    return frame_  # frame of 2D patterns is output to level 2

f = misc.face(gray=True)  # input frame of pixels
f = f.astype(int)
level_1(f)

