import sys
import numpy as np
from itertools import zip_longest
from copy import deepcopy, copy
from class_cluster import ClusterStructure, NoneType, comp_param, Cdert
import math as math
from comp_slice import *

'''
Blob edges may be represented by higher-composition patterns, etc., if top param-layer match,
in combination with spliced lower-composition patterns, etc, if only lower param-layers match.
This may form closed edge patterns around flat core blobs, which defines stable objects.   
'''

ave_G = 6  # fixed costs per G
ave_Gm = 5  # for inclusion in graph
ave_Gd = 4
G_aves = [ave_Gm, ave_Gd]
ave_med = 3  # call cluster_node_layer
ave_rng = 3  # rng per combined val


class Cgraph(CPP):  # graph or generic PP of any composition

    plevels = list  # max n ptuples / level = n ptuples in all lower layers: 1, 1, 2, 4, 8...
    # plevel_t[1]s is summed from alt_graph_, sub comp support, agg comp suppression?
    fds = list  # prior forks in plevels, then player fds in plevel
    valt = lambda: [0, 0]  # mval, dval from cis+alt forks
    nvalt = lambda: [0, 0]  # from neg open links
    rdn = int  # for PP evaluation, recursion count + Rdn / nderPs; no alt_rdn: valt representation in alt_PP_ valts?
    rng = lambda: 1  # not for alt_graphs
    link_ = list  # all evaluated external graph links, nested in link_layers? open links replace alt_node_
    node_ = list  # graph elements, root of layers and levels:
    rlayers = list  # | mlayers, top-down
    dlayers = list  # | alayers
    mlevels = list  # agg_PPs ) agg_PPPs ) agg_PPPPs.., bottom-up
    dlevels = list
    roott = lambda: [None, None]  # higher-order segG or graph
    alt_graph_ = list


def agg_recursion(root, G_, fseg, fsub):  # compositional recursion in root.PP_, pretty sure we still need fseg, process should be different

    ivalt = root.valt
    mgraph_, dgraph_ = form_graph_(root, G_, fsub)  # PP cross-comp and clustering

    # intra graph:
    if root.valt[0] > ave_sub * root.rdn:
        sub_rlayers, rvalt = sub_recursion_g(mgraph_, root.valt, fd=0)  # subdivide graph.node_ by der+|rng+, accum root.valt
        root.valt[0] += sum(rvalt); root.rlayers = sub_rlayers
    if root.valt[1] > ave_sub * root.rdn:
        sub_dlayers, dvalt = sub_recursion_g(dgraph_, root.valt, fd=1)
        root.valt[1] += sum(dvalt); root.dlayers = sub_dlayers

    # cross graph:
    root.mlevels += mgraph_; root.dlevels += dgraph_
    for fd, graph_ in enumerate([mgraph_, dgraph_]):
        adj_val = root.valt[fd] - ivalt[fd]
        # recursion if adjusted val:
        if (adj_val > G_aves[fd] * ave_agg * (root.rdn + 1)) and len(graph_) > ave_nsub:
            root.rdn += 1  # estimate
            agg_recursion(root, graph_, fseg=fseg, fsub=fsub)  # cross-comp graphs


def form_graph_(root, G_, fsub):  # G is potential node graph, in higher-order GG graph

    for G in G_:  # initialize mgraph, dgraph as roott per G, for comp_G_
        for i in 0,1:
            graph = [[G], [], [0,0]]  # proto-GG: [node_, meds_, valt]
            G.roott[i] = graph

    comp_G_(G_, fsub)  # cross-comp all graphs within rng, graphs may be segs
    mgraph_, dgraph_ = [],[]  # initialize graphs with >0 positive links in graph roots:
    for G in G_:
        if len(G.roott[0][0])>1: mgraph_ += [G.roott[0]]  # root = [node_, valt] for cluster_node_layer eval, + link_nvalt?
        if len(G.roott[1][0])>1: dgraph_ += [G.roott[1]]

    for fd, graph_ in enumerate([mgraph_, dgraph_]):  # evaluate intermediate nodes to delete or merge graphs:
        regraph_ = []
        while graph_:
            graph = graph_.pop(0)
            cluster_node_layer(graph_= graph_, graph=graph, fd=fd)
            if graph[2][fd] > ave_agg: regraph_ += [graph]  # graph reformed by merges and removes in cluster_node_layer

        if regraph_:
            graph_[:] = sum2graph_(regraph_, fd)  # sum proto-graph node_ params in graph
            plevels = deepcopy(graph_[0].plevels)
            for graph in graph_[1:]:
                sum_plevel_ts(plevels, graph.plevels)  # each plevel is plevel_t: (plevel, alt_plevel)
            root.plevels = plevels

    return mgraph_, dgraph_


