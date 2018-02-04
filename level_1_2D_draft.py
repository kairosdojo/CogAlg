from scipy import misc
from collections import deque
import numpy as np

''' Level 1 with patterns defined by the sign of quadrant gradient: modified core algorithm of levels 1+2.

    Pixel comparison in 2D forms lateral and vertical derivatives: 2 matches and 2 differences per pixel. 
    They are formed on the same level because average lateral match ~ average vertical match.
    
    Pixels are discrete samples of continuous image, so rightward and downward derivatives per pixel are 
    equally representative samples of 0-90 degree quadrant gradient: minimal unique unit of 2D gradient. 
    Such gradient is computed as the average of these two orthogonally diverging derivatives.
   
    2D blobs are defined by same-sign quadrant gradient, of value for vP or difference for dP.
    Level 1 has 5 steps of encoding, incremental per line defined by vertical coordinate y:

    y:   comp(p_): lateral comp -> tuple t,
    y-1: ycomp(t_): vertical comp -> quadrant t2,
    y-1: form_P(t2_): lateral combination -> 1D pattern P,  
    y-2: form_P2(P_): vertical scan_P_, fork_eval, form_blob, comp_P, form_PP -> 2D P2, 
    y-3: term_P2(P2_): P2s are evaluated for termination, re-orientation, and re-consolidation 

    postfix '_' denotes array name, vs. same-name elements of that array 
    prefix '_' denotes higher-line variable or pattern
    
    Higher-line patterns include additional variables, derived during their run as lower-line patterns 
    All 2D functions (from ycomp, scan_P_, etc.) input two lines at once: relatively higher and lower ones.'''


def comp(p_):  # comparison of consecutive pixels within line forms tuples: pixel, match, difference

    t_ = []  # complete fuzzy tuples: summation range = rng
    it_ = deque(maxlen=rng)  # incomplete fuzzy tuples: summation range < rng

    for p in p_:
        index = 0

        for it in it_:  # incomplete tuples, with summation range from 0 to rng-1
            pri_p, fd, fm = it

            d = p - pri_p  # difference between pixels
            m = min(p, pri_p)  # match between pixels

            fd += d  # fuzzy d: sum of ds between p and all prior ps within it_
            fm += m  # fuzzy m: sum of ms between p and all prior ps within it_

            it = pri_p, fd, fm
            it_[index] = it
            index += 1

        if len(it_) == rng:

            t = pri_p, fd, fm
            t_.append(t)  # completed tuple is transferred from it_ to t_

        it = p, 0, 0  # fd and fm are directional, initialized per new p
        it_.appendleft(it)  # new prior tuple

    t_ += it_  # last number = rng of tuples that remain incomplete
    return t_


