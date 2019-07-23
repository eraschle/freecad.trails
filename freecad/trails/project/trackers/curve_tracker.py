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
Tracker for curve editing
"""

import math

from pivy import coin

from FreeCAD import Vector

import FreeCADGui as Gui

from ...geometry import support, arc, spiral

from .base_tracker import BaseTracker
from .coin_style import CoinStyle

from ..support.utils import Constants as C
from ..support.mouse_state import MouseState

from ..containers import DragState

from .node_tracker import NodeTracker
from .wire_tracker import WireTracker

class CurveTracker(BaseTracker):
    """
    Tracker class for alignment design
    """

    def __init__(self, view, names, curve, pi_nodes):
        """
        Constructor
        """

        self.curve = curve
        self.pi_nodes = pi_nodes
        self.callbacks = {}
        self.names = names
        self.mouse = MouseState()
        self.user_dragging = False
        self.is_valid = True
        self.status_bar = Gui.getMainWindow().statusBar()
        self.drag = DragState()
        self.view = view
        self.state = 'UNSELECTED'
        self.viewport = \
            view.getViewer().getSoRenderManager().getViewportRegion()

        super().__init__(names=self.names)

        #input callback assignments
        self.callbacks = {
            'SoLocation2Event':
            self.view.addEventCallback('SoLocation2Event', self.mouse_event),

            'SoMouseButtonEvent':
            self.view.addEventCallback('SoMouseButtonEvent', self.button_event)
        }

        #scenegraph node structure for editing and dragging operations
        self.groups = {
            'EDIT': coin.SoGroup(),
            'DRAG': coin.SoGroup(),
        }

        self.node.addChild(self.groups['EDIT'])
        self.node.addChild(self.groups['DRAG'])

        #generate initial node trackers and wire trackers for mouse interaction
        #and add them to the scenegraph
        self.trackers = None
        self.build_trackers()

        _trackers = []

        for _v in self.trackers.values():
            _trackers.extend(_v)

        for _v in _trackers:
            self.insert_node(_v.node, self.groups['EDIT'])

        #insert in the scenegraph root
        self.insert_node(self.node)

    def _update_status_bar(self, info):
        """
        Update the status bar with the latest mouseover data
        """

        pass
        #_id = ''

        #if info:
        #    _id = info['Component']

        #_pos = self.view.getPoint(self.mouse.pos)

        #if 'NODE' in _id:
        #    _pos = self.datum.add(
        #        self.trackers['Nodes'][int(_id.split('-')[1])].get()
        #    )

        #_msg = _id + ' ' + str(tuple(_pos))

        ##self.status_bar.clearMessage()
        #self.status_bar.showMessage(_msg)

    def mouse_event(self, arg):
        """
        Manage mouse actions affecting multiple nodes / wires
        """

        _p = self.view.getCursorPos()

        self.mouse.update(arg, _p)

        self._update_status_bar(self.view.getObjectInfo(_p))

        if self.mouse.button1.dragging:

            if self.user_dragging:
                self.on_drag(arg['CtrlDown'], arg['ShiftDown'])
                self.view.redraw()

            else:
                self.start_drag()
                self.user_dragging = True


    def button_event(self, arg):
        """
        Manage button actions affecting multiple nodes / wires
        """

        self.mouse.update(arg, self.view.getCursorPos())

        _states = [_v.state == 'SELECTED' for _v in self.trackers['Nodes']]

        if all(_states):
            self.state = 'SELECTED'
        elif any(_states):
            self.state = 'PARTIAL'
        else:
            self.state = 'UNSELECTED'

        #terminate dragging if button is released
        if self.user_dragging and not self.mouse.button1.dragging:
            self.end_drag()
            self.user_dragging = False

    def build_trackers(self):
        """
        Build the node and wire trackers that represent the selectable
        portions of the curve geometry
        """

        _node_names = ['Center', 'Start', 'End', 'PI', 'Center']
        _wires = (
            ('Start Radius', 1, 0),
            ('Start Tangent', 1, 3),
            ('End Radius', 2, 0),
            ('End Tangent', 2, 3)
        )

        #build a list of coordinates from curves in the geometry
        #skipping the last (duplicate of center)
        _coords = [self.curve[_k] for _k in _node_names[:-1]]

        #build the trackers
        _result = {'Nodes': [], 'Wires': [], 'Curve': None}

        #node trackers - don't create a PI node
        for _i, _pt in enumerate(_coords[:-1]):

            _names = self.names[:]
            _names[-1] = _names[-1] + '-' + _node_names[_i]

            _tr = NodeTracker(
                view=self.view,
                names=_names,
                point=_pt
            )

            _tr.update(_pt)

            _result['Nodes'].append(_tr)

        #wire trackers
        for _i, _v in enumerate(_wires):

            _result['Wires'].append(
                self._build_wire_tracker(
                    wire_name=self.names + [_v[0]],
                    nodes=_result['Nodes'],
                    points=[_coords[_v[1]], _coords[_v[2]]]
                )
            )

        _points = []

        #curve wire tracker
        _class = arc

        if self.curve['Type'] == 'Spiral':
            _class = spiral

        _points, _x = _class.get_points(self.curve)

        _result['Curve'] = [
            self._build_wire_tracker(
                wire_name=self.names + [self.curve['Type']],
                nodes=_result['Nodes'],
                points=_points,
                select=True
            )
        ]

        self.trackers = _result

    def _build_wire_tracker(self, wire_name, nodes, points, select=False):
        """
        Convenience function for WireTracker construction
        """

        _wt = WireTracker(view=self.view, names=wire_name)

        _wt.set_selectability(select)
        _wt.set_selection_nodes(nodes)
        _wt.update(points)

        return _wt

    def update(self):
        """
        Update the curve based on the passed data points
        """

        if self.curve['Type'] == 'Spiral':
            self.curve = self._generate_spiral()

        else:
            self.curve = self._generate_arc()

        self.build_trackers()

    def _generate_spiral(self):
        """
        Generate a spiral curve
        """

        _key = ''
        _rad = 0.0

        _start = self.pi_nodes[0].get()
        _pi = self.pi_nodes[1].get()
        _end = self.pi_nodes[2].get()

        if not self.curve.get('StartRadius') \
            or self.curve['StartRadius'] == math.inf:

            _key = 'EndRadius'
            _end = self.curve['End']

            #first curve uses the start point.
            #otherwise, calculate a point halfway in between.
            if _start.is_end_node:

                _start = _pi.sub(
                    Vector(_pi.sub(_start)).multiply(
                        _start.distanceToPoint(_pi) / 2.0
                    )
                )

        else:

            _key = 'StartRadius'
            _start = self.curve['Start']

            #last curve uses the end point.
            #otherwise, calcualte a point halfway between.
            if _start.is_end_node:

                    _end = _pi.add(
                        Vector(_end.sub(_pi)).multiply(
                             _end.distanceToPoint(_pi) / 2.0)
                    )

        _curve = {
            'PI': _pi,
            'Start': _start,
            'End': _end,
            _key: self.curve[_key]
        }

        _curve = spiral.solve_unk_length(_curve)

        #re-render the last known good points if an error occurs
        if _curve['TanShort'] <= 0.0 or _curve['TanLong'] <= 0.0:
            _curve = self.curve

        return _curve

    def _generate_arc(self):
        """
        Generate a simple arc curve
        """

        _start = self.pi_nodes[0].get()
        _pi = self.pi_nodes[1].get()
        _end = self.pi_nodes[2].get()

        _curve = {
                'BearingIn': support.get_bearing(_pi.sub(_start)),
                'BearingOut': support.get_bearing(_end.sub(_pi)),
                'PI': _pi,
                'Radius': self.curve['Radius'],
            }

        return arc.get_parameters(_curve)

    def start_drag(self):
        """
        Set up the scene graph for dragging operations
        """

        pass

        ##set the drag start point to the first selected node
        #for _i, _v in enumerate(self.trackers['Nodes']):

        #    if _v.state != 'SELECTED':
        #        continue

        #    _c = _v.get()

        #    if not self.drag.start:

        #        self.drag.start =\
        #            Vector(self.view.getPoint(self.mouse.pos)).sub(self.datum)

        #        self.drag.position = self.drag.start
        #        self.drag.center = _c

        #    if self.drag.nodes:

        #        if self.drag.nodes[-1] == _c:
        #            continue

        #    self.drag.nodes.append(_c)
        #    self.drag.node_idx.append(_i)


        #self.curves = self.alignment.get_curves()
        #self.pi_list = self.alignment.model.get_pi_coords()
        #self.drag.pi = self.pi_list[:]

        #_partial = []

        ##duplicate scene nodes of selected and partially-selected wires
        ##for _v in self.trackers['Tangents'] + self.trackers['Curves']:

        #    self.drag.tracker_state.append(
        #        [_w.get() for _w in _v.selection_nodes]
        #    )

        #    if _v.state == 'UNSELECTED':
        #        continue

        #    self.groups[_v.state].addChild(_v.copy())

        #self.drag.multi = self.groups['SELECTED'].getNumChildren() > 2

        ##get paritally selected tangents to build curve index
        #_partial = [
        #    _i for _i, _v in enumerate(self.trackers['Tangents'])\
        #        if _v.state == 'PARTIAL'
        #]

        #_curves = []

        ##build list of curve indices
        #for _i in _partial:

        #    if _i > 0 and not _i - 1 in _curves:
        #        _curves.append(_i - 1)

        #    if _i < len(self.curves):
        #        _curves.append(_i)

        #self.drag.curves = _curves

    def on_drag(self, do_rotation, modify):
        """
        Update method during drag operations
        """

        pass

        #if self.drag.start is None:
        #    return

        #_world_pos = self.view.getPoint(self.mouse.pos).sub(self.datum)

        #self._update_transform(_world_pos, do_rotation, modify)
        #self._update_pi_nodes(_world_pos)

        #_curves = self._generate_curves()

        #self._validate_curves(_curves)
        #self.drag.position = _world_pos

    def end_drag(self):
        """
        Cleanup method for drag operations
        """

        pass

        #if self.is_valid:

        ##do a final calculation on the curves
        #    self.drag.curves = list(range(0, len(self.curves)))

        #    self.alignment.update_curves(self.curves, self.drag.pi, True)

        #    for _i, _v in enumerate(self.alignment.model.get_pi_coords()):
        #        self.trackers['Nodes'][_i].update(_v)

        #    for _v in self.trackers['Tangents']:
        #        _v.update([_w.get() for _w in _v.selection_nodes])

        #    for _v in self.trackers['Curves']:
        #        _v.update([
        #            tuple(Vector(_w).sub(self.drag.pi[0])) for _w in _v.points
        #        ])

        #    self.datum = self.datum.add(self.drag.pi[0])
        #    self.transform.translation.setValue(tuple(self.datum))

        ##reset the tracker state
        #else:

        #    print('tracker state = ', self.drag.tracker_state)
        #    for _i, _v in enumerate(
        #        self.trackers['Tangents'] + self.trackers['Curves']):

        #        _v.update(self.drag.tracker_state[_i])

        #self.drag.reset()

        #self.drag_transform.center = coin.SbVec3f((0.0, 0.0, 0.0))
        #self.drag_transform.translation.setValue((0.0, 0.0, 0.0))
        #self.drag_transform.rotation = coin.SbRotation()

        #remove child nodes from the selected group
        #self.groups['SELECTED'].removeAllChildren()
        #self.groups['SELECTED'].addChild(self.drag_transform)
        #self.groups['SELECTED'].addChild(coin.SoSeparator())

        #remove child nodes from the partial group
        #self.groups['PARTIAL'].removeAllChildren()

    def _update_nodes(self, world_pos):
        """
        Internal function - Update wires with selected nodes
        """

        pass

        #_tans = self.trackers['Tangents']

        ##transform selected nodes
        #_result = self._transform_nodes(self.drag.nodes)

        ##write updated nodes to PI's
        #for _i, _v in enumerate(_result):

        #    #pi index
        #    _j = self.drag.node_idx[_i]

        #    #save the updated PI coordinate
        #    self.drag.pi[_j] = _v

        #    _limits = [_w if _w >= 0 else 0 for _w in [_j - 1, _j + 1]]

        #    #if there are partially selected tangents, we need to manually
        #    #update the scenegraph for the selected vertex
        #    for _l, _t in enumerate(_tans[_limits[0]:_limits[1]]):

        #        if _t.state != 'PARTIAL':
        #            continue

        #        _pts = [tuple(_w.get()) for _w in _t.selection_nodes]

        #        if _t.selection_nodes[0].state == 'SELECTED':
        #            _pts[0] = tuple(_v)

        #        else:
        #            _pts[1] = tuple(_v)

        #        self.groups['PARTIAL'].getChild(_l).getChild(4)\
        #            .point.setValues(_pts)

    def _transform_nodes(self, nodes):
        """
        Transform selected nodes by the transformation matrix
        """

        pass

        #_matrix = self.get_matrix()
        #_result = []

        #for _n in nodes:

        #    _v = coin.SbVec4f(tuple(_n) + (1.0,))
        #    _v = _matrix.multVecMatrix(_v).getValue()[:3]

        #    _result.append(Vector(_v).sub(self.datum))

        #return _result

    def _generate_curve(self):
        """
        Internal function - Generate curves based on existing curves and nodes
        """

        pass

        ##get the indices of curves that are to be updated
        #_indices = self.drag.curves

        #if not _indices:
        #    return

        #_result = []
        #_rng = (_indices[0], _indices[-1] + 3)
        #_nodes = self.pi_list[_rng[0]:_rng[1]]

        #for _i, _v in enumerate(self.trackers['Nodes'][_rng[0]:_rng[1]]):

        #    if _v.state == 'SELECTED':
        #        _nodes[_i] = self._transform_nodes([_v.get()])[0]

        #_j = 0
        #_last_curve = None

        #for _i in _indices:

        #    _start = _nodes[_j]
        #    _pi = _nodes[_j + 1]
        #    _end = _nodes[_j + 2]

        #    _class = arc
        #    _curve = {
        #            'BearingIn': support.get_bearing(_pi.sub(_start)),
        #            'BearingOut': support.get_bearing(_end.sub(_pi)),
        #            'PI': _pi,
        #            'Radius': self.curves[_i]['Radius'],
        #        }

        #    if self.curves[_i]['Type'] == 'Spiral':

        #        _class = spiral
        #        _key = ''
        #        _rad = 0.0

        #        if not self.curves[_i].get('StartRadius') \
        #            or self.curves[_i]['StartRadius'] == math.inf:
        #            _key = 'EndRadius'
        #            _rad = self.curves[_i + 1]['Radius']
        #            _end = self.curves[_i + 1]['Start']

        #            if _i > 0:
        #                _start = _pi.sub(
        #                    Vector(_pi.sub(_start)).multiply(
        #                        _start.distanceToPoint(_pi) / 2.0
        #                    )
        #                )

        #        else:
        #            _key = 'StartRadius'
        #            _rad = self.curves[_i - 1]['Radius']
        #            _start = self.curves[_i - 1]['End']

        #            if _i < len(self.curves) - 1:
        #                _end = _pi.add(
        #                    Vector(_end.sub(_pi)).multiply(
        #                        _end.distanceToPoint(_pi) / 2.0)
        #                )

        #        _curve = {
        #            'PI': _pi,
        #            'Start': _start,
        #            'End': _end,
        #            _key: _rad
        #        }

        #        _curve = spiral.solve_unk_length(_curve)

        #        #re-render the last known good points if an error occurs
        #        if _curve['TanShort'] <= 0.0 or _curve['TanLong'] <= 0.0:
        #            _curve = self.curves[_i]

        #        _points, _x = spiral.get_points(_curve)

        #    else:
        #        _class = arc
        #        _curve = arc.get_parameters(_curve)
        #        _points, _x = arc.get_points(_curve)

        #    self.curves[_i] = _curve

        #    _result.append(_curve)

        #    self.trackers['Curves'][_i].update(_points)

        #    _j += 1

        #return _result

    def _validate_curve(self, curves):
        """
        Given a list of updated curves, validate them against themselves
        and adjoingin geometry
        """

        pass

        #_idx = self.drag.curves[:]

        #if not _idx:
        #    self.is_valid = True
        #    return

        ##append preceding and following curves if first / last curves
        ##aren't being updated
        #if _idx[0] > 0:
        #    _idx.insert(0, _idx[0] - 1)
        #    curves.insert(0, self.curves[_idx[0]])

        #elif _idx[-1] < len(self.curves) - 1:
        #    _idx.append(_idx[-1] + 1)
        #    curves.append(self.curves[_idx[-1]])

        #_styles = [CoinStyle.DEFAULT]*len(curves)

        ##validate curves against each other,
        ##ensuring PI distance >= sum  of curve tangents
        #for _i in range(0, len(curves) - 1):

        #    _c = [curves[_i], curves[_i + 1]]

        #    _tangents = [0.0, 0]

        #    if _c[0]['Type'] == 'Spiral':
        #        _tangents[0] = spiral.get_ordered_tangents(_c[0])[0]

        #    else:
        #        _tangents[0] = _c[0]['Tangent']

        #    if _c[1]['Type'] == 'Spiral':
        #        _tangents[1] = spiral.get_ordered_tangents(_c[1])[1]

        #    else:
        #        _tangents[1] = _c[1]['Tangent']

        #    if (_tangents[0] + _tangents[1])\
        #        > (_c[0]['PI'].distanceToPoint(_c[1]['PI'])):

        #        _styles[_i + 1] = CoinStyle.ERROR
        #        _styles[_i] = CoinStyle.ERROR

        ##do endpoint checks if the first or last curves are changing.
        #_x = []

        ##first curve is updating
        #if _idx[0] == 0:
        #    _x.append(0)

        ##last curve is updating
        #if _idx[-1] == len(self.curves) - 1:
        #    _x.append(-1)

        #for _i in _x:

        #    _c = curves[_i]
        #    _p = self.drag.pi[_i]
        #    _tangent = None

        #    #disable validation for spirals temporarily
        #    if _c['Type'] == 'Spiral':
                
        #        _tans = spiral.get_ordered_tangents(_c)
        #        _tangent = _tans[1]

        #        if _i == 0:
        #            _tangent = _tans[0]

        #    else:
        #        _tangent = _c['Tangent']

        #    if _styles[_i] != CoinStyle.ERROR:

        #        if _tangent > _c['PI'].distanceToPoint(_p):
        #            _styles[_i] = CoinStyle.ERROR

        #for _i, _c in enumerate(curves):
        #    self.trackers['Curves'][_idx[0] + _i].set_style(
        #        _styles[_i]
        #    )

        #self.is_valid = all([_v != CoinStyle.ERROR for _v in _styles])

    def finalize(self):
        """
        Cleanup the tracker
        """

        for _t in self.trackers.values():

            for _u in _t:
                _u.finalize()

        self.remove_node(self.groups['EDIT'], self.node)
        self.remove_node(self.groups['DRAG'], self.node)

        if self.callbacks:
            for _k, _v in self.callbacks.items():
                self.view.removeEventCallback(_k, _v)

            self.callbacks.clear()

        print('finalizing curve tracker....')
        super().finalize()
