# -*- coding: utf-8 -*-
#***********************************************************************
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
Task to edit an alignment
"""
import os

import PySide.QtGui as QtGui
import PySide.QtCore as QtCore

from pivy import coin

import FreeCAD as App
from FreeCAD import Vector
import FreeCADGui as Gui

import DraftTools

from .... import resources

from ...support import utils
from ...support.mouse_state import MouseState
from ...support.view_state import ViewState

from ...trackers.base_tracker import BaseTracker
from ...trackers.wire_tracker import WireTracker
from ...trackers.grid_tracker import GridTracker

from ...trackers.coin_style import CoinStyle

class SpriteSplitterTask:
    """
    Task to manage alignment editing
    """

    def __init__(self, doc):


        self.ui_path = resources.__path__[0] + '/ui/'
        self.ui = self.ui_path + 'sprite_splitter_task_panel.ui'

        self.form = None
        self.subtask = None

        self.panel = None
        self.doc = doc

        self.plane = None
        self.names = ['FreeCAD', self.doc.Name, 'Sprite Splitter']

        self.image = QtGui.QImage()

        self.cursor_trackers = [
            WireTracker(self.names), WireTracker(self.names)
        ]

        self.node = BaseTracker(self.names)

        self.node.insert_node(self.cursor_trackers[0].switch)
        self.node.insert_node(self.cursor_trackers[1].switch)

        #deselect existing selections
        Gui.Selection.clearSelection()

        self.callbacks = {
            'SoLocation2Event':
            ViewState().view.addEventCallback(
                'SoLocation2Event', self.mouse_event),

            'SoMouseButtonEvent':
            ViewState().view.addEventCallback(
                'SoMouseButtonEvent', self.button_event)
        }

        self.grid_tracker = GridTracker(self.names)

        DraftTools.redraw3DView()

    def setup(self):
        """
        Initiailze the task window and controls
        """
        _mw = utils.getMainWindow()

        form = _mw.findChild(QtGui.QWidget, 'TaskPanel')

        form.file_path = form.findChild(QtGui.QLineEdit, 'filename')
        form.pick_file = form.findChild(QtGui.QToolButton, 'pick_file')
        form.pick_file.clicked.connect(self.choose_file)

        self.form = form

    def load_file(self, file_name = None):
        """
        Load the image file onto a plane
        """

        if not file_name:
            file_name = self.form.file_path.text()

        if self.plane:
            self.doc.removeObject(self.plane.Name)

        self.doc.recompute()

        self.image.load(file_name)

        self.cursor_trackers[0].update(
            [Vector(-50.0, 0.0, 0.0), Vector(50.0, 0.0, 0.0)]
        )

        self.cursor_trackers[1].update(
            [Vector(0.0, -50.0, 0.0), Vector(0.0, 50.0, 0.0)]
        )

        for _v in self.cursor_trackers:
            _v.set_selectability(False)
            _v.coin_style = CoinStyle.DASHED

        _plane = self.doc.addObject('Image::ImagePlane', 'SpriteSheet')
        _plane.ImageFile = file_name
        _plane.XSize = 100.0
        _plane.YSize = 100.0
        _plane.Placement = App.Placement()

        App.ActiveDocument.recompute()

        Gui.Selection.addSelection(_plane)

        Gui.SendMsgToActiveView('ViewFit')

        self.plane = _plane

    def choose_file(self):
        """
        Open the file picker dialog and open the file
        that the user chooses
        """

        open_path = resources.__path__[0]

        filters = self.form.tr(
            'All files (*.*);; PNG files (*.png);; JPG files (*.jpg)'
        )

        #selected_filter = self.form.tr('LandXML files (*.xml)')

        file_name = QtGui.QFileDialog.getOpenFileName(
            self.form, 'Select File', open_path, filters
        )

        if not file_name[0]:
            return

        self.form.file_path.setText(file_name[0])
        self.load_file(file_name[0])

    def accept(self):
        """
        Accept the task parameters
        """

        self.finish()

        return None

    def reject(self):
        """
        Reject the task
        """

        self.finish()

        return None

    def key_event(self, arg):
        """
        SoKeyboardEvent callback
        """

        if arg['Key'] == 'ESCAPE':
            self.finish()

    def mouse_event(self, arg):
        """
        SoLocation2Event callback
        """

        if not self.plane:
            return

        MouseState().update(arg, ViewState().view.getCursorPos())

        #clear the matrix to force a refresh at the start of every mouse event
        ViewState().matrix = None

        if MouseState().object == self.plane.Name:

            self.cursor_trackers[0].update([
                Vector(-50.0, MouseState().coordinates.y, 0.0),
                Vector(50.0, MouseState().coordinates.y, 0.0)
            ])

            self.cursor_trackers[1].update([
                Vector(MouseState().coordinates.x, -50.0, 0.0),
                Vector(MouseState().coordinates.x, 50.0, 0.0)
            ])

    def button_event(self, arg):
        """
        SoMouseButtonEvent callback
        """

        if not self.plane:
            return

        MouseState().update(arg, ViewState().view.getCursorPos())

    def set_vobj_style(self, vobj, style):
        """
        Set the view object style based on the passed style tuple
        """

        vobj.LineColor = style[0]
        vobj.DrawStyle = style[1]

    def clean_up(self):
        """
        Callback to finish the command
        """

        self.finish()

        return True

    def finish(self):
        """
        Task cleanup
        """

        #re-enable selection
        ViewState().sg_root.getField("selectionRole").setValue(1)

        #close dialog
        Gui.Control.closeDialog()

        #remove the callback for action
        if self.callbacks:

            for _k, _v in self.callbacks.items():
                ViewState().view.removeEventCallback(_k, _v)

            self.callbacks.clear()
