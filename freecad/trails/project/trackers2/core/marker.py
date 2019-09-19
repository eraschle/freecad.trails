# -*- coding: utf-8 -*-
#**************************************************************************
#*                                                                     *
#* Copyright (c) 2019 Joel Graff <monograff76@gmail.com>               *
#*                                                                     *
#* This program is free software; you can redistribute it and/or modify*
#* it under the terms of the GNU Lesser General Public License (LGPL)  *
#* as published by the Free Software Foundation; either version 2 of   *
#* the License, or (at your option) any later version.                 *
#* for detail see the LICENCE text file.                               *
#*                                                                     *
#* This program is distributed in the hope that it will be useful,     *
#* but WITHOUT ANY WARRANTY; without even the implied warranty of      *
#* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the       *
#* GNU Library General Public License for more details.                *
#*                                                                     *
#* You should have received a copy of the GNU Library General Public   *
#* License along with this program; if not, write to the Free Software *
#* Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307*
#* USA                                                                 *
#*                                                                     *
#***********************************************************************
"""
Marker tracker class for tracker objects
"""

from collections.abc import Iterable

from pivy import coin

import FreeCADGui as Gui

#from .publisher_events import PublisherEvents as Events

from .base import Base
from .style import Style
from .selection import Selection
from .geometry import Geometry
from .coin_styles import CoinStyles

class Marker(Base, Style, Selection, Geometry):
    """
    Tracker object for nodes
    """

    def __init__(self, name, point):
        """
        Constructor
        """

        super().__init__(name=name)

        self.is_end_node = False
        self.point = tuple(point)

        #build node structure for the node tracker

        self.marker_node = coin.SoMarkerSet()

        self.drag_point = self.point

        self.geo_node.addChild(self.marker_node)

        self.set_style(CoinStyles.DEFAULT)

        self.update()


    def update(self, coord=None, do_notify=False):
        """
        Update the coordinate position
        """

        #if we have a list of points, pick the first
        if isinstance(coord, list):
            coord = coord[0]

        if not coord:
            coord = self.point

        _c = coord

        if not isinstance(coord, tuple) and isinstance(coord, Iterable):
            _c = tuple(_c,)

        self.point = _c
        self.drag_point = self.point

        Geometry.set_coordinates(self, _c, do_notify)

    def set_style(self, style=None, draw=None, color=None):
        """
        Override style implementation
        """

        Style.set_style(self, style, draw, color)

        self.marker_node.markerIndex = Gui.getMarkerIndex(
            self.active_style.shape, self.active_style.size)

    def finalize(self, node=None, parent=None):
        """
        Cleanup
        """

        super().finalize(self.geo_node, parent)