def comp_G_(G_, fini):  # cross-comp Gs (patterns of patterns): Gs, derGs, or segs inside PP

    for i, _G in enumerate(G_):  # compare _G to other Gs in rng, bilateral link assign:
        for G in G_[i+1:]:
            if G in [node for link in _G.link_ for node in link.node_]:  # add frng to skip?
                continue  # in rng+, G may have been compared to _G in prior sub_recursion

            area = G.plevels[0][0][0][0][0].L; _area = _G.plevels[0][0][0][0][0].L  # 1st plevel_t' last fork' players' 1st player' 1st ptuple L
            dx = ((_G.xn - _G.x0) / 2) / _area - ((G.xn - G.x0) / 2) / area
            dy = ((_G.yn - _G.y0) / 2) / _area - ((G.yn - G.y0) / 2) / area
            distance = np.hypot(dy, dx)  # Euclidean distance between PP centroids
            # max distance depends on combined value:
            if distance <= ave_rng * ((sum(_G.valt)+sum(G.valt)) / (2*sum(G_aves))):
                if fini:
                    mplayers, dplayers, mvalt, dvalt = comp_plevel_t(_G.plevels, G.plevels)
                else:
                    mplayers, dplayers, mvalt, dvalt = comp_plevel_ts(_G.plevels, G.plevels)
                valt = [sum(mvalt) - ave_Gm, sum(dvalt) - ave_Gd]  # *= link rdn?
                fds = deepcopy(_G.plevels[-1][0][1])  # last plevel fds
                derG = Cgraph(
                    plevels = [[[mplayers,fds,mvalt], [dplayers,fds,dvalt]]], # single plevel_t, same fds
                    x0=min(_G.x0,G.x0), xn=max(_G.xn,G.xn), y0=min(_G.y0,G.y0), yn=max(_G.yn,G.yn), valt=valt, node_=[_G,G]
                    )
                _G.link_ += [derG]; G.link_ += [derG]  # of any val
                for fd in 0,1:
                    if valt[fd] > 0:  # alt fork is redundant, no support?
                        for node, (graph, meds_, gvalt) in zip([_G, G], [G.roott[fd], _G.roott[fd]]):  # bilateral inclusion
                            if node not in graph:
                                graph += [node]
                                meds_ += [[derG.node_[0] if derG.node_[1] is node else derG.node_[1] for derG in node.link_]]
                                gvalt[0] += node.valt[0]; gvalt[1] += node.valt[1]


def cluster_node_layer(graph_, graph, fd):  # recursive eval of mutual links in increasingly mediated nodes

    node_, meds_, valt = graph
    save_node_, save_meds_ = [], []
    adj_Val = 0

    for G, med_node_ in zip(node_, meds_):  # G: node or sub-graph
        mmed_node_ = []  # __Gs that mediate between Gs and _Gs
        for _G in med_node_:
            for derG in _G.link_:
                if derG not in G.link_:  # link_ includes all unique evaluated mediated links, flat or in layers?
                    # med_PP.link_:
                    med_link_ = derG.node_[0].link_ if derG.node_[0] is not _G else derG.node_[1].link_
                    for _derG in med_link_:
                        if G in _derG.node_ and _derG not in G.link_:  # __G mediates between _G and G
                            G.link_ += [_derG]
                            adj_val = _derG.valt[fd] - ave_agg  # or increase ave per mediation depth
                            # adjust nodes:
                            G.valt[fd] += adj_val; _G.valt[fd] += adj_val
                            valt[fd] += adj_val; _G.roott[fd][2][fd] += adj_val  # root is not graph yet
                            __G = _derG.node_[0] if _derG.node_[0] is not _G else _derG.node_[1]
                            if __G not in mmed_node_:  # not saved via prior _G
                                mmed_node_ += [__G]
                                adj_Val += adj_val
        if G.valt[fd]>0:
            # G remains in graph
            save_node_ += [G]; save_meds_ += [mmed_node_]  # mmed_node_ may be empty

    for G, mmed_ in zip(save_node_, save_meds_):  # eval graph merge after adjusting graph by mediating node layer
        add_mmed_= []
        for _G in mmed_:
            _graph = _G.roott[fd]
            if _graph in graph_ and _graph is not graph:  # was not removed or merged via prior _G
                _node_, _meds_, _valt = _graph
                for _node, _meds in zip(_node_, _meds_):  # merge graphs, ignore _med_? add direct links:
                    for derG in _node.link_:
                        __G = derG.node_[0] if derG.node_[0] is not _G else derG.node_[1]
                        if __G not in add_mmed_ + mmed_:  # not saved via prior _G
                            add_mmed_ += [__G]
                            adj_Val += derG.valt[fd] - ave_agg
                valt[fd] += _valt[fd]
                graph_.remove(_graph)
        mmed_ += add_mmed_

    node_[:] = save_node_; meds_[:] = save_meds_
    if adj_Val > ave_med:  # positive adj_Val from mmed_
        cluster_node_layer(graph_, graph, fd)  # eval next mediation layer in reformed graph


