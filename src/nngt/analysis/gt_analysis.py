#!/usr/bin/env python
#-*- coding:utf-8 -*-

""" Tools for graph analysis using the graph_tool library """

import scipy as sp
import scipy.sparse.linalg as spl

from nngt.globals import config, analyze_graph



#-----------------------------------------------------------------------------#
# Set the functions
#------------------------
#

adjacency = analyze_graph["adjacency"]
assort = analyze_graph["assortativity"]
edge_reciprocity = analyze_graph["reciprocity"]
global_clustering = analyze_graph["clustering"]
scc = analyze_graph["scc"]
wcc = analyze_graph["wcc"]
diameter = analyze_graph["diameter"]


#-----------------------------------------------------------------------------#
# Distributions
#------------------------
#

def degree_distrib(graph, deg_type="total", node_list=None, use_weights=True,
                   log=False, num_bins=30):
    '''
    Computing the degree distribution of a graphwork.
    
    Parameters
    ----------
    graph : :class:`~nngt.Graph` or subclass
        the graphwork to analyze.
    deg_type : string, optional (default: "total")
        type of degree to consider ("in", "out", or "total").
    node_list : list or numpy.array of ints, optional (default: None)
        Restrict the distribution to a set of nodes (default: all nodes).
    use_weights : bool, optional (default: True)
        use weighted degrees (do not take the sign into account: all weights
        are positive).
    log : bool, optional (default: False)
        use log-spaced bins.
    
    Returns
    -------
    counts : :class:`numpy.array`
        number of nodes in each bin
    deg : :class:`numpy.array`
        bins
    '''
    ia_node_deg = graph.get_degrees(node_list, deg_type, use_weights)
    ra_bins = sp.linspace(ia_node_deg.min(), ia_node_deg.max(), num_bins)
    if log:
        ra_bins = sp.logspace(sp.log10(sp.maximum(ia_node_deg.min(),1)),
                               sp.log10(ia_node_deg.max()), num_bins)
    counts,deg = sp.histogram(ia_node_deg, ra_bins)
    ia_indices = sp.argwhere(counts)
    return counts[ia_indices], deg[ia_indices]
            
def betweenness_distrib(graph, use_weights=True, log=False):
    '''
    Computing the betweenness distribution of a graphwork
    
    Parameters
    ----------
    graph : :class:`~nngt.Graph` or subclass
        the graphwork to analyze.
    use_weights : bool, optional (default: True)
        use weighted degrees (do not take the sign into account : all weights
        are positive).
    log : bool, optional (default: False)
        use log-spaced bins.
    
    Returns
    -------
    ncounts : :class:`numpy.array`
        number of nodes in each bin
    nbetw : :class:`numpy.array`
        bins for node betweenness
    ecounts : :class:`numpy.array`
        number of edges in each bin
    ebetw : :class:`numpy.array`
        bins for edge betweenness
    '''
    ia_nbetw, ia_ebetw = graph.get_betweenness(use_weights)
    num_nbins, num_ebins = int(len(ia_nbetw) / 50), int(len(ia_ebetw) / 50)
    ra_nbins = sp.linspace(ia_nbetw.min(), ia_nbetw.max(), num_nbins)
    ra_ebins = sp.linspace(ia_ebetw.min(), ia_ebetw.max(), num_ebins)
    if log:
        ra_nbins = sp.logspace(sp.log10(sp.maximum(ia_nbetw.min(),10**-8)),
                               sp.log10(ia_nbetw.max()), num_nbins)
        ra_ebins = sp.logspace(sp.log10(sp.maximum(ia_ebetw.min(),10**-8)),
                               sp.log10(ia_ebetw.max()), num_ebins)
    ncounts,nbetw = sp.histogram(ia_nbetw, ra_nbins)
    ecounts,ebetw = sp.histogram(ia_ebetw, ra_ebins)
    return ncounts, nbetw[:-1], ecounts, ebetw[:-1]


#-----------------------------------------------------------------------------#
# Scalar properties
#------------------------
#

def assortativity(graph, deg_type="total"):
    '''
    Assortativity of the graph.
    àtodo: check how the various libraries functions work.
    
    Parameters
    ----------
    graph : :class:`~nngt.Graph` or subclass
        Network to analyze.
    deg_type : string, optional (default: 'total')
        Type of degree to take into account (among 'in', 'out' or 'total').
    
    Returns
    -------
    a float describing the graphwork assortativity.
    '''
    if config["graph_library"] == "igraph":
        return graph._graph.assortativity_degree(graph.is_directed())
    elif config["graph_library"] == "graph_tool":
        return assort(graph._graph,"total")[0]
    else:
        return assort(graph._graph)

