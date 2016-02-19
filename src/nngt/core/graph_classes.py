#!/usr/bin/env python
#-*- coding:utf-8 -*-

""" Graph classes for graph generation and management """

import warnings
from copy import deepcopy
import numpy as np
import scipy.sparse as ssp

from nngt.globals import (default_neuron, default_synapse, POS, WEIGHT, DELAY,
                       DIST, TYPE)
from nngt.core.graph_objects import GraphLib, GraphObject
from nngt.core.graph_datastruct import NeuralPop, Shape, Connections
import nngt.analysis as na
from nngt.lib import InvalidArgument


__all__ = [
    'Graph', 'SpatialGraph', 'Network', 'SpatialNetwork'
]


#-----------------------------------------------------------------------------#
# Graph
#------------------------
#

class Graph(object):
    
    """
    The basic class that contains a :class:`graph_tool.Graph` and some
    of is properties or methods to easily access them.

    :ivar id: :class:`int`
        unique id that identifies the instance.
    :ivar graph: :class:`~nngt.core.GraphObject`
        main attribute of the class instance.
    """

    #-------------------------------------------------------------------------#
    # Class properties

    __num_graphs = 0
    __max_id = 0
    #~ __di_property_func = {
            #~ "reciprocity": reciprocity, "clustering": clustering,
            #~ "assortativity": assortativity, "diameter": diameter,
            #~ "scc": num_scc, "wcc": num_wcc, "radius": spectral_radius, 
            #~ "num_iedges": num_iedges }
    #~ __properties = __di_property_func.keys()
    
    @classmethod
    def num_graphs(cls):
        ''' Returns the number of alive instances. '''
        return cls.__num_graphs
    
    @classmethod
    def from_matrix(cls, matrix, weighted=True, directed=True):
        '''
        Creates a :class:`~nngt.Graph` from a :class:`scipy.sparse` matrix or
        a dense matrix.
        
        Parameters
        ----------
        matrix : :class:`scipy.sparse` matrix or :class:`numpy.array`
            Adjacency matrix.
        weighted : bool, optional (default: True)
            Whether the graph edges have weight properties.
        directed : bool, optional (default: True)
            Whether the graph is directed or undirected.
        
        Returns
        -------
        :class:`~nngt.Graph`
        '''
        shape = matrix.shape
        if shape[0] != shape[1]:
            raise InvalidArgument('A square matrix is required')
        nodes = shape[0]
        if not directed:
            if issubclass(matrix.__class__, ssp.spmatrix):
                if not (matrix.T != matrix).nnz == 0:
                    raise InvalidArgument('Incompatible directed=False option \
with non symmetric matrix provided.')
            else:
                if not (matrix.T == matrix).all():
                    raise InvalidArgument('Incompatible directed=False option \
with non symmetric matrix provided.')
        edges = np.array(matrix.nonzero()).T
        graph = cls(nodes,name='FromNpArray_{}'.format(cls.__num_graphs),
                    weighted=weighted, directed=directed)
        graph.add_edges(edges)
        if weighted:
            weights = None
            if issubclass(matrix.__class__, ssp.spmatrix):
                weights = np.array(matrix[edges[:,0],edges[:,1]])[0]
            else:
                weights = matrix[dges[:,0],dges[:,1]]
                
            graph.set_weights(elist=edges, wlist=weights)
        return graph
            

    #-------------------------------------------------------------------------#
    # Constructor/destructor and properties
    
    def __init__(self, nodes=0, name="Graph",
                  weighted=True, directed=True, libgraph=None, **kwargs):
        '''
        Initialize Graph instance

        Parameters
        ----------
        nodes : int, optional (default: 0)
            Number of nodes in the graph.
        name : string, optional (default: "Graph")
            The name of this :class:`Graph` instance.
        weighted : bool, optional (default: True)
            Whether the graph edges have weight properties.
        directed : bool, optional (default: True)
            Whether the graph is directed or undirected.
        libgraph : :class:`~nngt.core.GraphObject`, optional
            An optional :class:`~nngt.core.GraphObject` to serve as base.
        
        Returns
        -------
        self : :class:`~nggt.core.Graph`
        '''
        self.__id = self.__class__.__max_id
        self._name = name
        self._directed = directed
        self._edges = []
        self._graph_type = "custom"
        # create the graphlib graph
        if libgraph is not None:
            self._graph = GraphObject.to_graph_object(libgraph)
        else:
            self._graph = GraphObject(nodes=nodes, directed=directed)
        # take care of the weights @todo: use those of the libgraph
        if weighted:
            if "weight_prop" in kwargs.keys():
                self._w = kwargs["weight_prop"]
            else:
                self._w = {"distrib": "constant"}
            self.set_weights()
        # update the counters
        self.__class__.__num_graphs += 1
        self.__class__.__max_id += 1

    def __del__(self):
        self.__class__.__num_graphs -= 1

    @property
    def id(self):
        ''' unique :class:`int` identifying the instance '''
        return self.__id
    
    @property
    def graph(self):
        ''' :class:`graph_tool.Graph` attribute of the instance '''
        return self._graph

    @graph.setter
    def graph(self, new_graph):
        if isinstance(new_graph, GraphLib):
            self._graph = GraphObject.to_graph_object(new_graph)
        elif isinstance(new_graph, GraphObject):
            self._graph = new_graph
        else:
            raise TypeError("The object passed is not a \
                GraphObject but a {}".format(new_graph.__class__.__name__))
    
    @property
    def name(self):
        ''' name of the graph '''
        return self._name

    @property
    def edges(self):
        return self._edges

    #-------------------------------------------------------------------------#
    # Graph actions
    
    def copy(self):
        '''
        Returns a deepcopy of the current :class:`~nngt.core.Graph`
        instance
        '''
        gc_instance = Graph(name=self._name+'_copy',
                            weighted=self.is_weighted(),
                            graph=self._graph.copy())
        return gc_instance
    
    def add_edges(self, lst_edges):
        '''
        Add a list of edges to the graph.
        
        Parameters
        ----------
        lst_edges : list of 2-tuples or np.array of shape (edge_nb, 2)
            List of the edges that should be added as tuples (source, target)
            
        @todo: add example, check the edges for self-loops and multiple edges
        '''
        self._graph.new_edges(lst_edges)
        self._edges.extend(lst_edges)

    def inhibitory_subgraph(self):
        ''' Create a :class:`~nngt.core.Graph` instance which graph
        contains only the inhibitory edges of the current instance's
        :class:`graph_tool.Graph` '''
        eprop_b_type = self._graph.new_edge_property(
                       "bool",-self._graph.edge_properties[TYPE].a+1)
        self._graph.set_edge_filter(eprop_b_type)
        inhib_graph = Graph( name=self._name + '_inhib',
                             weighted=self.is_weighted(),
                             graph=GraphObject(self._graph,prune=True) )
        self._graph.clear_filters()
        return inhib_graph

    def excitatory_subgraph(self):
        ''' create a :class:`~nngt.core.Graph` instance which graph
        contains only the excitatory edges of the current instance's
        :class:`GraphObject` '''
        eprop_b_type = self._graph.new_edge_property(
                       "bool",self._graph.edge_properties[TYPE].a+1)
        self._graph.set_edge_filter(eprop_b_type)
        exc_graph = Graph( name=self._name + '_exc',
                             weighted=self.is_weighted(),
                             graph=GraphObject(self._graph,prune=True) )
        self._graph.clear_filters()
        return exc_graph

    def adjacency_matrix(self, typed=True, weighted=True):
        '''
        Returns the adjacency matrix of the graph as a
        :class:`scipy.sparse.csr_matrix`.
        
        Parameters
        ----------
        weighted : bool or string, optional (default: True)
            If True, each entry ``adj[i,j] = w_ij`` where ``w_ij`` is the
            strength of the connection from `i` to `j`, if False, ``adj[i,j] = 
            0. or 1.``. Weighted can also be a string describing an edge
            attribute (e.g. if "distance" refers to an edge attribute ``dist``,
            then ``ajacency_matrix("distance")`` will return
            ``adj[i,i] = dist_ij``).
            
        Returns
        -------
        adj : :class:`scipy.sparse.csr_matrix`
            The adjacency matrix of the graph.
        '''
        return na.adjacency_matrix(self, typed=typed, weighted=weighted)

    def clear_edges(self):
        ''' Remove all the edges in the graph. '''
        self._graph.clear_edges()

    #-------------------------------------------------------------------------#
    # Setters
        
    def set_name(self, name=""):
        ''' set graph name '''
        if name != "":
            self._name = name
        else:
            self._name = "Graph_" + str(self.__id)

    def set_edge_attribute(self, attribute, values=None, val=None,
                           value_type=None):
        if attribute not in self.attributes():
            self._graph.new_edge_attribute(attribute, value_type, values, val)
        else:
            num_edges = self.edge_nb()
            if values is None:
                if val is not None:
                    values = np.repeat(val,num_edges)
                else:
                    raise InvalidArgument("At least one of the `values` and \
`val` arguments should not be ``None``.")
            self._graph._eattr[attribute] = values
    
    def set_weights(self, elist=None, wlist=None, ifrac=None, distrib=None,
                    distrib_prop=None, correl=None, noise_scale=None):
        '''
        Set the synaptic weights.
        @todo: take elist into account in Connections.weights
        
        Parameters
        ----------
        elist : class:`numpy.array`, optional (default: None)
            List of the edges (for user defined weights).
        wlist : class:`numpy.array`, optional (default: None)
            List of the weights (for user defined weights).
        distrib : class:`string`, optional (default: None)
            Type of distribution (choose among "constant", "uniform", 
            "gaussian", "lognormal", "lin_corr", "log_corr").
        distrib_prop : dict, optional (default: {})
            Dictoinary containing the properties of the weight distribution.
        correl : class:`string`, optional (default: None)
            Property to which the weights should be correlated.
        noise_scale : class:`int`, optional (default: None)
            Scale of the multiplicative Gaussian noise that should be applied
            on the weights.
        '''
        if distrib is None:
            distrib = self._w["distrib"]
        if distrib_prop is None:
            distrib_prop = (self._w["distrib_prop"] if "distrib_prop" in 
                            self._w.keys() else {})
        if correl is None:
            correl = self._w["correl"] if "correl" in self._w.keys() else None
        Connections.weights(self, elist=elist, wlist=wlist, distrib=distrib,
            correl=correl, distrib_prop=distrib_prop, noise_scale=noise_scale)

    def set_types(self, syn_type, nodes=None, fraction=None):
        '''
        Set the synaptic/connection types.

        .. warning :
            This is only for use in graph theoretical measurements; when 
            translating a :class:`~nngt.Network` to NEST, only the
            :class:`~nngt.NeuralGroup`s are taken into account. This is
            especially important if you set types that do not match those of
            the population : be aware that the types will not be taken into 
            account in the simulations.

        Parameters
        ----------
        syn_type : int or string
            Type of the connection among 'excitatory' (also `1`) or
            'inhibitory' (also `-1`).
        nodes : int, float or list, optional (default: `None`)
            If `nodes` is an int, number of nodes of the required type that
            will be created in the graph (all connections from inhibitory nodes
            are inhibitory); if it is a float, ratio of `syn_type` nodes in the
            graph; if it is a list, ids of the `syn_type` nodes.
        fraction : float, optional (default: `None`)
            Fraction of the selected edges that will be set as `syn_type` (if
            `nodes` is not `None`, it is the fraction of the specified nodes'
            edges, otherwise it is the fraction of all edges in the graph).

        Returns
        -------
        t_list : :class:`numpy.ndarray`
            List of the types in an order that matches the `edges` attribute of
            the graph.
        '''
        inhib_nodes = nodes
        if syn_type == 'excitatory' or syn_type == 1:
            if issubclass(nodes.__class__, int):
                inhib_nodes = graph.node_nb() - nodes
            elif issubclass(nodes.__class__, float):
                inhib_nodes = 1./nodes
            elif hasattr(nodes, '__iter__'):
                inhib_nodes = list(range(graph.node_nb()))
                nodes.sort()
                for node in nodes[::-1]:
                    del inhib_nodes[node]
        return Connections.types(self, inhib_nodes, fraction)
        
        

    #-------------------------------------------------------------------------#
    # Getters
    
    def attributes(self):
        ''' List of the graph's attributes (synaptic weights, delays...) '''
        return self._graph._eattr.keys()
    
    def get_name(self):
        ''' Get the name of the graph '''
        return self._name

    def get_graph_type(self):
        ''' Return the type of the graph (see nngt.generation) '''
        return self._graph_type
    
    def node_nb(self):
        ''' Number of nodes in the graph '''
        return self._graph.node_nb()
    
    def edge_nb(self):
        ''' Number of edges in the graph '''
        return self._graph.edge_nb()
    
    def get_density(self):
        '''
        Density of the graph: :math:`\\frac{E}{N^2}`, where `E` is the number of
        edges and `N` the number of nodes.
        '''
        return self._graph.edge_nb()/float(self._graph.node_nb()**2)

    def is_weighted(self):
        ''' Whether the edges have weights '''
        return "weight" in self.attributes()

    def is_directed(self):
        ''' Whether the graph is directed or not '''
        return self._directed

    #~ def get_property(self, s_property):
        #~ ''' Return the desired property or None for an incorrect one. '''
        #~ if s_property in Graph.__properties:
            #~ return Graph.__di_property_func[s_property](self._graph)
        #~ else:
            #~ warnings.warn("Ignoring request for unknown property \
                          #~ '{}'".format(s_property))
            #~ return None

    #~ def get_properties(self, a_properties):
        #~ '''
        #~ Return a dictionary containing the desired properties