def sub_recursion_g(graph_, fseg, fd):  # rng+: extend G_ per graph, der+: replace G_ with derG_

    comb_layers_t = [[],[]]
    sub_valt = [0,0]
    for graph in graph_:
        if fd:
            node_ = []  # positive links within graph
            for node in graph.node_:
                for link in node.link_:
                    if link.valt[0]>0 and link not in node_:
                        node_ += [link]
        else: node_ = graph.node_
        # or if adj_val: top-level only?
        if graph.valt[fd] > G_aves[fd] and len(node_) > ave_nsub:

            sub_mgraph_, sub_dgraph_ = form_graph_(graph, node_, fsub=1)  # cross-comp and clustering cycle
            # rng+:
            if graph.valt[0] > ave_sub * graph.rdn:  # >cost of calling sub_recursion and looping:
                sub_rlayers, valt = sub_recursion_g(sub_mgraph_, graph.valt, fd=0)
                rvalt = sum(valt); graph.valt[0] += rvalt; sub_valt[0] += rvalt  # not sure
                graph.rlayers = [sub_mgraph_] + [sub_rlayers]
            # der+:
            if graph.valt[1] > ave_sub * graph.rdn:
                sub_dlayers, valt = sub_recursion_g(sub_dgraph_, graph.valt, fd=1)
                dvalt = sum(valt); graph.valt[1] += dvalt; sub_valt[1] += dvalt
                graph.dlayers = [sub_dgraph_] + [sub_dlayers]

            for comb_layers, graph_layers in zip(comb_layers_t, [graph.rlayers, graph.dlayers]):
                for i, (comb_layer, graph_layer) in enumerate(zip_longest(comb_layers, graph_layers, fillvalue=[])):
                    if graph_layer:
                        if i > len(comb_layers) - 1:
                            comb_layers += [graph_layer]  # add new r|d layer
                        else:
                            comb_layers[i] += graph_layer  # splice r|d PP layer into existing layer

    return comb_layers_t, sub_valt


def sum2graph_(G_, fd):  # sum node and link params into graph
    # fsub if from sub_recursion: add players vs. plevels?

    graph_ = []  # new graph_
    for G in G_:
        node_, meds_, valt = G
        link = node_[0].link_[0]
        link_ = [link]  # to avoid rdn
        graph = Cgraph(plevels=deepcopy(node_[0].plevels) + [[link.plevels[0][fd], []]], # init plevels: 1st node, link, empty alt
                       x0=node_[0].x0, xn=node_[0].xn, y0=node_[0].y0, yn=node_[0].yn,
                       fds=deepcopy(node_[0].fds+[fd]), node_ = node_, meds_ = meds_)
        for node in node_:
            graph.valt[0] += node.valt[0]; graph.valt[1] += node.valt[1]
            graph.x0=min(graph.x0, node.x0)
            graph.xn=max(graph.xn, node.xn)
            graph.y0=min(graph.y0, node.y0)
            graph.yn=max(graph.yn, node.yn)
            # accum params:
            if node is node_[0]:
                continue
            sum_plevel_ts(graph.plevels[:-1], node.plevels)
            for derG in node.link_:  # accum derG in new level
                if derG in link_:
                    continue
                # i think this need depend on fsub? plevels's players could be players or players_t
                # so it will be sum_plevel here, and sum_players or sum_player_ts will be depend on fsub inside the sum_plevel
                sum_player_ts(graph.plevels[-1][0], derG.plevels[0][fd])  # sum last plevel_t[0] only
                valt[0] += derG.valt[0]; valt[1] += derG.valt[1]
                derG.fds = [fd]
                derG.roott[fd] = graph
                link_ = [derG]

        graph_ += [graph]

    for graph in graph_:  # 2nd pass to accum alt_graph params
        for node in graph.node_:
            for derG in node.link_:
                for G in derG.node_:
                    if G not in graph.node_:  # alt graphs are roots of not-in-graph G in derG.node_
                        alt_graph = G.roott[fd]
                        if alt_graph not in graph.alt_graph_ and isinstance(alt_graph, Cgraph):  # not proto-graph
                            sum_player_ts(graph.plevels[-1][1], alt_graph.plevels[-1][0])
                            graph.alt_graph_ += [alt_graph]
    return graph_


