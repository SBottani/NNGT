#!/usr/bin/env python
#-*- coding:utf-8 -*-

"""
Functions for plotting graphs and graph properties.

note ::
    For now, graph plotting is only supported when using the
    `graph_tool <https://graph-tool.skewed.de>`_ library.

Content
=======
"""

import sys
import matplotlib

from nngt import config

if config["backend"] is not None:
    print("Changing matplotlib backend to {}".format(config["backend"]))
    matplotlib.use(config["backend"])
else:
    sav_backend = matplotlib.get_backend()
    backends = [ 'GTK3Agg', 'Qt4Agg', 'Qt5Agg' ]
    keep_trying = True
    while backends and keep_trying:
        try:
            backend = backends.pop()
            matplotlib.use(backend)
            keep_trying = False
        except:
            matplotlib.use(sav_backend)
    
        
import warnings
warnings.filterwarnings("ignore", module="matplotlib")

from nngt.globals import config


# module import

from .custom_plt import palette
from .plt_properties import degree_distribution, betweenness_distribution
from .plt_activity import spike_raster

__all__ = [ "degree_distribution", "betweenness_distribution", 'spike_raster' ]

if config["graph_library"] == 'graph-tool':
    from .plt_networks import draw_network
    __all__.append("draw_network")
else:
    warnings.warn("Graph drawing is only available with graph_tool at the \
moment. As {} is currently being used, all graph drawing functions will be \
disabled.".format(config["graph_library"]))