def reciprocity(graph):
    '''
    Returns the graphwork reciprocity, defined as :math:`E^\leftrightarrow/E`,
    where :math:`E^\leftrightarrow` and :math:`E` are, respectively, the number
    of bidirectional edges and the total number of edges in the graphwork.
    '''
    if config["graph_library"] == "igraph":
        return graph._graph.reciprocity()
    else:
        return edge_reciprocity(graph._graph)

def clustering(graph):
    '''
    Returns the global clustering coefficient of the graph, defined as
    
    .. math::
       c = 3 \times \frac{\text{number of triangles}}
                         {\text{number of connected triples}}
    '''
    if config["graph_library"] == "igraph":
        return graph._graph.transitivity_undirected()
    else:
        return global_clustering(graph)[0]

def num_iedges(graph):
    ''' Returns the number of inhibitory connections. '''
    num_einhib = len(graph["type"].a < 0)
    return float(num_einhib)/graph.edge_nb()

def num_scc(graph, listing=False):
    '''
    Returns the number of strongly connected components, i.e. ensembles where 
    all nodes inside the ensemble can reach any other node in the ensemble
    using the directed edges.
    
    See also
    --------
    num_wcc
    '''
    lst_histo = None
    if config["graph_library"] == "graph_tool":
        vprop_comp, lst_histo = scc(graph._graph,directed=True)
    elif config["graph_library"] == "igraph":
        lst_histo = graph._graph.clusters()
        lst_histo = [ cluster for cluster in lst_histo ]
    else:
        lst_histo = [ comp for comp in scc(graph._graph) ]
    if listing:
        return len(lst_histo), lst_histo
    else:
        return len(lst_histo)
        

def num_wcc(graph, listing=False):
    '''
    Connected components if the directivity of the edges is ignored (i.e. all 
    edges are considered as bidirectional).
    
    See also
    --------
    num_scc
    '''
    lst_histo = None
    if config["graph_library"] == "graph_tool":
        vprop_comp, lst_histo = wcc(graph._graph,directed=False)
    elif config["graph_library"] == "igraph":
        lst_histo = graph._graphclusters("WEAK")
        lst_histo = [ cluster for cluster in lst_histo ]
    else:
        lst_histo = [ comp for comp in wcc(graph._graph) ]
    if listing:
        return len(lst_histo), lst_histo
    else:
        return len(lst_histo)

def diameter(graph):
    ''' Pseudo-diameter of the graph @todo: weighted diameter'''
    if config["graph_library"] == "igraph":
        return graph._graph.diameter()
    elif config["graph_library"] == "networkx":
        return diameter(graph._graph)
    else:
        return diameter(graph._graph)[0]


#-----------------------------------------------------------------------------#
# Spectral properties
#------------------------
#

def spectral_radius(graph, typed=True, weighted=True):
    '''
    Spectral radius of the graph, defined as the eigenvalue of greatest module.
    
    Parameters
    ----------
    graph : :class:`~nngt.Graph` or subclass
        Network to analyze.
    typed : bool, optional (default: True)
        Whether the excitatory/inhibitory type of the connnections should be
        considered.
    weighted : bool, optional (default: True)
        Whether the weights should be taken into account.
    
    Returns
    -------
    the spectral radius as a float.
    '''
    weights = None
    if typed and "type" in graph.eproperties.keys():
        weights = graph.eproperties["type"].copy()
    if weighted and "weight" in graph.eproperties.keys():
        if weights is not None:
            weights = sp.multiply(weights,
                                  graph.eproperties["weight"])
        else:
            weights = graph.eproperties["weight"].copy()
    mat_adj = adjacency(graph,weights)
    eigenval = [0]
    try:
        eigenval = spl.eigs(mat_adj,return_eigenvectors=False)
    except spl.eigen.arpack.ArpackNoConvergence as err:
        eigenval = err.eigenvalues
    if len(eigenval):
        return sp.amax(sp.absolute(eigenval))
    else:
        raise spl.eigen.arpack.ArpackNoConvergence()

def adjacency_matrix(graph, types=True, weights=True):
    '''
    Adjacency matrix of the graph.
    
    Parameters
    ----------
    graph : :class:`~nngt.Graph` or subclass
        Network to analyze.
    types : bool, optional (default: True)
        Whether the excitatory/inhibitory type of the connnections should be
        considered (only if the weighing factor is the synaptic strength).
    weights : bool or string, optional (default: True)
        Whether weights should be taken into account; if True, then connections
        are weighed by their synaptic strength, if False, then a binary matrix
        is returned, if `weights` is a string, then the ponderation is the
        correponding value of the edge attribute (e.g. "distance" will return 
        an adjacency matrix where each connection is multiplied by its length).
    
    Returns
    -------
    a :class:`~scipy.sparse.csr_matrix`.
    '''
    return graph.adjacency_matrix(types, weights)
        