def comp_plevel_ts(_plevels, plevels):

    mplevel_t, dplevel_t = [],[]  # output
    mValt, dValt = [0,0], [0,0]

    for _plevel_t, plevel_t in zip(_plevels, plevels):
        mplevel, dplevel = [], []  # each is cis,alt tuple

        for alt, (_plevel, plevel) in enumerate(zip(_plevel_t, plevel_t)):
            # cis | alt fork:
            if _plevel and plevel:
                _players, _fds, _valt = _plevel; players, fds, valt = plevel
                if len(players) == 2:
                    mplayers, dplayers, mval, dval = comp_player_ts(_players, players, _fds, fds)
                else: mplayers, dplayers, mval, dval = comp_players(_players, players, _fds, fds)

                mplevel += [mplayers, fds, mval]; dplevel += [dplayers, fds, dval]  # each is cis,alt tuple
                mValt[alt] += mval; dValt[alt] += dval
            else:
                mplevel += []; dplevel += []   # not sure

        mplevel_t += [mplevel]; dplevel_t += [dplevel]

    return mplevel_t, dplevel_t, mValt, dValt

# if fini:
def comp_plevel_t(_plevel_t, plevel_t):
    # plevel is fd tuple in derG if der+ or alt tuple in 1-plevel PP'G if initial rng+

    mplayers_t, dplayers_t = [],[]
    mvalt, dvalt = [], []

    for (_players, _fds, _valt), (players, fds, valt) in zip(_plevel_t, plevel_t):
        if len(players)==2:
            mplayers, dplayers, mval, dval = comp_player_ts(_players, players, _fds, fds)
        else: mplayers, dplayers, mval, dval = comp_players(_players, players, _fds, fds)

        mplayers_t += [mplayers]; dplayers_t += [dplayers]  # or combined into flat lists?
        mvalt += [mval]; dvalt += [dval]

    return mplayers_t, dplayers_t, mvalt, dvalt


def comp_plevel(_plevel, plevel, mValt, dValt):  # each unpacked plevel is nested as derivatives from comp in prior agg+

    new_players = [[]]  # single taken fd fork per input level per agg+
    mValt, dValt = [0, 0], [0, 0]

    for nderT, (_der_plevel, der_plevel) in enumerate(zip(reversed(_plevel), reversed(plevel))):  # nderT: n ders of lower agg levels

        while nderT:  # recursively unpack ders per per lower agg level
            for _der_pplevel, der_pplevel in zip(_der_plevel, der_plevel):
                nderT -= 1
                # add packing: new_players[fd] += [], we get [],[],[].., then use it as indices?

        mplayer, dplayer = comp_players(_der_pplevel, der_pplevel, mValt, dValt)
        # as below but we need to unpack naltT per player first:
        # not updated:
        for i, ((_players, _fds, _valt), (players, fds, valt)) in enumerate(zip(_plevel, plevel)):
            mplayers, dplayers, mval, dval = comp_players(_players, players, _fds, fds)
            plevels_[0] += [[[mplayers], _fds, [mval, dval]]]  # m fork output, will be selected in sum2graph based on fd
            plevels_[1] += [[[dplayers], _fds, [mval, dval]]]  # d fork output, will be selected in sum2graph based on fd
            if i % 2: dValt[0] += mval; dValt[1] += dval  # odd index is d fork
            else:     mValt[0] += mval; mValt[1] += dval

    return plevels_


def comp_player_ts(_players, players, _fds, fds):  # unpack and compare der layers, if any from der+

    mplayer_ts, dplayer_ts = [[],[]], [[],[]]  # flat lists of ptuples, nesting decoded by mapping to lower levels
    mval, dval = 0, 0

    for _player_t, player_t, _fd, fd in zip(_players, players, _fds, fds):
        if _fd==fd:
            mplayer_t, dplayer_t = [],[]
            for _player, player in zip(_player_t, player_t):
                # cis|alt
                if _player and player:  # alt_players may be empty
                    mplayer, dplayer = [],[]
                    for _ptuple, ptuple in zip(_player, player):

                        mtuple, dtuple = comp_ptuple(_ptuple, ptuple)
                        mplayer += [mtuple]; dplayer += [dtuple]
                        mval += mtuple.val; dval += dtuple.val

                    mplayer_t += [mplayer]; dplayer_t += [dplayer]
            mplayer_ts += [mplayer_t]; dplayer_ts += [dplayer_t]
        else:
            break  # only same-fd players are compared

    return mplayer_ts, dplayer_ts, mval, dval