def ycomp(t_, t2__, _vP_, _dP_):  # vertical comparison between pixels, forms 2D t2: p, d, dy, m, my

    vP_, dP_, valt_, dalt_ = [],[],[],[]  # append by form_P, alt_-> alt2_, packed in scan_P_

    vP = 0,0,0,0,0,0,0,0,[]  # pri_s, I, D, Dy, M, My, G, alt_rdn, e_
    dP = 0,0,0,0,0,0,0,0,[]  # pri_s, I, D, Dy, M, My, G, alt_rdn, e_

    x = 0; alt = 0,0,0  # alt_len, alt_vG, alt_dG: overlap between current vP and dP
    new_t2__ = []  # t2_ buffer: 2D array
    
    for t, t2_ in zip(t_, t2__):  # compares vertically consecutive pixels, forms quadrant gradients

        p, d, m = t
        index = 0
        x += 1

        for t2 in t2_:
            pri_p, _d, fdy, _m, fmy = t2

            dy = p - pri_p  # vertical difference between pixels
            my = min(p, pri_p)  # vertical match between pixels

            fdy += dy  # fuzzy dy: sum of dys between p and all prior ps within t2_
            fmy += my  # fuzzy my: sum of mys between p and all prior ps within t2_

            t2 = pri_p, _d, fdy, _m, fmy
            t2_[index] = t2
            index += 1

        if len(t2_) == rng: # 2D tuple is completed and moved from t2_ to form_P:

            dg = _d + fdy  # d gradient
            vg = _m + fmy - ave  # v gradient
            t2 = pri_p, _d, fdy, _m, fmy  # 2D tuple

            # form 1D value pattern vP: horizontal span of same-sign vg s with associated vars:

            sv, alt, valt_, dalt_, vP, dP, vP_, _vP_ = \
            form_P(1, t2, vg, dg, alt, valt_, dalt_, vP, dP, vP_, _vP_, x)

            # form 1D difference pattern dP: horizontal span of same-sign dg s, associated vars:

            sd, alt, dalt_, valt_, dP, vP, dP_, _dP_ = \
            form_P(0, t2, dg, vg, alt, dalt_, valt_, dP, vP, dP_, _dP_, x)

        t2 = p, d, 0, m, 0  # fdy and fmy are initialized at 0
        t2_.appendleft(t2)  # new prior tuple is added to t2_, replaces completed one
        new_t2__.append(t2_)
        
    # line ends, alt term, vP term, dP term, no init, inclusion per incomplete lateral fd and fm:

    if alt[0]: # or if and (vP, dP): vP x dP overlap?

        dalt_.append(alt); valt_.append(alt)
        alt_len, alt_vG, alt_dG = alt  # same for vP and dP, incomplete vg - ave / (rng / X-x)?

        if alt_vG > alt_dG:  # comp of alt_vG to alt_dG, == goes to alt_P or to vP: primary?
            vP = list(vP); vP[7] += alt_len  # redundant overlap of lesser-oG- vP or dP
        else:
            dP = list(dP); dP[7] += alt_len  # rdn ratio = alt_rdn / len(e_), not P[8] /= P[7]

    if y + 1 > rng:  # starting with the first line of complete t2s

        vP_, _vP_ = scan_P_(0, vP, valt_, vP_, _vP_, x)  # empty _vP_
        dP_, _dP_ = scan_P_(1, dP, dalt_, dP_, _dP_, x)  # empty _dP_

    return new_t2__, vP_, dP_  # extended in scan_P_, renamed as arguments _vP_, _dP_

    # P_ redefined as np.array ([P, alt_, roots, fork_P2s]): to increment without init?
    # P2: 0,0,0,0,0,0,0,[],0,[]: L2, G2, I2, D2, Dy2, M2, My2, alt2_, rdn2, Py_?


def form_P(typ, t2, g, alt_g, alt, alt_, _alt_, P, alt_P, P_, _P_, x):  # forms 1D dP or vP

    p, d, dy, m, my = t2  # 2D tuple of quadrant variables per pixel
    pri_s, I, D, Dy, M, My, G, alt_rdn, e_ = P

    if typ:
        alt_len, oG, alt_oG = alt  # overlap between current vP and dP, accumulated in ycomp,
    else:
        alt_len, alt_oG, oG = alt  # -> P2 alt_rdn2, generic 1D ave *= 2: low variation?

    s = 1 if g > 0 else 0
    if s != pri_s and x > rng + 2:  # P (span of same-sign gs) is terminated

        if alt_oG > oG:  # comp of olp_vG to olp_dG, == goes to alt_P or to vP: primary pattern?
            alt_rdn += alt_len
        else:
            alt_P[7] += alt_len  # redundant overlap in weaker-oG- vP or dP, at either-P term
            # converted to list, else full unpack / repack: no assign to tuple?

        P = pri_s, I, D, Dy, M, My, G, alt_rdn, e_ # -> alt_rdn2, no A = ave * alt_rdn / e_: dA < cost?
        P_, _P_ = scan_P_(typ, P, alt_, P_, _P_, x)  # scan over contiguous higher-level _Ps

        alt = alt_P, alt_len, oG, alt_oG  # or P index len(P_): faster than P?  for P eval in form_blob
        alt_.append(alt)

        _alt = P, alt_len, alt_oG, oG  # redundant olp repr in concurrent alt_P, formed by terminated P
        _alt_.append(_alt)

        I, D, Dy, M, My, G, alt_rdn, e_, alt_ = 0,0,0,0,0,0,0,[],[]  # P and alt_ initialization
        alt_len, oG, alt_oG = 0,0,0  # alt initialization

    # continued or initialized vars are accumulated:

    alt_len += 1  # alt P overlap: alt_len, oG, alt_oG are accumulated until either P or _P terminates
    oG += g; alt_oG += alt_g

    I += p    # pixels summed within P
    D += d    # lateral D, for P comp and P2 orientation
    Dy += dy  # vertical D, for P2 normalization
    M += m    # lateral D, for P comp and P2 orientation
    My += my  # vertical M, for P2 orientation
    G += g    # d or v gradient summed to define P value, or V = M - 2a * W?

    if typ:
        pri = p, g, alt_g  # g = v gradient
        e_.append(pri)  # pattern element: prior same-level quadrant, for selective incremental range
    else:
        e_.append(g)  # g = d gradient and pattern element, for selective incremental derivation

    P = s, I, D, Dy, M, My, G, alt_rdn, e_  # incomplete P
    alt = alt_len, oG, alt_oG  # overlap to stronger alt-type P

    return s, alt, alt_, _alt_, P, alt_P, P_, _P_  # alt_ and _alt_ are accumulated in ycomp per line


