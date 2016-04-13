# This file is part of gnome-tweak-tool.
# Copyright (c) 2012 Red Hat, Inc.
#
# gnome-tweak-tool is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# gnome-tweak-tool is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with gnome-tweak-tool.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#       Rui Matos

import logging

import gi
gi.require_version("GnomeDesktop", "3.0")
from gi.repository import Pango, Gtk, GnomeDesktop
from gtweak.gshellwrapper import GnomeShellFactory
from gtweak.tweakmodel import Tweak, TweakGroup
from gtweak.widgets import GSettingsSwitchTweak, build_label_beside_widget, GSettingsComboEnumTweak, GSettingsComboTweak, build_horizontal_sizegroup, ListBoxTweakGroup, Title
from gtweak.gsettings import GSettingsSetting, GSettingsMissingError, GSettingsFakeSetting

_shell = GnomeShellFactory().get_shell()
_shell_loaded = _shell is not None

class _XkbOption(Gtk.Expander, Tweak):
    def __init__(self, group_id, parent_settings, xkb_info, **options):
        try:
            desc = xkb_info.description_for_group(group_id)
        except AttributeError:
            desc = group_id
        Gtk.Expander.__init__(self)
        Tweak.__init__(self, desc, desc, **options)

        self.set_label(self.name)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        vbox.set_margin_start(15)
        self.add(vbox)

        self._multiple_selection = not group_id in { 'keypad', 'kpdl', 'caps', 'altwin', 'nbsp', 'esperanto' }
        self._group_id = group_id
        self._parent_settings = parent_settings
        self._xkb_info = xkb_info
        self._possible_values = []

        model_values = []
        for option_id in self._xkb_info.get_options_for_group(group_id):
            desc = self._xkb_info.description_for_option(group_id, option_id)
            model_values.append((option_id, desc))
            self._possible_values.append(option_id)

        self._checks = dict()
        for (val, name) in model_values:
            self._checks[val] = r = Gtk.CheckButton.new()
            vbox.add(r)
            l = Gtk.Label(label=name)
            l.set_line_wrap(True)
            r.add(l)
            r._changed_id = r.connect('toggled', self._on_check_changed)
            r._val = val

        self.widget_for_size_group = None
        self.reload()

    def reload(self):
        self._values = []
        for v in self._parent_settings.get_strv(TypingTweakGroup.XKB_GSETTINGS_NAME):
            if (v in self._possible_values):
                self._values.append(v)

        self._update_checks()

    def _update_checks(self):
        if len(self._values) > 0:
            self.set_label('<b>'+self.name+'</b>')
            self.set_use_markup(True)
        else:
            self.set_label(self.name)

        for r in self._checks.values():
            r.disconnect(r._changed_id)
            if r._val in self._values:
                r.set_active(True)
            else:
                r.set_active(False)
            r._changed_id = r.connect('toggled', self._on_check_changed)

    def _on_check_changed(self, r):
        active = r.get_active()
        if not self._multiple_selection and active:
            for v in self._values:
                self._parent_settings.setting_remove_from_list(TypingTweakGroup.XKB_GSETTINGS_NAME, v)

        if r._val in self._values and not active:
            self._parent_settings.setting_remove_from_list(TypingTweakGroup.XKB_GSETTINGS_NAME, r._val)
        elif active and not r._val in self._values:
            self._parent_settings.setting_add_to_list(TypingTweakGroup.XKB_GSETTINGS_NAME, r._val)

class TypingTweakGroup(Gtk.Box, TweakGroup):

    XKB_GSETTINGS_SCHEMA = "org.gnome.desktop.input-sources"
    XKB_GSETTINGS_NAME = "xkb-options"
    # These are configurable in gnome-control-center. grp_led is unsupported
    XKB_OPTIONS_BLACKLIST = {"lv3","Compose key","grp","grp_led"}

    def __init__(self):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=3)
        self._option_objects = []
        ok = False
        try:
            self._kbdsettings = GSettingsSetting(self.XKB_GSETTINGS_SCHEMA)
            self._kbdsettings.connect("changed::"+self.XKB_GSETTINGS_NAME, self._on_changed)
            self._xkb_info = GnomeDesktop.XkbInfo()
            ok = True
            self.loaded = True
        except GSettingsMissingError:
            logging.info("Typing missing schema %s" % self.XKB_GSETTINGS_SCHEMA)
            self.loaded = False            
        except AttributeError:
            logging.warning("Typing missing GnomeDesktop.gir with Xkb support")
            self.loaded = False
        finally:
            if ok:
                for opt in set(self._xkb_info.get_all_option_groups()) - self.XKB_OPTIONS_BLACKLIST:
                    obj = _XkbOption(opt, self._kbdsettings, self._xkb_info)
                    self._option_objects.append(obj)
                    self.pack_start(obj, False, False, 0)
        TweakGroup.__init__(self, _("Typing"), *self._option_objects)

    def _on_changed(self, *args):
        for obj in self._option_objects:
            obj.reload()

TWEAK_GROUPS = [
    TypingTweakGroup(),
]