# if len(players)!=2:
def comp_players(_layers, layers, _fds, fds):  # unpack and compare der layers, if any from der+

    mplayer, dplayer = [], []  # flat lists of ptuples, nesting decoded by mapping to lower levels
    mval, dval = 0, 0

    for _player, player, _fd, fd in zip(_layers, layers, _fds, fds):
        if _fd==fd:
            for _ptuple, ptuple in zip(_player, player):
                mtuple, dtuple = comp_ptuple(_ptuple, ptuple)
                mplayer += [mtuple]; mval = mtuple.val
                dplayer += [dtuple]; dval = dtuple.val
        else:
            break  # only same-fd players are compared

    return mplayer, dplayer, mval, dval


# summing part pending update
def sum_plevel_ts(pLevels, plevels):

    for pLevel_t, plevel_t in zip_longest(pLevels, plevels, fillvalue=[]):
        if plevel_t:  # plevel_t must not be empty list from zip_longest
            if pLevel_t:
                for pLevel, plevel in zip_longest(pLevel_t, plevel_t, fillvalue=[]):
                    # cis | alt forks
                    if plevel and plevel[0]:
                        if pLevel:
                            if pLevel[0]: sum_players(pLevel[0], plevel[0], pLevel[1], plevel[1])  # accum nodes' players
                            else:         pLevel[0] = deepcopy(plevel[0])  # append node's players
                            pLevel[1] = deepcopy(plevel[1])  # assign fds
                            pLevel[2][0] += plevel[2][0]
                            pLevel[2][1] += plevel[2][1]  # accumulate valt
                        else:
                            pLevel.append(deepcopy(plevel))  # pack new plevel
            else:  # pack new plevel_t
                pLevels.append(deepcopy(plevel_t))


def sum_player_ts(pLevel, plevel, fsub):

    if plevel and plevel[0]:
       if pLevel:
           _players, _fds, _valt = pLevel
           players, fds, valt = plevel
           sum_players(_players, players, _fds, fds)
           _valt[0] += valt[0]; _valt[1] += valt[1]
       else:
           pLevel[:] = deepcopy(plevel)


def sum_players(Layers, layers, Fds, fds, fneg=0):  # accum layers while same fds

    fbreak = 0
    for i, (Layer, layer, Fd, fd) in enumerate(zip_longest(Layers, layers, Fds, fds, fillvalue=[])):
        if layer:
            if Layer:
                if Fd == fd:
                    sum_player(Layer, layer, fneg=fneg)
                else:
                    fbreak = 1
                    break
            else:
                Layers.append(layer)
    Fds[:] = Fds[:i+1-fbreak]