def scan_P_(typ, P, alt_, P_, _P_, x):  # P scans overlapping _Ps in _P_ for inclusion into attached P2s

    A = ave  # initialization before accumulation per rdn fork, cached | in P, no component adjust?
    buff_ = [] # _P_ buffer for next P; alt_ -> rolp, alt2_ -> rolp2

    fork_, fork_vP_, fork_dP_ = deque(),deque(),deque()  # refs per P to compute and transfer forks
    s, I, D, Dy, M, My, G, alt_rdn, e_ = P  # alt_rdn = ratio of 1D overlap by stronger alt Ps

    ix = x - len(e_)  # initial x of P
    _ix = 0  # initialized ix of _P displaced from _P_ by last scan_P_

    while x >= _ix:  # P to _P match eval, while horizontal overlap between P and _P_:

        fork_oG = 0  # fork overlap gradient: oG += g
        ex = x  # ex is lateral coordinate of loaded P element

        _P = _P_.popleft()
        # _P = _P, _alt_, roots, forks
        # _P = _s, _ix, _x, _I, _D, _Dy, _M, _My, _G, _alt_rdn, _e_ # or tuple rdn?

        if P[0] == _P[0][0]:  # if s == _s: vg or dg sign match

            while ex > _P[0][1]: # _ix = _P[0][1]
        
                for e in e_:  # oG accumulation per P (PM, PD from comp_P only)

                    if typ: fork_oG += e[1]  # if vP: e = p, g, alt_g
                    else: fork_oG += e  # if dP: e = g
                    ex += 1

            fork = fork_oG, _P  # or PM, PD in comp_P, vs. re-packing _P, rdn = sort order
            fork_.append(fork)  # _P inclusion in P

            _P[2][0].append(P)  # root_.append(P), to track continuing roots in form_PP

        if _P[0][2] > ix:  # if _x > ix:
            buff_.append(_P)  # _P is buffered for next-P comp

        else:  # no horizontal overlap between _P and next P, _P is removed from _P_

            if (_P[2][0] == 0 and y > rng + 3) or y == Y - 1:  # P2 term if root_== 0

                blob_ = _P[2][2]
                for blob in blob_:

                    blob, _vPP, _dPP = blob  # <= one _vPP and _dPP per higher-level blob
                    term_P2(blob, A)  # eval for 2D P re-orient and re-scan, then recursion

                    if _vPP: term_P2(_vPP, A)  # if comp_P in fork_eval(blob)
                    if _dPP: term_P2(_dPP, A)  # not for _dPP in _dPP_: only to eval for rdn?

    P = s, ix, x, I, D, Dy, M, My, G, alt_rdn, e_, alt_  # no x overlap between P and next _P

    if len(fork_):  # P is evaluated for inclusion into its fork _Ps on a higher line (y-1)

        bA = A  # P eval for _P blob inclusion and comp_P
        fork_, bA = fork_eval(2, P, fork_, bA, x)  # bA *= blob rdn

        if fork_vP_: # lateral len(dPP_): from comp_P over same forks, during fork_eval of blob_

            vA = bA  # eval for inclusion in vPPs (2D value patterns), rdn alt_ = blobs:
            fork_vP_, vA = fork_eval(0, P, fork_vP_, vA, x)

            dA = vA  # eval for inclusion in dPPs (2D difference patterns), rdn alt_ = vPPs:
            fork_dP_, dA = fork_eval(1, P, fork_dP_, dA, x)

            # individual vPPs and dPPs are also modified in their fork

    roots = [],[],[]  # root_, root_vP_, root_dP_ for displaced _P term eval and P2 initialization
    forks = fork_, fork_vP_, fork_dP_  # current values, each has blob, init unless passed down?

    P = P, roots, forks  # bA, vA, dA per fork rdn, one inclusion per root
    P_.append(P)  # _P_ = P_ for next-line scan_P_()
    buff_ += _P_  # excluding displaced _Ps

    return P_, buff_  # _P_ = buff_ for scan_P_(next P)

    # y-1 P = P, fork_Ps, -> _P at _P_ scan end
    # y-2 _P = P, roots, fork_P2s, -> old | ini P2 at P_ scan end
    # y-3 __P = P2, roots, fork_seg_P2s, -> seg_P2 if root_>1 | term_P2 if root_=0:
    # y-4+: layers of segmented P2s, terminated if full root_-> term_, full term at last contin_P