#~ 
        #~ Parameters
        #~ ----------
        #~ a_properties : sequence
            #~ List or tuple of strings of the property names.
#~ 
        #~ Returns
        #~ -------
        #~ di_result : dict
            #~ A dictionary of values with the property names as keys.
        #~ '''
        #~ di_result = { prop: self.get_property(prop) for prop in a_properties }
        #~ return di_result

    def get_degrees(self, node_list=None, deg_type="total", use_weights=True):
        '''
        Degree sequence of all the nodes.
        
        Parameters
        ----------
        node_list : list, optional (default: None)
            List of the nodes which degree should be returned
        deg_type : string, optional (default: "total")
            Degree type (among 'in', 'out' or 'total').
        use_weights : bool, optional (default: True)
            Whether to use weighted (True) or simple degrees (False).
        
        Returns
        -------
        :class:`numpy.array` or None (if an invalid type is asked).
        '''
        valid_types = ("in", "out", "total")
        if deg_type in valid_types:
            return self._graph.degree_list(node_list, deg_type, use_weights)
        else:
            warnings.warn("Ignoring invalid degree type '{}'".format(strType))
            return None

    def get_betweenness(self, use_weights=True):
        '''
        Betweenness centrality sequence of all nodes and edges.
        
        Parameters
        ----------
        use_weights : bool, optional (default: True)
            Whether to use weighted (True) or simple degrees (False).
        
        Returns
        -------
        node_betweenness : :class:`numpy.array`
            Betweenness of the nodes.
        edge_betweenness : :class:`numpy.array`
            Betweenness of the edges.
        '''
        return self._graph.betweenness(use_weights)

    def get_edge_types(self):
        if TYPE in self._graph.edge_properties.keys():
            return self._graph.edge_properties[TYPE].a
        else:
            return repeat(1, self._graph.edge_nb())
    
    def get_weights(self):
        ''' Returns the weighted adjacency matrix as a
        :class:`scipy.sparse.lil_matrix`.
        '''
        return self._graph.eproperties["weight"]

    def is_spatial(self):
        '''
        Whether the graph is embedded in space (has a :class:`~nngt.Shape`
        attribute).
        '''
        return True if issubclass(self.__class__, SpatialGraph) else False



