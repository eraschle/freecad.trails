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
Geometry nodes for Tracker objects
"""

from pivy import coin

from .coin_styles import CoinStyles
from .signal import Signal
from .publisher_events import PublisherEvents as Events

class Geometry(Signal):
    """
    Geometry nodes for Tracker objects
    """

    #members provided by Base, Style
    base_node = None
    active_style = None
    def set_visibility(self, visible=True): pass
    def set_style(self, style=None, draw=None, color=None): pass

    def __init__(self):
        """
        Constructor
        """

        if not (self.active_style and self.base_node):
            return

        self.geo_node = coin.SoSeparator()
        self.coordinate_node = coin.SoCoordinate3()

        self.geo_node.addChild(self.coordinate_node)
        self.base_node.addChild(self.geo_node)

        super().__init__()

    def set_coordinates(self, coordinates, do_notify):
        """
        Update the SoCoordinate3 with the passed coordinates
        Assumes coordinates is a list of 3-float tuples
        """

        if not coordinates:
            return

        if not isinstance(coordinates, list):
            coordinates = [coordinates]

        self.coordinate_node.point.setValues(coordinates)

        if do_notify and self.do_publish:
            self.dispatch(Events.NODE.UPDATED, (self.name, coordinates), False)

    def get(self, _dtype=tuple):
        """
        Return the coordinates as the specified iterable type
        """

        _values = self.coordinate_node.point.getValues()

        return [_dtype(_v.getValue()) for _v in _values]