def fork_eval(typ, P, fork_, A, x):  # _Ps eval for form_blob, comp_P, form_PP

    # fork = crit, _P; _P = _P, roots, fork_P2s
    # _P = _s, _ix, _x, _I, _D, _Dy, _M, _My, _G, _rdn, _e_, _alt_; same as P?
    # alt, rdn, A = rdn

    ini = 1; select_ = deque()
    fork_.sort(key = lambda fork: fork[0])  # max-to-min crit, or sort and select at once:

    while fork_ and (crit > A or ini == 1):  # _P -> P2 inclusion if contiguous sign match

        ini = 0
        fork = fork_.pop() # _P: fork | vPP | dPP
        crit, fork = fork  # criterion: oG for blob, PM for vPP, PD for dPP

        fA = A * (1 + P[9][0] / P[10])  # rolp: 1 + alt_rdn / len(e_), indiv P adjust < cost?
        fork = fA, fork

        select_.appendleft(fork)
        A += A  # or olp_rdn += 1, then A * comb rdn: local and adjustable by hLe selection?

    init = 0 if len(select_) == 1 else 1
    for fork in select_:

        if typ == 2:  # fork = blob

            fork = form_blob(P, fork, init)  # crit is summed in _G, alt_rdn in fA?
            P_ders = comp_P(P, fork, x)  # comp_P if form_blob?
            P = P, P_ders

        else:
            fork = form_PP(typ, P, P_ders, fork, init)  # fork = vPP or dPP, known olp, no form at comp_P

        fork_.appendleft(fork)  # not-selected forks are out of fork_, don't increment root_

    return fork_  # A or rdn is packed for higher P2-type accumulation?


def form_blob(P, fork, init):  # P inclusion into blob (initialized or continuing) of selected fork

    _P, roots, fork_P2s = fork
    blob_ = fork_P2s[0]  # P2: blob | vPP | dPP
    s, ix, x, I, D, Dy, M, My, G, rdn, e_, alt_ = _P  # alt_ is packed, rdn = alt_rdn, blob_rdn, A?

    if init:  # fork_P2s are neither extended nor terminated

        L2 = len(e_)  # no separate e2_: Py_( P( e_? overlap / comp_P only?
        I2 = I
        D2 = D; Dy2 = Dy
        M2 = M; My2 = My
        G2 = G  # oG: vertical contiguity for fork_eval, also for comp_P?
        rdn2 = rdn    # alt_rdn, not fA or rdn_fork?
        alt2_ = []; alt2_.append(alt_)  # or replaced by alt_blob_?
        Py_ = []; Py_.append(_P)  # vertical array of patterns within a blob

        blob = L2, I2, D2, Dy2, M2, My2, G2, rdn2, alt2_, Py_
        blob_ = blob,  # single fork blob?

    else:  # single fork continues, max fork if multi-A select?

        L2, I2, D2, Dy2, M2, My2, G2, rdn2, alt2_, Py_ = blob_[0]

        L2 += len(e_)
        I2 += I
        D2 += D; Dy2 += Dy
        M2 += M; My2 += My
        G2 += G
        alt2_ += alt_
        rdn2 += rdn
        Py_.append(_P)

        blob_[0] = L2, G2, I2, D2, Dy2, M2, My2, alt2_, rdn2, Py_  # tuple assignment?

    fork_P2s[0] = blob_
    fork = P, roots, fork_P2s  # P is replacing _P, which was summed into P2

    return fork