#-----------------------------------------------------------------------------#
# SpatialGraph
#------------------------
#

class SpatialGraph(Graph):
    
    """
    The detailed class that inherits from :class:`Graph` and implements
    additional properties to describe various biological functions
    and interact with the NEST simulator.

    :ivar shape: :class:`~nngt.Shape`
        Shape of the neurons environment.
    :ivar positions: :class:`numpy.array`
        Positions of the neurons.
    :ivar graph: :class:`~nngt.GraphObject`
        Main attribute of the class instance.
    """

    #-------------------------------------------------------------------------#
    # Class properties

    __num_graphs = 0
    __max_id = 0

    @classmethod
    def make_spatial(graph, shape=Shape(), positions=None):
        if isinstance(graph, Network):
            graph.__class__ = SpatialNetwork
        else:
            graph.__class__ = SpatialGraph
        graph._init_spatial_properties(shape, positions)

    #-------------------------------------------------------------------------#
    # Constructor, destructor, attributes    
    
    def __init__(self, nodes=0, name="Graph", weighted=True, directed=True,
                  libgraph=None, shape=None, positions=None, **kwargs):
        '''
        Initialize SpatialClass instance.
        @todo: see what we do with the libgraph argument

        Parameters
        ----------
        nodes : int, optional (default: 0)
            Number of nodes in the graph.
        name : string, optional (default: "Graph")
            The name of this :class:`Graph` instance.
        weighted : bool, optional (default: True)
            Whether the graph edges have weight properties.
        directed : bool, optional (default: True)
            Whether the graph is directed or undirected.
        shape : :class:`~nngt.core.Shape`, optional (default: None)
            Shape of the neurons' environment (None leads to Shape())
        positions : :class:`numpy.array`, optional (default: None)
            Positions of the neurons; if not specified and `nodes` is not 0,
            then neurons will be reparted at random inside the
            :class:`~nngt.core.Shape` object of the instance.
        
        Returns
        -------
        self : :class:`~nggt.Graph`
        '''
        self.__id = self.__class__.__max_id
        self.__class__.__num_graphs += 1
        self.__class__.__max_id += 1
        self._shape = None
        super(SpatialGraph, self).__init__(nodes, name, weighted, directed,
                                           libgraph, **kwargs)
        self._init_spatial_properties(shape, positions, **kwargs)
        
    def __del__(self):
        if self._shape is not None:
            self._shape._parent = None
        self._shape = None
        super(SpatialGraph, self).__del__()
        self.__class__.__num_graphs -= 1

    @property
    def shape(self):
        return self._shape

    @property
    def position(self):
        return self._pos

    #-------------------------------------------------------------------------#
    # Init tool
    
    def _init_spatial_properties(self, shape, positions=None, **kwargs):
        '''
        Create the positions of the neurons from the graph `shape` attribute
        and computes the connections distances.
        '''
        if positions is not None and len(positions) != self.node_nb():
            raise InvalidArgument("Wrong number of neurons in `positions`.")
        if shape is not None:
            shape.set_parent(self)
            self._shape = shape
        else:
            self._shape = Shape.rectangle(self,1,1)
        b_rnd_pos = True if not self.node_nb() or positions is None else False
        self._pos = self._shape.rnd_distrib() if b_rnd_pos else positions
        Connections.distances(self)


