# Copyright (C) 2007 - Nando Vieira
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# 2007-10-25 - Alexandre da Silva <simpsomboy@gmail.com>
# Obtained original program from Nando Vieira, and changed need use only
# python and mozembed, removed not used code


from gettext import gettext as _
import gedit
import gconf
import gtk
import gtk.gdk
import os
import pygtk
import webkit
import re

TMP_FILE = '/tmp/%s_rspec_mate.html' %  os.environ['USER']

ui_str = """
<ui>
    <menubar name="MenuBar">
        <menu name="ViewMenu" action="View">
            <menuitem name="RSpec" action="RSpec"/>
        </menu>
    </menubar>
</ui>
"""

DEBUG_NAME = 'RM_DEBUG'
DEBUG_TITLE = 'RSpec_Mate'

class BrowserPage(webkit.WebView):
    def __init__(self):
        webkit.WebView.__init__(self)

def debug(text, level=1):
    if os.environ.has_key(DEBUG_NAME):
        try:
            required_level = int(os.environ[DEBUG_NAME])

            if required_level >= level:
                print "[%s] %s" % (DEBUG_TITLE, text)
        except:
            print "[%s] debug error" % DEBUG_TITLE
# Link Pattern (in line)
lp = re.compile('([^/]*)(((\/[a-zA-Z0-9-_\.]+)+):(\d+):)(.*)$')

# Helper Functions
def get_line(line = ''):
    output = '%s<a href="%s">%s</a>%s\n'
    result = lp.match(line)
    if result:
        line = output % (result.group(1), file_link(result.group(3), int(result.group(5))), result.group(2), result.group(6))
    return line

def file_link(file, line=0):
    return "gedit:///%s?line=%d" % (file,line)

# TODO: Create a Configuragion dialog
class RspecPlugin(gedit.Plugin):
    def __init__(self):
        gedit.Plugin.__init__(self)
        self.instances = {}

    def activate(self, window):
        debug('activating plugin')
        self.instances[window] = RspecWindowHelper(self, window)

    def deactivate(self, window):
        debug('deactivating plugin')
        self.instances[window].deactivate()
        del self.instances[window]

    def update_ui(self, window):
        debug('updating ui')
        self.instances[window].update_ui()

class RspecWindowHelper:
    handlers = {}

    mt = re.compile(r'(?P<protocol>^gedit:\/\/)(?P<file>.*?)\?line=(?P<line>.*?)$')

    def __init__(self, plugin, window):
        self.window = window
        self.plugin = plugin
        self.rspec_window = None
        self._browser = None
        self.client = gconf.client_get_default()
        self.add_menu()

    def deactivate(self):
        debug('deactivate function called')

        self._browser = None
        self.rspec_window = None
        self.window = None
        self.plugin = None

    def add_menu(self):
        actions = [
            ('RSpec', gtk.STOCK_EDIT, _('RSpec Mate'), '<Super>r', _("Run current spec"), self.show_rspec_marks)
        ]

        action_group = gtk.ActionGroup("RSpecActions")
        action_group.add_actions(actions, self.window)

        self.manager = self.window.get_ui_manager()
        self.manager.insert_action_group(action_group, -1)
        self.manager.add_ui_from_string(ui_str)

    def get_root_directory(self):
        # get filebrowser plugin root
        fb_root = self.get_filebrowser_root()
        # get eddt plugin root
        eddt_root = self.get_eddt_root()

        if fb_root and fb_root != "" and fb_root is not None:
            title = "RSpec (Filebrowser integration)"
            root = fb_root
        elif eddt_root and eddt_root != "" and eddt_root is not None:
            title = "RSpec (EDDT integration)"
            root = eddt_root
        else:
            title = "RSpec (current directory)"
            root = os.path.dirname(__file__)

        return (root.replace("file://", ""), title)

    # taken from snapopen plugin
    def get_filebrowser_root(self):
        base = u'/apps/gedit-2/plugins/filebrowser/on_load'
        client = gconf.client_get_default()
        client.add_dir(base, gconf.CLIENT_PRELOAD_NONE)
        path = os.path.join(base, u'virtual_root')
        val = client.get(path)

        if val is not None:
            base = u'/apps/gedit-2/plugins/filebrowser'
            client = gconf.client_get_default()
            client.add_dir(base, gconf.CLIENT_PRELOAD_NONE)
            path = os.path.join(base, u'filter_mode')
            fbfilter = client.get(path).get_string()

        return val.get_string()

    # taken from snapopen plugin
    def get_eddt_root(self):
        base = u'/apps/gedit-2/plugins/eddt'
        client = gconf.client_get_default()
        client.add_dir(base, gconf.CLIENT_PRELOAD_NONE)
        path = os.path.join(base, u'repository')
        val = client.get(path)

        if val is not None:
            return val.get_string()

    def show_rspec_marks(self, *args):
        debug("opening list of rspec marks")

        # getting variables
        root, title = self.get_root_directory()

        debug("title: %s" % title)
        debug("root: %s" % root)

        # build script path
        rspec_script = os.path.join(os.path.dirname(__file__), "rspec_mate.py")

        debug("script: %s" % rspec_script)

        # call the script
        # FIXME: Replace local path to relative
        os.system("spec /home/cleitonfco/www/jus-cadastro/spec/models/user_spec.rb -f h:%s" % (TMP_FILE))
        #os.system('python %s "%s"' % (rspec_script, root))

        if self.rspec_window:
            self.rspec_window.show()
            self.rspec_window.grab_focus()
        else:
            self._browser = BrowserPage()
            self._browser.connect('navigation-requested', self.on_navigation_request)
            self.rspec_window = gtk.Window()
            self.rspec_window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
            self.rspec_window.resize(700,510)
            self.rspec_window.connect('delete_event', self.on_rspec_close)
            self.rspec_window.set_destroy_with_parent(True)
            self.rspec_window.add(self._browser)
            self.rspec_window.show_all()

        self.rspec_window.set_title(title)
        f = open(TMP_FILE)
        html_str = ''
        for l in f.readlines():
            html_str += get_line(l)
        self._browser.load_string(html_str, "text/html", "utf-8", "about:")
        # remove the temporary file after load to avoid any security issue
        os.unlink(TMP_FILE)

    def on_rspec_close(self, *args):
        self.rspec_window.hide()
        return True

    def on_navigation_request(self, page, frame, request):
        file_uri = None
        uri = request.get_uri()
        gp =  self.mt.search(uri)
        if gp:
            file_uri = 'file:///%s' % gp.group('file')
            line_number = gp.group('line')
            if file_uri:
                # Test if document is not already open
                for doc in self.window.get_documents():
                    if doc.get_uri() == file_uri:
                        tab = gedit.tab_get_from_document(doc)
                        view = tab.get_view()
                        self.window.set_active_tab(tab)
                        doc.goto_line(int(line_number))
                        view.scroll_to_cursor()
                        self.rspec_window.hide()
                        return 1
                # Document isn't open, create a new tab from uri
                self.window.create_tab_from_uri(file_uri,
                            gedit.encoding_get_current(),
                            int(line_number), False, True)
        else:
            print "(%s) not found" % file_uri
        self.rspec_window.hide()
        return 1

    def update(self, text=None):
        pass

    def update_ui(self):
        pass

    def set_data(self, name, value):
        self.window.get_active_tab().get_view().set_data(name, value)

    def get_data(self, name):
        return self.window.get_active_tab().get_view().get_data(name)