def comp_P(P, _P, x):  # forms vertical derivatives of P vars, also from conditional DIV comp

    s, I, D, Dy, M, My, G, rdn, e_, alt_ = P  # select alt_ per fork, no olp: = mx? no oG: fork sel
    _s, _ix, _x, _I, _D, _Dy, _M, _My, _G, _rdn, _e_, _alt_ = _P

    ddx = 0  # optional, 2Le norm / D? s_ddx and s_dL correlate, s_dx position and s_dL dimension don't?
    ix = x - len(e_)  # initial coordinate of P; S is generic for summed vars I, D, M:

    dx = x - len(e_)/2 - _x - len(_e_)/2  # Dx? comp(dx), ddx = Ddx / h? dS *= cos(ddx), mS /= cos(ddx)?
    mx = x - _ix; if ix > _ix: mx -= ix - _ix  # mx = x olp, - a_mx -> vxP, distant P mx = -(a_dx - dx)?

    dL = len(e_) - len(_e_); mL = min(len(e_), len(_e_))  # relative olp = mx / L? ext_miss: Ddx + DL?
    dI = I - _I; mI = min(I, _I)
    dD = D - _D; mD = min(D, _D)
    dM = M - _M; mM = min(M, _M)  # no G comp: y-derivatives are incomplete, no alt_ comp: rdn only?

    Pd = ddx + dL + dI + dD + dM  # defines dPP; var_P form if PP form, term if var_P or PP term;
    Pm = mx + mL + mI + mD + mM   # defines vPP; comb rep value = Pm * 2 + Pd? group by y_ders?

    if dI * dL > div_a: # DIV comp: cross-scale d, neg if cross-sign, nS = S * rL, ~ rS,rP: L defines P

        rL = len(e_) / len(_e_)  # L defines P, SUB comp of rL-normalized nS:
        nI = I * rL; ndI = nI - _I; nmI = min(nI, _I)  # vs. nI = dI * nrL?
        nD = D * rL; ndD = nD - _D; nmD = min(nD, _D)
        nM = M * rL; ndM = nM - _M; nmM = min(nM, _M)

        Pnm = mx + nmI + nmD + nmM  # normalized m defines norm_vPP, as long as rL is computed
        if Pm > Pnm: nvPP_rdn = 1; vPP_rdn = 0 # added to rdn, or diff alt, olp, div rdn?
        else: vPP_rdn = 1; nvPP_rdn = 0

        Pnd = ddx + ndI + ndD + ndM  # normalized d defines norm_dPP or ndPP
        if Pd > Pnd: ndPP_rdn = 1; dPP_rdn = 0  # value = D | nD
        else: dPP_rdn = 1; ndPP_rdn = 0

        div_f = 1
        nvars = Pnm, nmI, nmD, nmM, vPP_rdn, nvPP_rdn, \
                Pnd, ndI, ndD, ndM, dPP_rdn, ndPP_rdn

    else:
        div_f = 0  # DIV comp flag
        nvars = 0  # DIV + norm derivatives

    ''' 
    no DIV comp(L): match is insignificant and redundant to mS?
    if dL: nL = len(e_) // len(_e_)  # L match = min L mult
    else: nL = len(_e_) // len(e_)
    fL = len(e_) % len(_e_)  # miss = remainder 
    
    form_PP at fork_eval after full rdn: A = a * alt_rdn * fork_rdn * norm_rdn, 
    form_pP (parameter pattern) in +vPPs only, then cost of adjust for pP_rdn?
    
    comp_P is not fuzzy: x & y vars are already fuzzy?  
    eval per fork, PP, or yP, not per comp

    no comp aS: m_aS * rL cost, minor cpr / nL? no DIV S: weak nS = S // _S; fS = rS - nS  
    or aS if positive eV (not eD?) = mx + mL -ave:
    
    aI = I / len(e_); dI = aI - _aI; mI = min(aI, _aI)  
    aD = D / len(e_); dD = aD - _aD; mD = min(aD, _aD)  
    aM = M / len(e_); dM = aM - _aM; mM = min(aM, _aM)

    d_aS comp if cs D_aS, _aS is aS stored in _P, S preserved to form hP SS?
    iter dS - S -> (n, M, diff): var precision or modulus + remainder? '''

    P_ders = Pd, Pm, mx, dx, mL, dL, mI, dI, mD, dD, mM, dM, div_f, nvars

    return P_ders  # for inclusion in vPP_, dPP_ by form_PP in fork_eval, P -> P_ in scan_P_