#-----------------------------------------------------------------------------#
# Network
#------------------------
#

class Network(Graph):
    
    """
    The detailed class that inherits from :class:`Graph` and implements
    additional properties to describe various biological functions
    and interact with the NEST simulator.
    
    :ivar population: :class:`~nngt.NeuralPop`
        Object reparting the neurons into groups with specific properties.
    :ivar graph: :class:`~nngt.core.GraphObject`
        Main attribute of the class instance
    :ivar nest_gid: :class:`numpy.array`
        Array containing the NEST gid associated to each neuron; it is ``None``
        until a NEST network has been created.
    :ivar id_from_nest_gid: dict
        Dictionary mapping each NEST gid to the corresponding neuron index in 
        the :class:`nngt.~Network`
    """

    #-------------------------------------------------------------------------#
    # Class attributes and methods

    __num_networks = 0
    __max_id = 0
        
    @classmethod
    def num_networks(cls):
        ''' Returns the number of alive instances. '''
        return cls.__num_networks

    @classmethod
    def uniform_network(cls, size, neuron_model=default_neuron,
                        neuron_param={}, syn_model=default_synapse,
                        syn_param={}):
        '''
        Generate a network containing only one type of neurons.
        
        Parameters
        ----------
        size : int
            Number of neurons in the network.
        neuron_model : string, optional (default: 'aief_cond_alpha')
            Name of the NEST neural model to use when simulating the activity.
        neuron_param : dict, optional (default: {})
            Dictionary containing the neural parameters; the default value will
            make NEST use the default parameters of the model.
        syn_model : string, optional (default: 'static_synapse')
            NEST synaptic model to use when simulating the activity.
        syn_param : dict, optional (default: {})
            Dictionary containing the synaptic parameters; the default value
            will make NEST use the default parameters of the model.
        
        Returns
        -------
        net : :class:`~nngt.Network` or subclass
            Uniform network of disconnected neurons.
        '''
        pop = NeuralPop.uniform_population(size, None, neuron_model,
           neuron_param, syn_model, syn_param)
        net = cls(population=pop)
        return net

    @classmethod
    def ei_network(cls, size, ei_ratio=0.2, en_model=default_neuron,
            en_param={}, es_model=default_synapse, es_param={},
            in_model=default_neuron, in_param={}, is_model=default_synapse,
            is_param={}):
        '''
        Generate a network containing a population of two neural groups:
        inhibitory and excitatory neurons.
        
        Parameters
        ----------
        size : int
            Number of neurons in the network.
        ei_ratio : double, optional (default: 0.2)
            Ratio of inhibitory neurons: :math:`\\frac{N_i}{N_e+N_i}`.
        en_model : string, optional (default: 'aeif_cond_alpha')
           Nest model for the excitatory neuron.
        en_param : dict, optional (default: {})
            Dictionary of parameters for the the excitatory neuron.
        es_model : string, optional (default: 'static_synapse')
            NEST model for the excitatory synapse.
        es_param : dict, optional (default: {})
            Dictionary containing the excitatory synaptic parameters.
        in_model : string, optional (default: 'aeif_cond_alpha')
           Nest model for the inhibitory neuron.
        in_param : dict, optional (default: {})
            Dictionary of parameters for the the inhibitory neuron.
        is_model : string, optional (default: 'static_synapse')
            NEST model for the inhibitory synapse.
        is_param : dict, optional (default: {})
            Dictionary containing the inhibitory synaptic parameters.
        
        Returns
        -------
        net : :class:`~nngt.Network` or subclass
            Network of disconnected excitatory and inhibitory neurons.
        '''
        pop = NeuralPop.ei_population(size, ei_ratio, None, en_model, en_param,
                    es_model, es_param, in_model, in_param, is_model, is_param)
        print(Network is cls)
        net = cls(population=pop)
        return net

    @staticmethod
    def make_network(graph, neural_pop):
        '''
        Turn a :class:`~nngt.Graph` object into a :class:`~nngt.Network`, or a
        :class:`~nngt.SpatialGraph` into a :class:`~nngt.SpatialNetwork`.

        Parameters
        ----------
        graph : :class:`~nngt.Graph` or :class:`~nngt.SpatialGraph`
            Graph to convert
        neural_pop : :class:`~nngt.NeuralPop`
            Population to associate to the new :class:`~nngt.Network`

        Notes
        -----
        In-place operation that directly converts the original graph.
        '''
        if isinstance(graph, SpatialGraph):
            graph.__class__ = SpatialNetwork
        else:
            graph.__class__ = Network
        graph.population = neural_pop
        Connections.delays(graph)

    #-------------------------------------------------------------------------#
    # Constructor, destructor and attributes
    
    def __init__(self, name="Graph", weighted=True, directed=True,
                 libgraph=None, population=None, **kwargs):
        '''
        Initializes :class:`~nngt.Network` instance.

        Parameters
        ----------
        nodes : int, optional (default: 0)
            Number of nodes in the graph.
        name : string, optional (default: "Graph")
            The name of this :class:`Graph` instance.
        weighted : bool, optional (default: True)
            Whether the graph edges have weight properties.
        directed : bool, optional (default: True)
            Whether the graph is directed or undirected.
        libgraph : :class:`~nngt.core.GraphObject`, optional (default: None)
            An optional :class:`~nngt.core.GraphObject` to serve as base.
        @todo:
        population : :class:`NeuralPop`, (default: None)
            A tuple containing the model(s) to use in NEST to simulate the 
            neurons as well as a dictionary containing the parameters for the
            neuron.
        
        Returns
        -------
        self : :class:`~nggt.core.Graph`
        '''
        self.__id = self.__class__.__max_id
        self._population = None
        self._nest_gid = None
        self.id_from_nest_gid = None
        self.__class__.__num_networks += 1
        self.__class__.__max_id += 1
        if population is None:
            raise InvalidArgument("Network needs a NeuralPop to be created")
        nodes = population.size
        if "nodes" in kwargs.keys():
            del kwargs["nodes"]
        super(Network, self).__init__(nodes=nodes, name=name,
                                      weighted=weighted, directed=directed,
                                      libgraph=libgraph, **kwargs)
        self._init_bioproperties(population)
    
    def __del__(self):
        super(Network, self).__del__()
        self.__class__.__num_networks -= 1

    @property
    def population(self):
        '''
        :class:`~nngt.NeuralPop` that divides the neurons into groups with
        specific properties.
        '''
        return self._population

    @population.setter
    def population(self, population):
        if issubclass(population.__class__, NeuralPop):
            if self._graph.node_nb() == population.size:
                if population.is_valid:
                    self._population = population
                else:
                    raise AttributeError("NeuralPop is not valid (not all \
                    neurons are associated to a group).")
            else:
                raise AttributeError("{} and NeuralPop must have same number \
                    of neurons".format(self.__class__.__name__))
        else:
            raise AttributeError("Expecting NeuralPop but received \
                    {}".format(pop.__class__.__name__))
    
    @property
    def nest_gid(self):
        return self._nest_gid
    
    @nest_gid.setter
    def nest_gid(self, gids):
        self._nest_gid = gids
        for group in self.population.itervalues():
            group._nest_gids = gids[group.id_list]

    #-------------------------------------------------------------------------#
    # Init tool
    
    def _init_bioproperties(self, population):
        ''' Set the population attribute and link each neuron to its group. '''
        if issubclass(population.__class__, NeuralPop):
            if population.is_valid:
                self._population = population
                nodes = population.size
                # create the delay attribute
                Connections.delays(self)
            else:
                raise AttributeError("NeuralPop is not valid (not all \
                neurons are associated to a group).")
        else:
            raise AttributeError("Expected NeuralPop but received \
                    {}".format(pop.__class__.__name__))

    #-------------------------------------------------------------------------#
    # Getter

    def neuron_properties(self, idx_neuron):
        '''
        Properties of a neuron in the graph.

        Parameters
        ----------
        idx_neuron : int
            Index of a neuron in the graph.

        Returns
        -------
        dict of the neuron properties.
        '''
        group_name = self._population._neuron_group[idx_neuron]
        return self._population[group_name].properties()