# not revised, this is an alternative to form_graph, but may not be accurate enough to cluster:
def comp_centroid(PPP_):  # comp PP to average PP in PPP, sum >ave PPs into new centroid, recursion while update>ave

    update_val = 0  # update val, terminate recursion if low

    for PPP in PPP_:
        PPP_valt = [0 ,0]  # new total, may delete PPP
        PPP_rdn = 0  # rdn of PPs to cPPs in other PPPs
        PPP_players_t = [[], []]
        DerPP = CderG(player=[[], []])  # summed across PP_:
        Valt = [0, 0]  # mval, dval

        for i, (PP, _, fint) in enumerate(PPP.PP_):  # comp PP to PPP centroid, derPP is replaced, use comp_plevels?
            Mplayer, Dplayer = [],[]
            # both PP core and edge are compared to PPP core, results are summed or concatenated:
            for fd in 0, 1:
                if PP.players_t[fd]:  # PP.players_t[1] may be empty
                    mplayer, dplayer = comp_players(PPP.players_t[0], PP.players_t[fd], PPP.fds, PP.fds)  # params norm in comp_ptuple
                    player_t = [Mplayer + mplayer, Dplayer + dplayer]
                    valt = [sum([mtuple.val for mtuple in mplayer]), sum([dtuple.val for dtuple in dplayer])]
                    Valt[0] += valt[0]; Valt[1] += valt[1]  # accumulate mval and dval
                    # accum DerPP:
                    for Ptuple, ptuple in zip_longest(DerPP.player_t[fd], player_t[fd], fillvalue=[]):
                        if ptuple:
                            if not Ptuple: DerPP.player_t[fd].append(ptuple)  # pack new layer
                            else:          sum_players([[Ptuple]], [[ptuple]])
                    DerPP.valt[fd] += valt[fd]

            # compute rdn:
            cPP_ = PP.cPP_  # sort by derPP value:
            cPP_ = sorted(cPP_, key=lambda cPP: sum(cPP[1].valt), reverse=True)
            rdn = 1
            fint = [0, 0]
            for fd in 0, 1:  # sum players per fork
                for (cPP, CderG, cfint) in cPP_:
                    if valt[fd] > PP_aves[fd] and PP.players_t[fd]:
                        fint[fd] = 1  # PPs match, sum derPP in both PPP and _PPP:
                        sum_players(PPP.players_t[fd], PP.players_t[fd])
                        sum_players(PPP.players_t[fd], PP.players_t[fd])  # all PP.players in each PPP.players

                    if CderG.valt[fd] > Valt[fd]:  # cPP is instance of PP
                        if cfint[fd]: PPP_rdn += 1  # n of cPPs redundant to PP, if included and >val
                    else:
                        break  # cPP_ is sorted by value

            fnegm = Valt[0] < PP_aves[0] * rdn;  fnegd = Valt[1] < PP_aves[1] * rdn  # rdn per PP
            for fd, fneg, in zip([0, 1], [fnegm, fnegd]):

                if (fneg and fint[fd]) or (not fneg and not fint[fd]):  # re-clustering: exclude included or include excluded PP
                    PPP.PP_[i][2][fd] = 1 -  PPP.PP_[i][2][fd]  # reverse 1-0 or 0-1
                    update_val += abs(Valt[fd])  # or sum abs mparams?
                if not fneg:
                    PPP_valt[fd] += Valt[fd]
                    PPP_rdn += 1  # not sure
                if fint[fd]:
                    # include PP in PPP:
                    if PPP_players_t[fd]: sum_players(PPP_players_t[fd], PP.players_t[fd])
                    else: PPP_players_t[fd] = copy(PP.players_t[fd])  # initialization is simpler
                    # not revised:
                    PPP.PP_[i][1] = derPP   # no derPP now?
                    for i, cPPt in enumerate(PP.cPP_):
                        cPPP = cPPt[0].root
                        for j, PPt in enumerate(cPPP.cPP_):  # get PPP and replace their derPP
                            if PPt[0] is PP:
                                cPPP.cPP_[j][1] = derPP
                        if cPPt[0] is PP: # replace cPP's derPP
                            PPP.cPP_[i][1] = derPP
                PPP.valt[fd] = PPP_valt[fd]

        if PPP_players_t: PPP.players_t = PPP_players_t

        # not revised:
        if PPP_val < PP_aves[fPd] * PPP_rdn:  # ave rdn-adjusted value per cost of PPP

            update_val += abs(PPP_val)  # or sum abs mparams?
            PPP_.remove(PPP)  # PPPs are hugely redundant, need to be pruned

            for (PP, derPP, fin) in PPP.PP_:  # remove refs to local copy of PP in other PPPs
                for (cPP, _, _) in PP.cPP_:
                    for i, (ccPP, _, _) in enumerate(cPP.cPP_):  # ref of ref
                        if ccPP is PP:
                            cPP.cPP_.pop(i)  # remove ccPP tuple
                            break

    if update_val > sum(PP_aves):
        comp_centroid(PPP_)  # recursion while min update value

    return PPP_
'''
    1st and 2nd layers are single sublayers, the 2nd adds tuple pair nesting. Both are unpacked by func_pairs, not func_layers.  
    Multiple sublayers start on the 3rd layer, because it's derived from comparison between two (not one) lower layers. 
    4th layer is derived from comparison between 3 lower layers, where the 3rd layer is already nested, etc:
    initial 3-layer nesting: https://github.com/assets/52521979/ea6d436a-6c5e-429f-a152-ec89e715ebd6
'''

class CpHier(ClusterStructure):  # plevels | players

    plevels = list  # max cis+alt nesting per level = 2 ** n+1 higher levels: 2, 4, 8.., actual nesting is len(player)
    fds = list
    valt = lambda: [0, 0]  # mval, dval from cis+alt forks
    nvalt = lambda: [0, 0]  # from neg open links