def form_PP(typ, P, P_ders, fork, init):  # forms vPPs, dPPs, and their pPs

    PP, roots, forks = fork
    s, ix, x, I, D, Dy, M, My, G, rdn, e_, alt_ = P
    Pd, Pm, mx, dx, mL, dL, mI, dI, mD, dD, mM, dM, div_f, nvars = P_ders

    if typ: crit = Pm  # total match per pattern
    else: crit = Pd / 2  # total difference per pattern: range = m_range / 2?

    if crit > ave * 5 * rdn:  # comp cost, or * number of vars per P: rep cost?

        if init:  # new PP initialization:

            L2 = len(e_); I2 = I; D2 = D; Dy2 = Dy; M2 = M; My2 = My; G2 = G; rdn2 = rdn; alt2_ = alt_
            Py_ = []; Py_.append(P)
            root_ = []; root_.append(P)

        else:  # increments current PP

            crit, rdn, L2, I2, D2, Dy2, M2, My2, G2, rdn2, alt2_, Py_, root_ = PP

            L2 += len(e_); I2 += I; D2 += D; Dy2 += Dy; M2 += M; My2 += My; G2 += G
            rdn_contents = rdn  # alt and olp?

            alt2_.append(alt_); Py_.append(P)
            root_.append(P)  # connected Ps in future blob_ and _P2_

    # a_mx = 2; a_mw = 2; a_mI = 256; a_mD = 128; a_mM = 128: feedback to define vpPs: parameter value patterns
    # a_PM = a_mx + a_mw + a_mI + a_mD + a_mM  or A * n_vars, rdn accum per pP, alt eval per vertical overlap?

    # LIDV per dx, L, I, D, M? select per term?
    # alt2_: fork_ alt_ concat, to re-compute redundancy per PP

    ''' PP = PP, root_, blob_, _vPP_, _dPP_?
    s, ix, x, I, D, Dy, M, My, G, r, e_, alt_ = P: no inclusion of last input?

    vPP and dPP included in selected forks, rdn assign and form_PP eval after fork_ term in form_blob?

    blob= 0,0,0,0,0,0,0,0,0,0,[],[]  # crit, rdn, W, I2, D2, Dy2, M2, My2, G2, rdn2, alt2_, Py_
    vPP = 0,0,0,0,0,0,0,0,0,0,[],[]
    dPP = 0,0,0,0,0,0,0,0,0,0,[],[]  # P2s are initialized at non-matching P transfer to _P_?

    np.array for direct accumulation, or simply iterator of initialization?

    P2_ = np.array([blob, vPP, dPP],
        dtype=[('crit', 'i4'), ('rdn', 'i4'), ('W', 'i4'), ('I2', 'i4'), ('D2', 'i4'), ('Dy2', 'i4'),
        ('M2', 'i4'), ('My2', 'i4'), ('G2', 'i4'), ('rdn2', 'i4'), ('alt2_', list), ('Py_', list)]) 
    '''

    PP = L2, I2, D2, Dy2, M2, My2, G2, rdn2, alt2_, Py_  # also len(_P_): _P index?
    return PP


def term_P2(P2, A):  # blob | vPP | dPP eval for rotation, re-scan, re-comp, recursion, accumulation

    P2_ = []
    ''' 
    conversion of root to term, sum into wider fork, also sum per frame?
    
    dimensionally reduced axis: vP PP or contour: dP PP; dxP is direction pattern

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


def root_2D(f):  # postfix '_' denotes array vs. element, prefix '_' denotes higher-line variable

    global rng; rng = 1
    global ave; ave = 127  # filters, ultimately set by separate feedback, then ave *= rng
    global div_a; div_a = 127  # not justified

    global _vP2_; _vP2_ = []
    global _dP2_; _dP2_ = []  # 2D Ps terminated on line y-3
    _vP_, _dP_, frame_ = [], [], []

    global Y; global X
    Y, X = f.shape  # Y: frame height, X: frame width
    global y; y = 0

    t2_ = deque(maxlen=rng)  # vertical buffer of incomplete pixel tuples, for fuzzy ycomp
    t2__ = []  # 2D (vertical buffer + horizontal line) array of 2D tuples, also deque for speed?
    p_ = f[0, :]  # first line of pixels
    t_ = comp(p_)

    for t in t_:
        p, d, m = t
        t2 = p, d, 0, m, 0  # fdy and fmy initialized at 0
        t2_.append(t2)  # only one tuple per first-line t2_
        t2__.append(t2_)  # in same order as t_

    for y in range(1, Y):  # vertical coordinate y is index of new line p_

        p_ = f[y, :]
        t_ = comp(p_)  # lateral pixel comparison
        t2__, _vP_, _dP_ = ycomp(t_, t2__, _vP_, _dP_) # vertical pixel comp, P and P2 form

        P2_ = _vP2_, _dP2_  # arrays of blobs terminated per line, adjusted by term_P2
        frame_.append(P2_)  # line of patterns is added to frame of patterns
        _vP2_, _dP2_ = [],[]

    return frame_  # frame of 2D patterns is outputted to level 2

f = misc.face(gray=True)  # input frame of pixels
f = f.astype(int)
root_2D(f)