#-----------------------------------------------------------------------------#
# SpatialNetwork
#------------------------
#

class SpatialNetwork(Network,SpatialGraph):
    
    """
    Class that inherits from :class:`~nngt.Network` and :class:`SpatialGraph`
    to provide a detailed description of a real neural network in space, i.e.
    with positions and biological properties to interact with NEST.

    :ivar shape: :class:`nngt.core.Shape`
        Shape of the neurons environment.
    :ivar positions: :class:`numpy.array`
        Positions of the neurons.
    :ivar population: :class:`~nngt.NeuralPop`
        Object reparting the neurons into groups with specific properties.
    :ivar graph: :class:`~nngt.core.GraphObject`
        Main attribute of the class instance.
    :ivar nest_gid: :class:`numpy.array`
        Array containing the NEST gid associated to each neuron; it is ``None``
        until a NEST network has been created.
    :ivar id_from_nest_gid: dict
        Dictionary mapping each NEST gid to the corresponding neuron index in 
        the :class:`nngt.~SpatialNetwork`
    """

    #-------------------------------------------------------------------------#
    # Class attributes

    __num_networks = 0
    __max_id = 0

    #-------------------------------------------------------------------------#
    # Constructor, destructor, and attributes
    
    def __init__(self, population, name="Graph", weighted=True, directed=True,
                 shape=None, graph=None, positions=None, **kwargs):
        '''
        Initialize Graph instance

        Parameters
        ----------
        name : string, optional (default: "Graph")
            The name of this :class:`Graph` instance.
        weighted : bool, optional (default: True)
            Whether the graph edges have weight properties.
        directed : bool, optional (default: True)
            Whether the graph is directed or undirected.
        shape : :class:`~nngt.core.Shape`, optional (default: None)
            Shape of the neurons' environment (None leads to Shape())
        positions : :class:`numpy.array`, optional (default: None)
            Positions of the neurons; if not specified and `nodes` != 0, then
            neurons will be reparted at random inside the
            :class:`~nngt.core.Shape` object of the instance.
        population : class:`~nngt.NeuralPop`, optional (default: None)
        
        Returns
        -------
        self : :class:`~nggt.core.Graph`
        '''
        self.__id = self.__class__.__max_id
        self.__class__.__num_networks += 1
        self.__class__.__max_id += 1
        if population is None:
            raise InvalidArgument("Network needs a NeuralPop to be created")
        nodes = population.size
        super(SpatialNetwork, self).__init__(
            nodes=nodes, name=name, weighted=weighted, directed=directed,
            shape=shape, positions=positions, population=population, **kwargs)

    def __del__ (self):
        super(SpatialNetwork, self).__del__()
        self.__class__.__num_networks -= 1