def comp_plevels(_plevels, plevels):  # each packed plevel is nested as altT: variable-depth cis/alt tuple

    new_plevel = [[], []]
    mValt, dValt = [0,0], [0,0]
    # new_caTree = [[] for _ in range(depth + 1)]  # [],[],[]... to use as nested indices

    for naltT,(_iplevel, iplevel) in enumerate(zip( reversed(_plevels),reversed(plevels))):  # top-down depth increase

        _next_plevel, next_plevel = _iplevel, iplevel
        next_new_plevel = [ [[],[]] for _ in range(naltT+1)]
        if naltT == 0: new_plevel[:] = next_new_plevel[0]  # assign top new plevel

        while naltT:  # recursively unpack nested c/a tuple

            _plevel, plevel = copy(_next_plevel), copy(next_plevel)  # get prior next plevel as current plevel
            _next_plevel, next_plevel = [], []   # reset

            new_plevel = copy(next_new_plevel)  # get prior next new plevel as current new plevel
            next_new_plevel = []  # reset

            for alt, (_pplevel, pplevel, new_pplevel) in enumerate(zip(_plevel, plevel, new_plevel)):  # each plevel is plevel_t here for c|a fork?
                mplevel = []; dplevel = []
                new_pplevel[0] += [mplevel]; new_pplevel[1] += [dplevel]

                next_new_plevel += [[mplevel,dplevel]]  # mplevel and dplevel will be new_pplevel[0] and new_pplevel[1] of next level
                _next_plevel += [_pplevel]; next_plevel += [pplevel]  # pack to be checked in the next loop
            naltT -= 1

        else:
            for _pplevel, pplevel, new_pplevel in zip(_next_plevel, next_plevel, next_new_plevel):
                mplevel, dplevel = comp_plevel(_pplevel, _pplevel, mValt, dValt)
                new_pplevel[0] += [mplevel]; new_pplevel[1] += [dplevel]  # nested derivatives of all compared plevels

    return new_plevel, mValt, dValt  # always single new plevel

def sum_derG(plevels, lplevel, fd):

    plevels += lplevel[fd]

    for fdQueP, fdQuep in zip(CaTree, caTree):  # fdQuep is ca pair: leaf in implicit binary tree, nleaves = 2**depth
        for FdQue, fdQue in zip(FdQuep, fdQuep):  # cis fdQue | alt fdQue, alts may be empty
            if FdQue and fdQue:
                for Playerst, playerst in zip_longest(FdQue, fdQue, fillvalue=[]):
                    sum_playerst(Playerst, playerst)


def sum_playerst(pLayerst, playerst):  # accum layers while same fds

    pLayers, Fds, Valt = pLayerst
    players, fds, valt = playerst
    fbreak = 0

    for i, (pLayer, player, Fd, fd) in enumerate( zip_longest(pLayers, players, Fds, fds, fillvalue=[])):
        if Fd==fd:
            if fa:  # when pLayer is not converted to pLayerst yet
                if player and  pLayer:
                    if isinstance(player[0], Cptuple):
                        pLayers[i] = [pLayer, deepcopy(player)]  # player is not playerst, add alt part
                    else:
                        pLayers[i] = [pLayer, deepcopy(player[0])]  # player is playerst, add only playerst[0] as alt part

            elif player:
                if isinstance(player[0], Cptuple):  # playerst not converted to playerst yet
                    if pLayer:
                        if isinstance(pLayer[0], Cptuple):  # pLayerst not converted too
                            if pLayer:
                                sum_player(pLayer, player, fneg=0)
                            else:
                                pLayers+=[player]
                        else:
                            if pLayer[0]:
                                sum_player(pLayer[0], player, fneg=0)
                            else:
                                pLayers[0]+=[player]
                    # need to sum vals per player:
                    # Val, val in zip(Valt, valt): Val+=val?

                else:  # both converted to playerst
                    for ppLayer, pplayer in zip_longest(pLayer, player, fillvalue=[]):  # pLayer and player is playerst
                        if pplayer:
                            if ppLayer: sum_player(ppLayer, pplayer, fneg=0)
                            else:       ppLayers+=[pplayer]
        else:
            fbreak = 1
            break
    Fds[:] = Fds[:i + 1 - fbreak]

def fork_select(caTree, faTree, fa):

    if len(caTree) > 1:  # not leaf
        # split into cisT, altT:
        caT = [ caTree[:len(caTree)/2 +1], caTree[len(caTree)/2:] ]
        faTree += caT[fa]  # altT if fa else cisT
        fork_select(caT[not fa], faTree, fa)

    return faTree


def old_splice(cis, alt):  # recursive unpack and splice alt forks to extend (add?) list nesting:

    cQ, cvalt = cis
    if alt:
        aQ, avalt = alt
    else:
        aQ, avalt = [], 0

    # valt[0] += cval; valt[1] += aval
    for i, (cval, aval) in enumerate(zip(cvalt, avalt)): cval += aval

    cQ[:] = cQ, aQ  # this adds nesting, we need to keep it?
    if not isinstance(cQ[0], Cptuple):
        ca_splice(cQ, aQ)
    ''' 
    unpacked Cgraph.plevels: plevels ( caTree ( players ( caTree ( ptuples
    Ts have pair valt, Qs have single val?

        for (cTree, cvalt), (aTree, avalt) in zip(graph.plevels, Alt_plevels):
            cvalt[0] += avalt[0]; avalt[1] += avalt[1]
            cTree[:] = cTree, aTree
            for cplayerst, aplayerst in zip(cTree, aTree):
                if cplayerst: cplayers, cvalt = cplayerst
                else: cplayers = [], cvalt = [0,0]
                if aplayerst: aplayers, avalt = cplayerst
                else: aplayers = [], avalt = [0,0]
                cvalt[0] += avalt[0]; avalt[1] += avalt[1]
                cplayers[:] = cplayers, aplayers

                for (cT, cvalt), (aT, avalt) in zip(cplayers, aplayers):
                    cvalt[0] += avalt[0]; avalt[1] += avalt[1]
                    cT[:] = cT, aT
                    for cptuplest, aptuplest in zip(cTree, aTree):
                        if cptuplest: cptuples, cfds, cvalt = cptuplest
                        else: cptuples = [], cvalt = [0,0]
                        if aptuplest: aptuples, afds, avalt = cptuplest
                        else: aptuples = [], avalt = [0,0]
                        cvalt[0] += avalt[0]; avalt[1] += avalt[1]
                        cptuples[:] = cptuples, aptuples
    '''
def accum_ptuple(Ptuple, ptuple, fneg=0):  # lataple or vertuple

    for param_name in Ptuple.numeric_params:
        if param_name != "G" and param_name != "Ga":
            Param = getattr(Ptuple, param_name)
            param = getattr(ptuple, param_name)
            if fneg: out = Param-param
            else:    out = Param+param
            setattr(Ptuple, param_name, out)  # update value

    if isinstance(Ptuple.angle, list):
        for i, angle in enumerate(ptuple.angle):
            if fneg: Ptuple.angle[i] -= angle
            else:    Ptuple.angle[i] += angle
        for i, aangle in enumerate(ptuple.aangle):
            if fneg: Ptuple.aangle[i] -= aangle
            else:    Ptuple.aangle[i] += aangle
    else:
        if fneg: Ptuple.angle -= ptuple.angle; Ptuple.aangle -= ptuple.aangle
        else:    Ptuple.angle += ptuple.angle; Ptuple.aangle += ptuple.aangle

# ca_splice(graph.plevels, Alt_plevels)  # recursive unpack and splice alt forks
def ca_splice_deep(cQue, aQue):  # Que is plevels or players, unpack and splice alt forks in two calls
    fplayers=0

    for (cTree, cvalt), (aTree, avalt) in zip(cQue, aQue):
        cvalt[0] += avalt[0]; avalt[1] += avalt[1]
        cTree += cTree
        for cQt, aQt in zip(cTree, aTree):
            if cQt:
                if len(cQt) == 2: cQ, cvalt = cQt; fplayers = 1  # Q is players
                else:             cQ, cfds, cvalt = cQt  # Q is ptuples
            else: cQ=[], cvalt=[0,0]
            if aQt:
                if len(aQt) == 2: aQ, avalt = aQt
                else:             aQ, afds, avalt = cQt
            else: aQ=[], avalt=[0,0]

            cvalt[0] += avalt[0]; avalt[1] += avalt[1]
            cQ += aQ

            if fplayers:
                ca_splice(cQ, aQ)

def ca_splice(cQue, aQue):  # Que is plevels or players, unpack and splice alt forks in two calls

    for (cTree, cvalt), (aTree, avalt) in zip(cQue, aQue):
        cvalt[0] += avalt[0]; avalt[1] += avalt[1]
        cTree += aTree  # Tree is flat list, aQs remain packed in aTree?

