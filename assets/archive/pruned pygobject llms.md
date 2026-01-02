
### Create a Basic GTK Application with PyGObject

Source: https://github.com/gnome/pygobject/blob/main/docs/getting_started.rst

This Python script demonstrates how to create a simple 'Hello World' GUI application using GTK 4.0 bindings provided by PyGObject. It initializes a Gtk.Application, sets up a main window, and presents it upon activation. This example serves as a foundational step for building more complex GTK applications.

```python
import sys

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk


class MyApplication(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.example.MyGtkApplication")
        GLib.set_application_name('My Gtk Application')

    def do_activate(self):
        window = Gtk.ApplicationWindow(application=self, title="Hello World")
        window.present()


app = MyApplication()
exit_status = app.run(sys.argv)
sys.exit(exit_status)
```

--------------------------------

### Create a Basic GTK4 Application Window with PyGObject

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/introduction.rst

This Python example initializes a GTK4 application using `gi.require_version` and defines a `Gtk.Application` subclass. It connects to the 'activate' signal to create and display an empty 200x200 pixel `Gtk.ApplicationWindow`, then starts the application's main loop.

```Python
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gio
import sys

class MyApp(Gtk.Application):
    def __init__(self, **kwargs):
        super().__init__(application_id="org.example.MyApp", **kwargs)
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        win = Gtk.ApplicationWindow(application=app, default_width=200, default_height=200)
        win.present()

if __name__ == '__main__':
    app = MyApp()
    app.run(sys.argv)
```

--------------------------------

### Build an Extended GTK4 'Hello World' Application with PyGObject

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/introduction.rst

This Python example extends the basic GTK4 application by subclassing `Gtk.ApplicationWindow` to create a custom window. It adds a `Gtk.Button` that, when clicked, prints 'Hello World' to the console and closes the window. The application uses `Gtk.Application` for lifecycle management.

```Python
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gio
import sys

class MyWindow(Gtk.ApplicationWindow):
    def __init__(self, app, **kwargs):
        super().__init__(application=app, title="Hello World", **kwargs)

        button = Gtk.Button(label="Click Me")
        button.connect("clicked", self.on_button_clicked)
        self.set_child(button)

    def on_button_clicked(self, widget):
        print("Hello World")
        self.close()

class MyApp(Gtk.Application):
    def __init__(self, **kwargs):
        super().__init__(application_id="org.example.HelloWorld", **kwargs)
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        win = MyWindow(app)
        win.present()

if __name__ == '__main__':
    app = MyApp()
    app.run(sys.argv)
```

--------------------------------

### Basic GTK Application with PyGObject

Source: https://github.com/gnome/pygobject/blob/main/docs/index.rst

This snippet demonstrates how to create a basic 'Hello World' GTK application using PyGObject. It initializes a GTK application, sets its ID and name, and creates a simple window that is presented upon activation. This example illustrates the fundamental structure for a PyGObject-based GUI application.

```python
import sys

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk


class MyApplication(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.example.MyGtkApplication")
        GLib.set_application_name("My Gtk Application")

    def do_activate(self):
        window = Gtk.ApplicationWindow(application=self, title="Hello World")
        window.present()


app = MyApplication()
exit_status = app.run(sys.argv)
sys.exit(exit_status)
```

--------------------------------

### Display a Minimal GTK4 Window without Gtk.Application in Python

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/introduction.rst

This Python snippet demonstrates creating a basic GTK4 window without relying on `Gtk.Application`. It manually iterates the GLib main context to keep the window open until all top-level windows are closed. This approach is generally recommended only for specific use cases like testing.

```Python
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import GLib, Gtk

win = Gtk.Window()
win.present()

while (len(Gtk.Window.get_toplevels()) > 0):
    GLib.MainContext.default().iteration(True)
```

--------------------------------

### Adw.Application Class Overview

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/libadwaita/application.rst

Documents the core `Adw.Application` class, its inheritance from `Gtk.Application`, and its automatic initialization of the Adwaita library, ensuring proper setup of translations, types, themes, icons, and stylesheets.

```APIDOC
Adw.Application:
  Extends: Gtk.Application
  Purpose: Eases tasks related to creating applications for GNOME.
  Automatic Initialization: Calls Adw.init() upon instantiation, setting up translations, types, themes, icons, and stylesheets.
```

--------------------------------

### Set GObject Properties During Initialization in Python

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/basics.rst

Properties can be set as keyword arguments when creating a GObject instance. This example creates a right-aligned Gtk.Label with 'Hello World' text.

```python
label = Gtk.Label(label='Hello World', halign=Gtk.Align.END)
```

--------------------------------

### PyGObject Gtk.Grid Layout Example

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/layout-widgets.rst

An example demonstrating the use of Gtk.Grid for arranging widgets, typically showing how to attach children with specific column and row spans.

```Python
# Code for Gtk.Grid layout example (from examples/layout_grid.py)
# This content is typically a Python script demonstrating Gtk.Grid usage.
# Example: grid.attach(widget, left, top, width, height)
```

--------------------------------

### PyGObject Gtk.FlowBox Layout Example

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/layout-widgets.rst

An example demonstrating the use of Gtk.FlowBox for arranging widgets in a flowing grid, typically showing how to add and manage flow box children.

```Python
# Code for Gtk.FlowBox layout example (from examples/layout_flowbox.py)
# This content is typically a Python script demonstrating Gtk.FlowBox usage.
# Example: flowbox.append(Gtk.Button("Click Me"))
```

--------------------------------

### Import GObject from PyGObject

Source: https://github.com/gnome/pygobject/blob/main/docs/devguide/dev_environ.rst

This Python snippet demonstrates how to import the GObject module from the gi.repository, which is the entry point for accessing GTK and GLib functionalities in PyGObject applications. It's a fundamental step to start using PyGObject.

```python
from gi.repository import GObject
```

--------------------------------

### PyGObject Gtk.ListBox Layout Example

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/layout-widgets.rst

An example demonstrating the use of Gtk.ListBox for creating a scrollable list of items, typically showing how to add and manage list rows.

```Python
# Code for Gtk.ListBox layout example (from examples/layout_listbox.py)
# This content is typically a Python script demonstrating Gtk.ListBox usage.
# Example: listbox.append(Gtk.Label("Item"))
```

--------------------------------

### Getting and Setting GObject Properties in Python

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/api/properties.rst

Illustrates the use of `get_property()` and `set_property()` methods to retrieve and modify property values of a `GObject` instance. The example demonstrates that both underscore and hyphenated property names can be used with `get_property()`, but `set_property()` typically expects the Pythonic underscore version if the constructor used it.

```pycon
>>> app = Gio.Application(application_id="foo.bar")
>>> app
<Gio.Application object at 0x7f7499284fa0 (GApplication at 0x564b571e7c00)>
>>> app.get_property("application_id")
'foo.bar'
>>> app.set_property("application_id", "a.b")
>>> app.get_property("application-id")
'a.b'
```

--------------------------------

### Define a GObject Signal Callback Function

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/basics.rst

This example shows the basic structure for defining a callback function that will be executed when a signal is emitted. The callback typically receives the GObject instance that triggered the signal and any optional data passed during connection. Subsequent arguments depend on the specific signal.

```python
def on_event(gobject, data):
    ...

my_object.connect('event', on_event, data)
```

--------------------------------

### Using Gtk.PopoverMenu with Gio.MenuModel in PyGObject

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/popovers.rst

This example demonstrates how to create and display a `Gtk.PopoverMenu` from a `Gio.MenuModel`, often used in conjunction with `Gtk.MenuButton`. It illustrates how to define menu actions and associate them with the popover, providing a dynamic and structured way to present menu options to the user.

```Python
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio

class MenuPopoverWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Menu Popover Example")
        self.set_default_size(400, 300)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.set_child(main_box)

        # Create a Gio.MenuModel
        menu_model = Gio.Menu.new()
        menu_model.append("New", "app.new")
        menu_model.append("Open", "app.open")
        menu_model.append("Save", "app.save")
        menu_model.append("Quit", "app.quit")

        # Create a Gtk.MenuButton and attach the menu model
        menu_button = Gtk.MenuButton(label="File Actions")
        menu_button.set_menu_model(menu_model)
        main_box.append(menu_button)

        # Add actions to the application
        action_new = Gio.SimpleAction.new("new", None)
        action_new.connect("activate", self.on_menu_action, "New")
        app.add_action(action_new)

        action_open = Gio.SimpleAction.new("open", None)
        action_open.connect("activate", self.on_menu_action, "Open")
        app.add_action(action_open)

        action_save = Gio.SimpleAction.new("save", None)
        action_save.connect("activate", self.on_menu_action, "Save")
        app.add_action(action_save)

        action_quit = Gio.SimpleAction.new("quit", None)
        action_quit.connect("activate", self.on_quit_action)
        app.add_action(action_quit)

    def on_menu_action(self, action, param, action_name):
        print(f"Menu action '{action_name}' activated!")

    def on_quit_action(self, action, param):
        self.get_application().quit()

class MenuPopoverApplication(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.example.MenuPopoverApp",
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = self.get_active_window()
        if not win:
            win = MenuPopoverWindow(self)
        win.present()

if __name__ == "__main__":
    app = MenuPopoverApplication()
    app.run(None)
```

--------------------------------

### Displaying an Image with Gtk.Picture in Python

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/display-widgets/picture.rst

This Python example demonstrates how to create a `Gtk.Picture` widget, load an image (either from a file or as a resource), and configure its display properties such as `content_fit` and alignment within a `Gtk.ApplicationWindow`. This snippet requires GTK 4.8 or newer.

```Python
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio

class PictureWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Gtk.Picture Example")
        self.set_default_size(400, 300)

        # Create a Gtk.Picture from a filename or resource
        # For a real application, ensure 'images/example.png' exists
        # or embed it as a GIO resource.
        try:
            picture = Gtk.Picture.new_for_filename("images/example.png")
        except Exception:
            print("Could not load 'images/example.png'. Using a placeholder.")
            # Fallback: create an empty picture or use a resource if available
            # Example for resource (requires Gio.Resource setup):
            # resource_path = "/org/example/app/images/default.png"
            # picture = Gtk.Picture.new_for_resource(resource_path)
            picture = Gtk.Picture()

        # Set content fit (e.g., SCALE_DOWN, FILL, etc.)
        picture.set_content_fit(Gtk.ContentFit.SCALE_DOWN)

        # Set alignment within the widget's allocated space
        picture.set_halign(Gtk.Align.CENTER)
        picture.set_valign(Gtk.Align.CENTER)

        self.set_child(picture)

class Application(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.gtk.example.Picture",
                         flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.window = None

    def do_activate(self):
        if not self.window:
            self.window = PictureWindow(self)
        self.window.present()

    def do_startup(self):
        Gtk.Application.do_startup(self)

if __name__ == "__main__":
    app = Application()
    app.run(None)
```

--------------------------------

### Defining Custom GObject Properties with Decorator in Python

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/api/properties.rst

Presents a Python example demonstrating how to use the `GObject.Property` decorator to define custom properties within a `GObject.Object` subclass. It shows examples of both a read-only property and a read-write integer property with a setter method.

```python
class AnotherObject(GObject.Object):
    value = 0

    @GObject.Property
    def prop_pyobj(self):
        """Read only property."""

        return object()

    @GObject.Property(type=int)
    def prop_gint(self):
        """Read-write integer property."""

        return self.value

    @prop_gint.setter
    def prop_gint(self, value):
        self.value = value
```

--------------------------------

### Define Gtk.Template with XML String and Basic Widgets

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/gtk_template.rst

This example demonstrates the fundamental usage of Gtk.Template by embedding the GtkBuilder UI definition directly as a string. It shows how to decorate a Gtk.Box subclass with @Gtk.Template, define the __gtype_name__, declare a Gtk.Template.Child for a GtkButton, and connect a signal handler using @Gtk.Template.Callback.

```python
xml = """\
<interface>
  <template class="example1" parent="GtkBox">
    <child>
      <object class="GtkButton" id="hello_button">
        <property name="label">Hello World</property>
        <signal name="clicked" handler="hello_button_clicked" swapped="no" />
      </object>
    </child>
  </template>
</interface>
"""

@Gtk.Template(string=xml)
class Foo(Gtk.Box):
    __gtype_name__ = "example1"

    hello_button = Gtk.Template.Child()

    @Gtk.Template.Callback()
    def hello_button_clicked(self, *args):
        pass
```

--------------------------------

### Subclassing GObject with Constructor Arguments

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/subclassing.rst

This example illustrates how to pass arguments to the parent GObject's constructor using super().__init__(). This allows for initializing or modifying properties of the parent GObject, such as setting a window title during instantiation.

```python
class MyWindow(Gtk.Window):

    def __init__(self):
        super().__init__(title='Custom title')
```

--------------------------------

### Bind GObject Properties with Custom Transformations in Python

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/basics.rst

Demonstrates using `bind_property` with custom transformation functions (`transform_to`, `transform_from`) to handle incompatible property types or apply logic during binding. This example converts between integer and boolean types bidirectionally.

```python
def transform_to(_binding, value):
   return bool(value)  # Return int converted to a bool

def transform_from(_binding, value):
    return int(value)  # Return bool converted to a int

source.bind_property(
    'int_prop',
    target,
    'bool_prop',
    GObject.BindingFlags.BIDIRECTIONAL,
    transform_to,
)
```

--------------------------------

### PyGObject Automatic Type Mappings Reference

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/api/basic_types.rst

A reference guide to how PyGObject automatically converts various Glib and C data types into their corresponding Python equivalents, covering number, text, and common collection types.

```APIDOC
PyGObject Type Mappings:
- Glib integer types <-> Python int, float (OverflowError for out-of-range values)
- Text types <-> Python str
- GList <-> Python list
- GSList <-> Python list
- GHashTable <-> Python dict
- arrays <-> Python list
```

--------------------------------

### Synchronous File Content Loading Example

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/asynchronous.rst

This snippet presents a synchronous approach to loading file contents from a URI using `Gio.File.load_contents()`. It serves as a comparison to asynchronous methods, demonstrating a blocking operation that fetches data directly and handles potential `GLib.GError` exceptions.

```python
file = Gio.File.new_for_uri(
    "https://developer.gnome.org/documentation/tutorials/beginners.html"
)
try:
    status, contents, etag_out = file.load_contents(None)
except GLib.GError:
    print("Error!")
else:
    print(contents)
```

--------------------------------

### Ensuring Specific Library Versions in PyGObject

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/imports.rst

To guarantee that a specific version of a library is used, this example shows how to employ `gi.require_version()` before importing the desired modules like Gtk and GLib.

```Python
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('GLib', '2.0')
from gi.repository import Gtk, GLib
```

--------------------------------

### Set Gtk.Label Markup with Hyperlink

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/display-widgets/label.rst

This Python example demonstrates how to set the text of a `Gtk.Label` using Pango Markup to include a clickable hyperlink. The `set_markup` method is used, allowing HTML-like `<a>` tags with `href` for the URL and `title` for the tooltip. This enables interactive text display within the label.

```Python
label.set_markup("Go to <a href=\"https://www.gtk.org\" title=\"Our website\">GTK+ website</a> for more")
```

--------------------------------

### Subclassing GObject.Object in Python

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/api/gobject.rst

Demonstrates the basic process of subclassing `GObject.Object` in Python. This operation automatically creates a new `GObject.GType` that is linked to the Python class, making it compatible with GObject APIs. The example shows how to instantiate the subclass and inspect its automatically generated `__gtype__` and `__gtype__.name`.

```Python
>>> from gi.repository import GObject
>>> class A(GObject.Object):
...     pass
... 
>>> A()
<__main__.A object at 0x7f9113fc3280 (__main__+A at 0x559d9861acc0)>
>>> A.__gtype__
<GType __main__+A (94135355573712)>
>>> A.__gtype__.name
'__main__+A'
>>> 
```

--------------------------------

### Gtk.Template with Custom Subclass as XML Object

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/gtk_template.rst

This example shows how to integrate a custom Gtk.Button subclass (HelloButton) directly into the Gtk.Template XML definition. It highlights that any subclass declaring a __gtype_name__ can be instantiated as an object within the UI template, allowing for reusable custom widgets.

```python
xml = """\
<interface>
  <template class="example3" parent="GtkBox">
    <child>
      <object class="ExampleButton" id="hello_button">
        <property name="label">Hello World</property>
        <signal name="clicked" handler="hello_button_clicked" swapped="no" />
      </object>
    </child>
  </template>
</interface>
"""


class HelloButton(Gtk.Button):
    __gtype_name__ = "ExampleButton"


@Gtk.Template(string=xml)
class Foo(Gtk.Box):
    __gtype_name__ = "example3"

    hello_button = Gtk.Template.Child()

    @Gtk.Template.Callback()
    def hello_button_clicked(self, *args):
        pass
```

--------------------------------

### GObject.Object.weak_ref Method

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/api/weakrefs.rst

Registers a callback to be called when the underlying GObject gets finalized. The callback will receive the given `user_data`. To unregister the callback, call the `unref()` method of the returned GObjectWeakRef object.

```APIDOC
GObject.Object.weak_ref(callback, *user_data)
  Description: Registers a callback to be called when the underlying GObject gets finalized.
  Parameters:
    callback:
      Type: callable
      Description: A callback which will be called when the object is finalized
    user_data:
      Description: User data that will be passed to the callback
  Returns: GObjectWeakRef
```

--------------------------------

### Verifying Instance Consistency with GObject Subclasses and Gio.ListStore

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/api/gobject.rst

Demonstrates how `GObject.Object` ensures instance consistency when working with GObject containers like `Gio.ListStore`. The example shows creating a `Gio.ListStore` for a custom `GObject.Object` subclass, appending an instance, and then retrieving it. It verifies that the Python instance returned from the store is precisely the same object that was originally added, highlighting the robust wrapping mechanism.

```Python
>>> from gi.repository import GObject, Gio
>>> class A(GObject.Object):
...     pass
... 
>>> store = Gio.ListStore.new(A)
>>> instance = A()
>>> store.append(instance)
>>> store.get_item(0) is instance
True
>>> 
```

--------------------------------

### Create GObject Signals using @GObject.Signal Decorator

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/subclassing.rst

This example illustrates how to define new signals in a PyGObject class using the `@GObject.Signal` decorator. It shows how to create signals with and without arguments, specify signal flags (e.g., `RUN_LAST`), and connect Python functions as callbacks. The snippet also demonstrates how to emit the defined signals.

```Python
from gi.repository import GObject

class MyObject(GObject.Object):

    def __init__(self):
        super().__init__()

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=(int,))
    def arg_signal(self, number):
        """Called every time the signal is emitted"""
        print('number:', number)

    @GObject.Signal
    def noarg_signal(self):
        """Called every time the signal is emitted"""
        print('noarg_signal')

    
my_object = MyObject()

def signal_callback(object_, number):
    """Called every time the signal is emitted until disconnection"""
    print(object_, number)

my_object.connect('arg_signal', signal_callback)
my_object.emit('arg_signal', 100)  # emit the signal "arg_signal", with the
                                   # argument 100

my_object.emit('noarg_signal')
```

--------------------------------

### Create and Manage Asyncio Tasks with GLib Event Loop

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/asynchronous.rst

After configuring the GLib event loop policy, this example shows how to retrieve the active event loop and create an asynchronous task using `loop.create_task()`. It highlights the process of scheduling a coroutine for execution within the GLib-integrated `asyncio` environment.

```python
loop = policy.get_event_loop()


async def do_some_work():
    await asyncio.sleep(2)
    print("Done working!")


task = loop.create_task(do_some_work())
```

--------------------------------

### Define and Emit Custom GObject Signals (PyGObject)

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/api/signals.rst

Provides a practical example of defining custom signals within a `GObject.Object` subclass using the `GObject.Signal` decorator. It demonstrates how to connect a handler to a custom signal and then emit the signal with arguments.

```python
class MyClass(GObject.Object):

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, return_type=bool,
                    arg_types=(object,),
                    accumulator=GObject.signal_accumulator_true_handled)
    def test(self, *args):
        print("Handler", args)

    @GObject.Signal
    def noarg_signal(self):
        print("noarg_signal")

instance = MyClass()

def test_callback(inst, obj):
    print "Handled", inst, obj
    return True

instance.connect("test", test_callback)
instance.emit("test", object())

instance.emit("noarg_signal")
```

--------------------------------

### Creating and Displaying a Custom Gtk.Popover in PyGObject

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/popovers.rst

This example demonstrates how to create a custom `Gtk.Popover`, set its child widget, and attach it to a parent widget. It shows how to configure its position and visibility, and how to open and hide it programmatically. The popover is typically used for displaying contextual information or custom controls.

```Python
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio

class PopoverWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Popover Example")
        self.set_default_size(400, 300)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.set_child(main_box)

        button = Gtk.Button(label="Show Popover")
        main_box.append(button)

        # Create a custom popover
        self.popover = Gtk.Popover()
        self.popover.set_parent(button) # Attach to the button

        popover_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        popover_content.set_margin_start(10)
        popover_content.set_margin_end(10)
        popover_content.set_margin_top(10)
        popover_content.set_margin_bottom(10)

        popover_content.append(Gtk.Label(label="This is a custom popover!"))
        popover_content.append(Gtk.Button(label="Close Popover",
                                          halign=Gtk.Align.CENTER))
        self.popover.set_child(popover_content)

        # Connect signals
        button.connect("clicked", self.on_button_clicked)
        popover_content.get_children()[1].connect("clicked", self.on_close_popover_clicked)

    def on_button_clicked(self, button):
        self.popover.popup()

    def on_close_popover_clicked(self, button):
        self.popover.hide()

class PopoverApplication(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.example.PopoverApp",
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = self.get_active_window()
        if not win:
            win = PopoverWindow(self)
        win.present()

if __name__ == "__main__":
    app = PopoverApplication()
    app.run(None)
```

--------------------------------

### Catching a specific GLib.Error in Python

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/api/error_handling.rst

This example demonstrates how to catch a `GLib.Error` in Python when performing file operations with `Gio.File`. It shows how to use `err.matches()` with `Gio.io_error_quark()` and `Gio.IOErrorEnum.NOT_FOUND` to specifically handle a 'file not found' error, re-raising other error types.

```Python
>>> from gi.repository import GLib, Gio
>>> f = Gio.File.new_for_path('missing-path')
>>> try:
...     f.read()
... except GLib.Error as err:
...     if err.matches(Gio.io_error_quark(), Gio.IOErrorEnum.NOT_FOUND):
...         print('File not found')
...     else:
...         raise
File not found
```

--------------------------------

### Gtk.Editable Interface Properties and Signals

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/controls/entries.rst

The Gtk.Editable interface defines common properties and signals for widgets that allow text editing, such as Gtk.Entry. It provides mechanisms to get and set text, limit character count, and control editability.

```APIDOC
Gtk.Editable:
  Interface for widgets that allow text editing.
  Properties:
    text (str): The contents of the entry.
    max_width_chars (int): The maximum number of characters the entry can hold.
    editable (bool): Whether the entry is editable.
  Signals:
    changed: Emitted when the text in the entry changes.
```

--------------------------------

### Control GObject Property Access with ParamFlags

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/subclassing.rst

GObject properties can have their read and write access controlled using GObject.ParamFlags. This example demonstrates setting properties as READABLE (read-only) or WRITABLE (write-only), providing fine-grained control over property visibility and modification.

```python
foo = GObject.Property(type=str, flags=GObject.ParamFlags.READABLE) # not writable
bar = GObject.Property(type=str, flags=GObject.ParamFlags.WRITABLE) # not readable
```

--------------------------------

### List Available GObject Properties with `props` in Python

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/basics.rst

Shows how to use the `props` attribute to access and list all available properties for a GObject instance, providing a more Pythonic way of interacting with properties.

```python
widget = Gtk.Box()
print(dir(widget.props))
```

--------------------------------

### Working with Gtk.Align Enums in PyGObject

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/api/flags_enums.rst

This example illustrates the usage of Gtk.Align, a subclass of GObject.GEnum. It covers accessing specific enum members, converting an enum member to its integer value, instantiating an enum object from its integer representation, and checking if an enum member is an instance of its enum type.

```pycon
>>> Gtk.Align.CENTER
<Align.CENTER: 3>
>>> int(Gtk.Align.CENTER)
3
>>> int(Gtk.Align.END)
2
>>> Gtk.Align(1)
<Align.START: 1>
>>> isinstance(Gtk.Align.CENTER, Gtk.Align)
True
```

--------------------------------

### Python Threading with GTK Progress Bar

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/threading.rst

This example demonstrates how to run a background task in a separate Python thread while updating a GTK progress bar on the main UI thread. It uses `GLib.idle_add` to safely schedule UI updates, ensuring the application remains responsive during the simulated blocking operation (`time.sleep`).

```python
import threading
import time
import gi

gi.require_version('Gtk', '4.0')
from gi.repository import GLib, Gtk, GObject


class Application(Gtk.Application):

    def do_activate(self):
        window = Gtk.ApplicationWindow(application=self)
        self.progress = Gtk.ProgressBar(show_text=True)

        window.set_child(self.progress)
        window.present()

        thread = threading.Thread(target=self.example_target)
        thread.daemon = True
        thread.start()

    def update_progress(self, i):
        self.progress.pulse()
        self.progress.set_text(str(i))
        return False

    def example_target(self):
        for i in range(50):
            GLib.idle_add(self.update_progress, i)
            time.sleep(0.2)


app = Application()
app.run()
```

--------------------------------

### Demonstrating PyGObject Integer Range Handling with GLib.random_int_range

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/api/basic_types.rst

This snippet illustrates how PyGObject maps glib integer types to Python `int` and `float`. It specifically shows an `OverflowError` when attempting to convert a Python integer that exceeds the maximum range of a glib integer type, using `GLib.random_int_range` as an example.

```pycon
>>> GLib.random_int_range(0, 2**31-1)
1684142898
>>> GLib.random_int_range(0, 2**31)
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
OverflowError: 2147483648 not in range -2147483648 to 2147483647
>>> 
```

--------------------------------

### Define GObject Properties with Minimum and Maximum Values

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/subclassing.rst

Numeric GObject properties can enforce value constraints by specifying minimum and maximum parameters during their definition. This ensures that assigned values fall within a defined range, and attempts to set values outside this range will result in an error, as shown in the example.

```python
class AnotherObject(GObject.Object):
        value = 0

        @GObject.Property(type=int, minimum=0, maximum=100)
        def prop_int(self):
            """Integer property with min-max.'"""
            return self.value

        @prop_int.setter
        def prop_int(self, value):
            self.value = value


    my_object = AnotherObject()
    my_object.prop_int = 200  # This will fail
```

--------------------------------

### Setting Explicit GType Name for Custom GEnum in PyGObject

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/api/flags_enums.rst

This example illustrates how to explicitly set the GType name for a custom enumeration type when subclassing GObject.GEnum. By providing a '__gtype_name__' attribute within the class definition, you can control the name registered with the GType system, as verified by accessing the '__gtype__.name' attribute.

```pycon
>>> from gi.repository import GObject
>>> class MyEnum(GObject.GEnum):
...     __gtype_name__ = "MyEnum"
...     ONE = 1
...
>>> MyEnum.__gtype__
<GType MyEnum (767309744)>
```

--------------------------------

### GTK Application Core API Reference

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/application.rst

This section provides an API reference for key classes, interfaces, and methods related to `Gtk.Application`, `Gio.Action`, and `Gio.Menu` within the `gi.repository` module, detailing their purpose, properties, and relevant methods for building GTK applications.

```APIDOC
gi.repository:
  Module containing GObject introspection bindings for GTK and GLib.

Gtk.Application:
  Base class for GTK applications, handling lifecycle, instances, D-Bus, and more.
  Methods:
    set_menubar(menu: Gio.Menu): Sets the application's menubar from a Gio.Menu.
    set_accels_for_action(action_name: str, accels: list[str]): Sets keyboard accelerators for a given action.

Gtk.ApplicationWindow:
  A Gtk.Window subclass designed for use as a main application window, providing additional features.

Gtk.Window:
  Base class for top-level windows.

Gio.Action:
  An interface for exposing a named task that can be activated or have its state changed.
  Properties:
    name: str (The unique name of the action)
    enabled: bool (Whether the action is currently enabled)
    state: GLib.Variant (The current state of the action, if stateful)

Gio.SimpleAction:
  A basic implementation of Gio.Action.

Gio.MenuItem:
  A widget that represents an item in a menu. Supports setting an action name.

Gtk.Actionable:
  An interface for widgets that can be associated with an action.
  Implementations:
    Gtk.Button: A button widget that can activate an action.

Gio.ActionGroup:
  A collection of Gio.Action objects.
  Methods:
    Gtk.Widget.insert_action_group(name: str, group: Gio.ActionGroup): Adds an action group to a widget, typically prefixing action names (e.g., "win.").

Gio.Menu:
  A model for a menu, typically defined in XML, referencing actions.

Gio.Resource:
  A way to bundle application data, including UI definitions like menus, into a single file.

Gio.ApplicationFlags:
  Flags to control Gio.Application behavior.
  Values:
    HANDLES_COMMAND_LINE: Allows custom handling of command-line arguments in do_command_line().
    HANDLES_OPEN: Allows handling of file arguments in do_open().
    NON_UNIQUE: Allows multiple instances of the application to run simultaneously.

Gio.Application:
  (Re-listing for methods related to flags)
  Methods:
    do_command_line(command_line: Gio.ApplicationCommandLine): Callback for custom command-line handling when HANDLES_COMMAND_LINE is set.
    add_main_option(long_name: str, short_name: int, flags: GLib.OptionFlags, arg: GLib.OptionArg, description: str, arg_description: str): Adds a custom command-line option.
    do_open(files: list[Gio.File], hint: str): Callback for handling file arguments when HANDLES_OPEN is set.
```

--------------------------------

### Initialize GObject in Python

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/basics.rst

GObjects are initialized like any other Python class. This snippet demonstrates creating a basic Gtk.Label instance.

```python
label = Gtk.Label()
```

--------------------------------

### Gtk.Image Widget and Image Loading API Reference

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/display-widgets/image.rst

Comprehensive API documentation for the Gtk.Image class, including its general description, how it displays images, and the primary methods and properties used to load image data from various sources like files, icon names, and GIO resources.

```APIDOC
Class: Gtk.Image
  Description: A widget designed to display various kinds of objects as an image.
  Display Behavior: Typically displays images as icons, with their size determined by the application.
  Contrast with Gtk.Picture: For displaying images at their actual size, refer to the /tutorials/gtk4/display-widgets/picture documentation.

Method: Gtk.Image.new_from_file
  Purpose: Convenience function to load a Gdk.Texture from a file and display it.
  Usage: Gtk.Image.new_from_file(filename: str)

Method: Gtk.Image.new_from_icon_name
  Purpose: Creates a Gtk.Image displaying an image from a named icon.
  Usage: Gtk.Image.new_from_icon_name(icon_name: str)

Method: Gtk.Image.new_from_resource
  Purpose: Used when an application embeds image data directly, avoiding external files.
  Usage: Gtk.Image.new_from_resource(resource_path: str)
  Related: Gio.Resource (for details on embedding resources)

Property: Gtk.Image.props.resource
  Purpose: Attribute to access or set the Gio.Resource associated with the image.
  Usage: Gtk.Image.props.resource
```

--------------------------------

### GObject.Object Class and Property Methods

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/basics.rst

Core GObject class providing fundamental methods for property interaction. `get_property` and `set_property` allow generic access to properties by name, while `bind_property` enables linking properties between objects.

```APIDOC
GObject.Object:
  get_property(property_name: str) -> Any
    property_name: The name of the property to retrieve.
    Returns: The value of the specified property.

  set_property(property_name: str, value: Any) -> None
    property_name: The name of the property to set.
    value: The new value for the property.

  bind_property(source_property: str, target_object: GObject.Object, target_property: str, flags: GObject.BindingFlags, transform_to: Callable = None, transform_from: Callable = None) -> GObject.Binding
    source_property: The name of the property on the source object to bind.
    target_object: The target GObject instance.
    target_property: The name of the property on the target object to bind.
    flags: A GObject.BindingFlags enum controlling the binding behavior.
    transform_to: Optional function to transform the source value before setting it on the target.
    transform_from: Optional function to transform the target value before setting it on the source (for bidirectional bindings).
    Returns: A GObject.Binding instance representing the created binding.
```

--------------------------------

### Manage GObject Properties with `set_property` and `get_property` in Python

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/basics.rst

Demonstrates using the generic `GObject.Object.set_property` and `GObject.Object.get_property` methods to interact with GObject properties. This is useful for GObject subclasses without specific getters/setters.

```python
label = Gtk.Label()
label.set_property('label', 'Hello World')
label.set_property('halign', Gtk.Align.END)
print(label.get_property('label'))
```

--------------------------------

### Instantiating GObject with Properties in Python

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/api/properties.rst

Shows how to initialize a `GObject.Object` subclass, such as `Gio.Application`, by passing property values as keyword arguments to its constructor. It highlights the Pythonic conversion of hyphenated property names to underscores.

```pycon
>>> app = Gio.Application(application_id="foo.bar")
```

--------------------------------

### Adwaita Automatic Stylesheet Loading

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/libadwaita/application.rst

Explains how `Adw.Application` automatically loads stylesheets from `Gio.Resource` based on system appearance settings exposed by `Adw.StyleManager`, eliminating the need for manual loading.

```APIDOC
Stylesheet Loading Mechanism:
  Trigger: Use of Gio.Resource in conjunction with Adw.Application.
  Automation: Adw.Application automatically loads stylesheets.
  Dynamic Loading: Loads matching stylesheets based on Adw.StyleManager.props.dark and Adw.StyleManager.props.high_contrast.
  Stylesheet Files:
    - style.css: Base styles.
    - style-dark.css: Applied when Adw.StyleManager.props.dark is True.
    - style-hc.css: Applied when Adw.StyleManager.props.high_contrast is True.
    - style-hc-dark.css: Applied when both Adw.StyleManager.props.high_contrast and Adw.StyleManager.props.dark are True.
```

--------------------------------

### Connect a GObject Signal to a Callback

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/basics.rst

This snippet demonstrates how to connect a GObject instance to a specific event signal. The `gobject.connect` method takes the event name, a callback function, and optional data, returning a unique handler ID for the connection.

```python
handler_id = gobject.connect('event', callback, data)
```

--------------------------------

### GObject.Binding Class

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/basics.rst

Represents an active property binding created by `GObject.Object.bind_property`.

```APIDOC
GObject.Binding:
  # This class represents a property binding.
  # It is returned by GObject.Object.bind_property.
```

--------------------------------

### Set GObject Properties Using Setter Methods in Python

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/basics.rst

This snippet shows the equivalent way to set GObject properties using their dedicated setter methods after initialization.

```python
label = Gtk.Label()
label.set_label('Hello World')
label.set_halign(Gtk.Align.END)
```

--------------------------------

### GObject Signal System API Reference

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/subclassing.rst

API documentation for key components involved in creating, emitting, and handling signals in PyGObject.

```APIDOC
GObject.Signal(flags: GObject.SignalFlags = None, arg_types: tuple = ()) -> Callable:
  Description: Decorator to define a new signal on a GObject class.
  Parameters:
    flags: GObject.SignalFlags - Controls when the method handler is invoked.
    arg_types: tuple - A tuple of types defining the arguments the signal will carry.
  Returns: Callable - The decorated method handler.
GObject.SignalFlags:
  RUN_FIRST: Invoke the object method handler in the first emission stage.
  RUN_LAST: Invoke the object method handler in the third emission stage.
  RUN_CLEANUP: Invoke the object method handler in the last emission stage.
GObject.Object:
  __gsignals__: dict
    Description: Class attribute dictionary to define signals.
    Format: { 'signal_name': (GObject.SignalFlags, return_type, arguments_tuple) }
  emit(signal_name: str, *args) -> None:
    Description: Emits a signal, invoking all connected handlers.
    Parameters:
      signal_name: str - The name of the signal to emit.
      *args: Any - Arguments to pass to the signal handlers, matching arg_types.
    Returns: None
  connect(signal_name: str, callback: Callable) -> int:
    Description: Connects a callback function to a signal.
    Parameters:
      signal_name: str - The name of the signal to connect to.
      callback: Callable - The function to be called when the signal is emitted.
    Returns: int - A handler ID for disconnection.
```

--------------------------------

### Gtk.Stack and Gtk.StackSwitcher API Documentation

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/layout-widgets.rst

API documentation for Gtk.Stack, a container showing one child at a time, and Gtk.StackSwitcher, which controls the visible child of a Gtk.Stack. It details their properties for transitions and methods for adding pages.

```APIDOC
Gtk.Stack
  Description: A container that displays only one of its children at a time. It does not provide user controls for changing the visible child; Gtk.StackSwitcher is used for this purpose.
  Properties:
    props.transition_type: Controls animation type for page transitions (e.g., slides, fades). Respects 'gtk-enable-animations' setting.
    props.transition_duration: Adjusts the speed of page transitions.
  Auxiliary Object: Gtk.StackPage (returned when adding children).
  Methods for adding children (return Gtk.StackPage):
    add_child(child: Gtk.Widget): Adds a child to the stack.
    add_named(child: Gtk.Widget, name: str): Adds a child with a specific name.
    add_titled(child: Gtk.Widget, name: str, title: str): Adds a child with a name and a title.

Gtk.StackSwitcher
  Description: A widget that acts as a controller for a Gtk.Stack, providing a row of buttons to switch between the various pages of the associated stack widget.
```

--------------------------------

### Gdk.Clipboard and Gdk.Display API Reference

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/clipboard.rst

Reference for key classes and methods related to clipboard operations in `Gdk` (part of `pygobject`), including how to access clipboards and set/read data.

```APIDOC
Gdk.Clipboard:
  Description: Provides a storage area for a variety of data, including text and images, for sharing between applications.
  Methods:
    set(value: Any):
      Description: Sets a simple value like text to the clipboard.
      Parameters:
        value: The data to set.
    set_content(provider: Gdk.ContentProvider):
      Description: Sets more complex data using a content provider.
      Parameters:
        provider: A Gdk.ContentProvider instance.
    read_text_async():
      Description: Asynchronously reads textual data from the clipboard.
      Returns: Promise<str>
    read_texture_async():
      Description: Asynchronously reads image data from the clipboard.
      Returns: Promise<Gdk.Texture>
    read_value_async():
      Description: Asynchronously reads other data types from the clipboard.
      Returns: Promise<Any>

Gdk.Display:
  Description: Provides access to different clipboard selections.
  Methods:
    get_default():
      Description: Gets the default display.
      Returns: Gdk.Display
    get_clipboard():
      Description: Gets the 'CLIPBOARD' selection.
      Returns: Gdk.Clipboard
    get_primary_clipboard():
      Description: Gets the 'PRIMARY' selection.
      Returns: Gdk.Clipboard

Gdk.ContentProvider:
  Description: Used to provide complex data to the clipboard.
  Methods:
    new_for_value(value: Any):
      Description: Creates a new content provider for a given value.
      Parameters:
        value: The value to be provided.
      Returns: Gdk.ContentProvider
```

--------------------------------

### GObject Property System API Reference

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/subclassing.rst

API documentation for key components involved in defining and managing custom properties in PyGObject.

```APIDOC
GObject.Object:
  __gproperties__: dict
    Description: Class attribute dictionary to define custom properties.
    Format: { 'property-name': (type, nick, blurb, min, max, default, GObject.ParamFlags) }
  do_get_property(prop: GObject.ParamSpec) -> Any:
    Description: Virtual method to retrieve the value of a property.
    Parameters:
      prop: GObject.ParamSpec - The parameter specification for the property.
    Returns: Any - The current value of the property.
  do_set_property(prop: GObject.ParamSpec, value: Any) -> None:
    Description: Virtual method to set the value of a property.
    Parameters:
      prop: GObject.ParamSpec - The parameter specification for the property.
      value: Any - The new value to set.
    Returns: None
GObject.ParamFlags:
  READWRITE: Flag indicating a property can be read and written.
```

--------------------------------

### Adw.ApplicationWindow Class Details

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/libadwaita/application.rst

Describes `Adw.ApplicationWindow` as a subclass of `Gtk.ApplicationWindow` that provides 'freeform' features, similar to those found in `Adw.Window`.

```APIDOC
Adw.ApplicationWindow:
  Extends: Gtk.ApplicationWindow
  Features: Provides 'freeform' capabilities akin to Adw.Window.
```

--------------------------------

### Gtk.Picture API Reference

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/display-widgets/picture.rst

Overview of key classes, methods, and properties related to Gtk.Picture for image display in GTK applications, including how to load images and control their display.

```APIDOC
Class: Gtk.Picture
  Description: Widget for displaying images at their natural size.
  Methods:
    new_for_filename(filename: str)
      Description: Creates a new Gtk.Picture from a local file path.
    new_for_resource(resource_path: str)
      Description: Creates a new Gtk.Picture from a GIO resource path.
    set_resource(resource_path: str)
      Description: Sets the image of an existing Gtk.Picture from a GIO resource path.
  Properties:
    props.content_fit: Gtk.ContentFit
      Description: Controls how the image is scaled and positioned within the widget's allocated space.

Class: Gtk.ContentFit
  Description: An enumeration defining how content should fit within its allocated space (e.g., SCALE_DOWN, FILL).

Class: Gio.Resource
  Description: GIO class for embedding application data, such as images, directly into the executable.

Class: Gtk.Widget
  Properties:
    props.halign: Gtk.Align
      Description: Horizontal alignment of the widget within its allocated space.
    props.valign: Gtk.Align
      Description: Vertical alignment of the widget within its allocated space.
```

--------------------------------

### GTK Drag and Drop API Reference

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/drag-and-drop.rst

Detailed API documentation for GTK drag-and-drop components, including classes, methods, and signals for Gtk.DragSource, Gtk.DropTarget, and Gdk.ContentProvider.

```APIDOC
Gtk.Widget.add_controller(controller):
  Description: Adds an event controller to a widget.
  Parameters:
    controller: The Gtk.EventController to add.

Gdk.ContentProvider:
  Description: Provides data for drag-and-drop operations.
  Methods:
    new_for_value(value):
      Description: Creates a content provider for a single value.
      Parameters:
        value: The value to provide.
    new_union(content_providers: list[Gdk.ContentProvider]):
      Description: Creates a content provider from a list of other content providers, allowing multiple data types.
      Parameters:
        content_providers: A list of Gdk.ContentProvider instances.

Gtk.DragSource:
  Description: An event controller that allows a widget to be used as a drag source.
  Methods:
    set_content(content_provider: Gdk.ContentProvider):
      Description: Sets the Gdk.ContentProvider that will be sent to drop targets.
      Parameters:
        content_provider: The Gdk.ContentProvider to set.
    set_icon(icon):
      Description: Changes the icon attached to the cursor when dragging.
      Parameters:
        icon: The icon to set.
  Signals:
    prepare():
      Description: Emitted when a drag is about to be initiated. Should return the Gdk.ContentProvider.
      Returns: Gdk.ContentProvider
    drag-begin():
      Description: Emitted when the drag is started.
    drag-end():
      Description: Emitted when the drag operation has ended.
    drag-cancel():
      Description: Emitted when the drag operation has been cancelled.

Gtk.DropTarget:
  Description: An event controller to receive drag-and-drop operations in a widget.
  Methods:
    new(data_type, drag_action: Gdk.DragAction):
      Description: Creates a new drop target.
      Parameters:
        data_type: The data type accepted (e.g., GObject.TYPE_NONE for multiple).
        drag_action: The Gdk.DragAction accepted.
    set_gtypes(types: list[GType]):
      Description: Sets a list of accepted data types, establishing priorities by order.
      Parameters:
        types: A list of GType objects.
  Signals:
    accept():
      Description: Emitted to determine if the drop target accepts the drag.
    drop():
      Description: Emitted when a drop occurs. Receives the value sent by the Gtk.DragSource.
    enter():
      Description: Emitted when the drag enters the drop target's area.
    leave():
      Description: Emitted when the drag leaves the drop target's area.
    motion():
      Description: Emitted when the drag moves within the drop target's area.

GObject.TYPE_NONE:
  Description: A special GType value used to indicate support for multiple data types in Gtk.DropTarget.

Gtk.DropTargetAsync:
  Description: A more complex version of Gtk.DropTarget for asynchronous drop handling.
```

--------------------------------

### Basic Import of GTK and GLib in PyGObject

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/imports.rst

This snippet demonstrates the fundamental way to import the GTK and GLib libraries from the `gi.repository` module, which holds the library bindings for PyGObject.

```Python
from gi.repository import Gtk, GLib
```

--------------------------------

### Bind GObject Properties with `bind_property` (Default) in Python

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/basics.rst

Illustrates how to bind properties of two different GObjects using `GObject.Object.bind_property`. The `DEFAULT` flag updates the target property whenever the source property changes.

```python
entry = Gtk.Entry()
label = Gtk.Label()

entry.bind_property('text', label, 'label', GObject.BindingFlags.DEFAULT)
```

--------------------------------

### Connect to GObject 'notify' Signal for Property Changes

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/basics.rst

The 'notify' signal is emitted when any of a GObject's properties change. This snippet illustrates how to connect to a 'detailed' notify signal, specifically for a particular property (e.g., 'notify::label'), allowing you to react to changes in that specific property.

```python
def callback(label, _pspec):
    print(f'The label prop changed to {label.props.label}')

label = Gtk.Label()
label.connect('notify::label', callback)
```

--------------------------------

### Apply Text Formatting Tag in Gtk.TextBuffer (Python)

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/textview.rst

This snippet demonstrates how to create a new formatting tag with specific properties (e.g., background color) and then apply it to a defined region of text within a Gtk.TextBuffer. It utilizes `create_tag` to define the style and `apply_tag` to link the style to text.

```Python
tag = textbuffer.create_tag('orange_bg', background='orange')
textbuffer.apply_tag(tag, start_iter, end_iter)
```

--------------------------------

### GObject.BindingFlags Enum

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/basics.rst

An enumeration used with `GObject.Object.bind_property` to control the behavior of property bindings.

```APIDOC
GObject.BindingFlags:
  DEFAULT: Updates the target property every time the source property changes.
  BIDIRECTIONAL: Creates a bidirectional binding; if either property changes, the other is updated.
  SYNC_CREATE: Similar to DEFAULT, but also synchronizes values when the binding is created.
  INVERT_BOOLEAN: Works only for boolean properties; setting one to True sets the other to False and vice versa. Cannot be used with custom transformation functions.
```

--------------------------------

### Basic GObject Subclassing in PyGObject

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/subclassing.rst

This snippet demonstrates the fundamental way to subclass GObject.Object in PyGObject. It highlights the necessity of calling super().__init__() within the constructor to properly initialize the inherited GObject.

```python
from gi.repository import GObject

class MyObject(GObject.Object):

    def __init__(self):
        super().__init__()
```

--------------------------------

### GObject.Property Decorator API Reference

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/api/properties.rst

Provides the API documentation for the `GObject.Property` decorator, which allows defining custom properties on `GObject.Object` subclasses. It lists all available parameters, their types, and descriptions, enabling fine-grained control over property behavior.

```APIDOC
GObject.Property(type=None, default=None, nick='', blurb='', flags=GObject.ParamFlags.READWRITE, minimum=None, maximum=None)
  type: Either a GType, a type with a GType or a Python type which maps to a default GType
  default: A default value
  nick: Property nickname
  blurb: Short description
  flags: Property configuration flags
  minimum: Minimum value, depends on the type
  maximum: Maximum value, depends on the type
```

--------------------------------

### Managing Asynchronous File Operations and UI State with PyGObject

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/asynchronous.rst

This documentation describes the process of handling asynchronous file loading operations using `Gio.AsyncResult` and `Gio.File` methods, and how to manage UI element sensitivity with `Gtk.Widget` to prevent concurrent operations.

```APIDOC
Gio.AsyncResult:
  Description: An instance containing the result of an asynchronous operation.

Gio.File:
  load_contents_finish():
    Description: Retrieves the result of a file loading operation.
    Behavior: Returns immediately without blocking, as the operation has already completed.
    Related: Behaves similarly to Gio.File.load_contents, but for completed operations.

Gio.Cancellable:
  reset():
    Description: Prepares the Cancellable instance for reuse in future operations.
    Usage: Call after handling the result of an operation to allow the Cancellable to be used again.

Gtk.Widget:
  set_sensitive(sensitive: bool):
    Description: Sets the sensitivity of the widget.
    Usage: Used to enable or disable UI elements (e.g., buttons) to control user interaction.
    Context: In this application, used to disable the "Load" button during an ongoing task to enforce single active operation.
```

--------------------------------

### Gtk.Entry Class Properties and Methods

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/controls/entries.rst

Gtk.Entry is the standard single-line text entry widget. It supports features like password visibility toggling, progress indication, displaying icons, and placeholder text.

```APIDOC
Gtk.Entry:
  Standard single-line text entry widget.
  Properties:
    visibility (bool): Whether the text is visible (useful for passwords).
    invisible_char (str): The character to use for invisible text (e.g., for passwords).
    progress_fraction (float): The current fraction of the task that's been completed (0.0-1.0).
    progress_pulse_step (float): The fraction of the progress bar to move when Gtk.Entry.progress_pulse() is called.
    placeholder_text (str): Text to be displayed in the entry when it is empty and unfocused.
  Methods:
    progress_pulse(): Indicates that some progress has been made, without knowing the exact amount.
    set_icon_from_icon_name(position: Gtk.EntryIconPosition, icon_name: str): Sets an icon from an icon name.
    set_icon_tooltip_text(position: Gtk.EntryIconPosition, tooltip_text: str): Sets a tooltip for an icon.
```

--------------------------------

### Python Class Inheritance and Method Overriding in GObject

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/subclassing.rst

This snippet defines `MyObject` inheriting from `SomeOject` (which itself inherits from `OtherObject`). It demonstrates overriding the `__init__` method using `super().__init__()` and a virtual method `do_virtual_method` by calling `super().do_virtual_method()` before adding custom logic. It also shows how to call a parent method directly (e.g., `OtherObject.do_other(self)`) when `super()` might not be suitable.

```Python
class SomeOject(OtherObject):
    ...

class MyObject(SomeOject):

    def __init__(self):
        super().__init__()

    def do_virtual_method(self):
        # Call the original method to keep its original behavior
        super().do_virtual_method()

        # Run some extra code
        ...

    """This is a virtual method from SomeOject parent"""
    def do_other(self):
        OtherObject.do_other(self)  # We can't use super()
        ...
```

--------------------------------

### gi.require_version Function

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/api/api.rst

Ensures a specific namespace is loaded with the given version. It raises a ValueError if the namespace was already loaded with a different version or if a different version was previously required.

```APIDOC
gi.require_version(namespace: str, version: str)
  Parameters:
    namespace: The namespace
    version: The version of the namespace which should be loaded
  Raises: ValueError
```

```python
import gi
gi.require_version('Gtk', '3.0')
```

--------------------------------

### Gtk.TextTag and Gtk.TextTagTable API Reference for Text Attributes

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/textview.rst

Describes Gtk.TextTag for applying attributes to text ranges and Gtk.TextTagTable for managing collections of tags within a buffer.

```APIDOC
Gtk.TextTag:
  Description: An attribute that can be applied to a range of text in a Gtk.TextBuffer, affecting appearance or behavior.
Gtk.TextTagTable:
  Description: A collection of Gtk.TextTag objects. Each Gtk.TextBuffer has an associated tag table.
```

--------------------------------

### Gtk.SearchEntry Class Properties, Methods, and Signals

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/controls/entries.rst

Gtk.SearchEntry is an entry widget optimized for search functionality, supporting 'type to search' and a debounced search_changed signal to prevent overloading backend services.

```APIDOC
Gtk.SearchEntry:
  Entry widget designed for search functionality.
  Properties:
    search_delay (int): The delay in milliseconds before the 'search-changed' signal is emitted after text input.
  Methods:
    set_key_capture_widget(widget: Gtk.Widget): Sets the parent widget that will redirect its key events to the entry.
  Signals:
    search_changed: Emitted after a short delay when the text in the entry changes, suitable for reactive searching.
```

--------------------------------

### Gtk.Grid.attach_next_to Method Parameters

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/layout-widgets.rst

API documentation for the Gtk.Grid.attach_next_to method, detailing its five parameters for adding a child widget next to an existing sibling within a Gtk.Grid.

```APIDOC
Gtk.Grid.attach_next_to(child: Gtk.Widget, sibling: Gtk.Widget | None, side: Gtk.PositionType, width: int, height: int)
  child: The Gtk.Widget to add.
  sibling: An existing child widget of the Gtk.Grid instance or None. The child widget will be placed next to sibling, or if sibling is None, at the beginning or end of the grid.
  side: A Gtk.PositionType indicating the side of sibling that child is positioned next to.
  width: The number of columns the child widget will span.
  height: The number of rows the child widget will span.
```

--------------------------------

### List GObject Signals for a Class (PyGObject)

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/api/signals.rst

Demonstrates how to retrieve a list of all available signal names for a given GObject class, such as `Gio.Application`, using `GObject.signal_list_names`.

```pycon
>>> GObject.signal_list_names(Gio.Application)
('activate', 'startup', 'shutdown', 'open', 'command-line', 'handle-local-options')
>>>
```

--------------------------------

### Gtk.TextIter API Reference for Text Navigation

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/textview.rst

Explains Gtk.TextIter, which represents a position within a Gtk.TextBuffer, and its use for navigating and searching text.

```APIDOC
Gtk.TextIter:
  Description: Represents a position between two characters in a Gtk.TextBuffer. Invalidated by buffer modifications.
  Methods:
    forward_search(str: str, flags: Gtk.TextSearchFlags, limit: Gtk.TextIter = None): tuple[Gtk.TextIter, Gtk.TextIter] - Searches forwards for a string.
    backward_search(str: str, flags: Gtk.TextSearchFlags, limit: Gtk.TextIter = None): tuple[Gtk.TextIter, Gtk.TextIter] - Searches backwards for a string.
```

--------------------------------

### Define GObject Signals using __gsignals__ Class Attribute

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/subclassing.rst

This snippet provides an alternative, more verbose method for defining signals using the `__gsignals__` class attribute. It shows how to specify signal flags, return type, and arguments. It also demonstrates the `do_signal_name` method handler, which is automatically called when the signal is emitted.

```Python
class MyObject(GObject.Object):
    __gsignals__ = {
        'my_signal': (
            GObject.SignalFlags.RUN_FIRST,  # flag
            None,  # return type
            (int,)  # arguments
        )
    }

    def do_my_signal(self, arg):
        print("method handler for `my_signal' called with argument", arg)
```

--------------------------------

### gi.version_info Data

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/api/api.rst

Represents the version of PyGObject as a tuple.

```APIDOC
gi.version_info = (3, 18, 1)
```

--------------------------------

### GObject.Signal Decorator API Reference (PyGObject)

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/api/signals.rst

API documentation for the `GObject.Signal` decorator, used to define custom signals. It details the parameters for configuring signal behavior, including name, flags, return type, argument types, and accumulator function.

```APIDOC
GObject.Signal(name: str = '', flags: GObject.SignalFlags = GObject.SignalFlags.RUN_FIRST, return_type: GObject.GType = None, arg_types: list = None, accumulator: GObject.SignalAccumulator = None, accu_data: object = None)
  name: The signal name
  flags: Signal flags
  return_type: Return type
  arg_types: List of GObject.GType argument types
  accumulator: Accumulator function (type: GObject.SignalAccumulator)
  accu_data: User data for the accumulator
```

--------------------------------

### gi.check_version Function

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/api/api.rst

Compares the provided version tuple with the current gi version. It performs no action if the gi version is the same or newer, otherwise, it raises a ValueError.

```APIDOC
gi.check_version(version: tuple)
  Parameters:
    version: A version tuple
  Raises: ValueError
```

--------------------------------

### Define GObject Properties with __gproperties__ and Handlers

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/subclassing.rst

This snippet demonstrates how to define custom properties for a GObject class using the `__gproperties__` class attribute. It shows how to specify property type, range, default value, and flags. It also illustrates the implementation of `do_get_property` and `do_set_property` virtual methods to handle property access and modification.

```Python
from gi.repository import GObject

class MyObject(GObject.Object):

    __gproperties__ = {
        'int-prop': (
            int, # type
            'integer prop', # nick
            'A property that contains an integer', # blurb
            1, # min
            5, # max
            2, # default
            GObject.ParamFlags.READWRITE # flags
        ),
    }

    def __init__(self):
        super().__init__()
        self.int_prop = 2

    def do_get_property(self, prop):
        if prop.name == 'int-prop':
            return self.int_prop
        else:
            raise AttributeError('unknown property %s' % prop.name)

    def do_set_property(self, prop, value):
        if prop.name == 'int-prop':
            self.int_prop = value
        else:
            raise AttributeError('unknown property %s' % prop.name)
```

--------------------------------

### Gio.ListModel Interface Definition

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/interfaces.rst

Defines a mutable list of `GObject.Object` instances. Implementations must provide methods for item type, item count, and item retrieval to allow consumers to iterate and use the objects.

```APIDOC
Gio.ListModel:
  Description: Represents a mutable list of GObject.Objects.
  Required Methods:
    - get_item_type():
        Description: Returns the GType of the items in the list.
        Return Type: GType
    - get_n_items():
        Description: Returns the number of items in the list.
        Return Type: int
    - get_item(position: int):
        Description: Returns the item at the given position.
        Parameters:
          position: The 0-indexed position of the item.
        Return Type: GObject.Object
```

--------------------------------

### Gtk.TextView Widget API Reference

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/textview.rst

Defines the Gtk.TextView widget, its purpose, and key properties for controlling text display and editability.

```APIDOC
Gtk.TextView:
  Description: Widget for displaying and editing large amounts of formatted text.
  Properties:
    props.buffer: Gtk.TextBuffer - The text buffer model associated with the view.
    props.editable: bool - If TRUE, the text can be edited by the user.
    props.cursor_visible: bool - If TRUE, the text cursor is visible.
    props.justification: Gtk.Justification - The alignment of the text within the view (LEFT, RIGHT, CENTER, FILL).
    props.wrap_mode: Gtk.WrapMode - Controls how text is wrapped (e.g., WORD, CHAR, WORD_CHAR).
```

--------------------------------

### Tracking GObject Property Changes with `notify` Signal in Python

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/api/properties.rst

Demonstrates how to connect a callback function to the `notify::property-name` signal to monitor changes to a specific property of a `GObject` instance. It's crucial to use the exact, hyphenated property name for the signal detail string.

```pycon
>>> app = Gio.Application(application_id="foo.bar")
>>> def my_func(instance, param):
...     print("New value %r" % instance.get_property(param.name))
...
>>> app.connect("notify::application-id", my_func)
11L
>>> app.set_property("application-id", "something.different")
New value 'something.different'
```

--------------------------------

### Robust PyGObject Imports with Versioning and Error Handling

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/imports.rst

This snippet demonstrates how to handle `gi.require_version()` and import statements within a `try-except` block. This approach gracefully manages `ImportError` or `ValueError` exceptions, ensuring dependencies are met and adhering to PEP8/E402 guidelines.

```Python
import sys

import gi
try:
    gi.require_version('Gtk', '4.0')
    gi.require_version('Adw', '1')
    from gi.repository import Adw, Gtk
except ImportError or ValueError as exc:
    print('Error: Dependencies not met.', exc)
    sys.exit(1)
```

--------------------------------

### Gtk.TextBuffer Tag Management Methods

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/textview.rst

This describes key methods of Gtk.TextBuffer for managing formatting tags. It includes methods for creating new tags, applying them to text regions, and removing specific or all tags from a given range.

```APIDOC
Gtk.TextBuffer Methods:
  create_tag(tag_name: str, **properties): Gtk.TextTag
    tag_name: The name for the new tag.
    properties: Keyword arguments for tag properties (e.g., background='orange').
    Returns: The newly created Gtk.TextTag object.

  apply_tag(tag: Gtk.TextTag, start_iter: Gtk.TextIter, end_iter: Gtk.TextIter): None
    tag: The Gtk.TextTag to apply.
    start_iter: The starting iterator for the text region.
    end_iter: The ending iterator for the text region.

  remove_tag(tag: Gtk.TextTag, start_iter: Gtk.TextIter, end_iter: Gtk.TextIter): None
    tag: The Gtk.TextTag to remove.
    start_iter: The starting iterator for the text region.
    end_iter: The ending iterator for the text region.

  remove_all_tags(start_iter: Gtk.TextIter, end_iter: Gtk.TextIter): None
    start_iter: The starting iterator for the text region.
    end_iter: The ending iterator for the text region.
```

--------------------------------

### Scheduling Function on GLib Main Loop with PyGObject

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/threading.rst

This Python snippet demonstrates how to use `GLib.idle_add` to schedule a function (`function_calling_gtk`) to be executed on the GLib main loop. It also shows a pattern for thread synchronization using an `event.wait()` call to block the current thread until the scheduled function completes and populates a `result` list, from which a boolean value is then retrieved and printed.

```Python
GLib.idle_add(function_calling_gtk, event, result)
event.wait()
toggle_button_is_active = result[0]
print(toggle_button_is_active)
```

--------------------------------

### gi.get_required_version Function

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/api/api.rst

Retrieves the version that was successfully required previously by the gi.require_version function. Returns None if no version was previously required.

```APIDOC
gi.get_required_version(namespace)
  Returns: str or None - The version successfully required previously by gi.require_version or None
```

--------------------------------

### Gtk.Template with Mismatched Python and XML Attribute Names

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/gtk_template.rst

This snippet illustrates how to handle situations where the Python attribute names for child widgets or signal handlers differ from their corresponding XML 'id' or 'handler' attributes. It demonstrates passing the XML attribute name as an argument to Gtk.Template.Child() and Gtk.Template.Callback() to establish the correct mapping.

```python
@Gtk.Template(string=xml)
class Foo(Gtk.Box):
    __gtype_name__ = "example1"

    my_button = Gtk.Template.Child("hello_button")

    @Gtk.Template.Callback("hello_button_clicked")
    def bar(self, *args):
        pass
```

--------------------------------

### Connect a Callback to a GObject Signal (PyGObject)

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/api/signals.rst

Illustrates how to connect a Python function as a callback to a GObject signal, specifically the 'activate' signal of a `Gio.Application` instance. The `connect` method returns a connection ID.

```pycon
>>> app = Gio.Application()
>>> def on_activate(instance):
...     print("Activated:", instance)
... 
>>> app.connect("activate", on_activate)
17L
>>> app.run()
('Activated:', <Gio.Application object at 0x7f1bbb304320 (GApplication at 0x5630f1faf200)>)
0
>>>
```

--------------------------------

### Gtk Button Widgets API Reference

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/controls/buttons.rst

Reference for Gtk.Button, Gtk.ToggleButton, and Gtk.LinkButton widgets in PyGObject, detailing their properties and signals.

```APIDOC
gi.repository.Gtk:
  Gtk.Button:
    Description: A standard button widget used to trigger actions.
    Child Widgets: Can hold any valid Gtk.Widget, commonly Gtk.Label.
    Properties:
      label (str): Text displayed on the button.
      icon_name (str): Name of an icon to display on the button.
    Signals:
      clicked(): Emitted when the button is pressed and released.

  Gtk.ToggleButton:
    Description: A button that remains activated (pressed) until clicked again.
    Inherits: Gtk.Button
    Properties:
      active (bool): True if the button is in the "down" (activated) state. Setting this property emits the 'toggled' signal if the state changes.
    Signals:
      toggled(): Emitted when the button's active state changes.

  Gtk.LinkButton:
    Description: A button with a hyperlink, similar to web browsers, that triggers an action when clicked.
    Inherits: Gtk.Button
    Properties:
      uri (str): The URI (Uniform Resource Identifier) bound to the link button.
```

--------------------------------

### Gtk.ListBox Class API Documentation

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/layout-widgets.rst

API documentation for the Gtk.ListBox class, a vertical container for Gtk.ListBoxRow children. It details its dynamic sorting, filtering, navigation, selection modes, and methods for adding children.

```APIDOC
Gtk.ListBox
  Description: A vertical container that holds Gtk.ListBoxRow children. Supports dynamic sorting, filtering, keyboard/mouse navigation, and selection.
  Children: Must be Gtk.ListBoxRow, but any widget can be added via append/insert, which automatically wraps it in a Gtk.ListBoxRow.
  Methods:
    append(child: Gtk.Widget): Adds a child widget to the list box.
    insert(child: Gtk.Widget, position: int): Inserts a child widget at a specific position.
  Properties:
    props.selection_mode: Configures selection behavior.
      Values:
        Gtk.SelectionMode.NONE: No selection.
        Gtk.SelectionMode.SINGLE: One or no elements can be selected.
        Gtk.SelectionMode.BROWSE: User cannot deselect a currently selected element except by selecting another.
        Gtk.SelectionMode.MULTIPLE: Any number of elements may be selected.
  Signals:
    row-activated: Emitted when a row is activated.
    row-selected: Emitted when a row is selected.
```

--------------------------------

### Gtk.FlowBox Class API Documentation

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/layout-widgets.rst

API documentation for the Gtk.FlowBox class, a container that positions child widgets in sequence based on its orientation. It behaves similarly to Gtk.ListBox but arranges items in a grid-like flow.

```APIDOC
Gtk.FlowBox
  Description: A container that positions child widgets in sequence according to its orientation (horizontal or vertical). Similar to Gtk.ListBox, it supports dynamic sorting, filtering, activation, and selection of children.
  Children: Must be Gtk.FlowBoxChild, but any widget can be added via append/insert, which automatically wraps it in a Gtk.FlowBoxChild.
  Methods:
    append(child: Gtk.Widget): Adds a child widget to the flow box.
    insert(child: Gtk.Widget, position: int): Inserts a child widget at a specific position.
```

--------------------------------

### Gtk.TextBuffer Model API Reference

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/textview.rst

Describes the Gtk.TextBuffer, the model component of Gtk.TextView, responsible for holding and managing the text content. It details properties for text access and methods for manipulation.

```APIDOC
Gtk.TextBuffer:
  Description: The model that holds the text content for a Gtk.TextView.
  Properties:
    props.text: str - The entire text content of the buffer.
  Methods:
    get_insert(): Gtk.TextMark - Retrieves the "insert" mark (cursor position).
    get_selection_bound(): Gtk.TextMark - Retrieves the "selection_bound" mark.
    get_start_iter(): Gtk.TextIter - Returns an iterator pointing to the first position in the buffer.
    get_end_iter(): Gtk.TextIter - Returns an iterator pointing past the last valid character in the buffer.
    get_selection_bounds(): tuple[Gtk.TextIter, Gtk.TextIter] - Returns the start and end iterators for the selected text.
    insert(iter: Gtk.TextIter, text: str, length: int = -1): None - Inserts text at the specified iterator position.
    insert_at_cursor(text: str, length: int = -1): None - Inserts text at the current cursor position.
    delete(start_iter: Gtk.TextIter, end_iter: Gtk.TextIter): None - Removes text between the two specified iterators.
```

--------------------------------

### Listing Class Properties in PyGObject

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/api/properties.rst

Demonstrates how to use `Gio.Application.list_properties()` to retrieve a list of `GParamSpec` objects for a class, allowing inspection of property details like name, owner type, and value type.

```pycon
>>> Gio.Application.list_properties()
[<GParamString 'application-id'>, <GParamFlags 'flags'>, <GParamString
'resource-base-path'>, <GParamBoolean 'is-registered'>, <GParamBoolean
'is-remote'>, <GParamUInt 'inactivity-timeout'>, <GParamObject
'action-group'>, <GParamBoolean 'is-busy'>]
>>> param = Gio.Application.list_properties()[0]
>>> param.name
'application-id'
>>> param.owner_type
<GType GApplication (94881584893168)>
>>> param.value_type
<GType gchararray (64)>
```

--------------------------------

### Enable PyGObject Cairo Integration

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/cairo_integration.rst

This Python snippet demonstrates how to explicitly enable Cairo integration within a PyGObject application using `gi.require_foreign("cairo")`. It includes error handling to catch `ImportError` if pycairo support is not available, informing the user about the missing integration.

```python
try:
    gi.require_foreign("cairo")
except ImportError:
    print("No pycairo integration :(")
```

--------------------------------

### Configure GLib Event Loop Policy for Asyncio

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/asynchronous.rst

This snippet demonstrates how to set up the GLib-based event loop policy for Python's `asyncio` module. By using `GLibEventLoopPolicy`, PyGObject integrates seamlessly with `asyncio`, enabling the use of standard asynchronous Python code within a GLib application context.

```python
import asyncio
from gi.events import GLibEventLoopPolicy

# Set up the GLib event loop
policy = GLibEventLoopPolicy()
asyncio.set_event_loop_policy(policy)
```

--------------------------------

### Define New GObject Properties with Type and Default

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/subclassing.rst

This snippet shows how to define new properties for a GObject subclass using GObject.Property. Each property requires a type (e.g., str, float) and can optionally be assigned a default value, ensuring type consistency within the GObject system.

```python
from gi.repository import GObject

class MyObject(GObject.Object):

    foo = GObject.Property(type=str, default='bar')
    property_float = GObject.Property(type=float)

    def __init__(self):
        super().__init__()
```

--------------------------------

### Gtk.CheckButton Class API Reference

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/controls/check-radio-buttons.rst

Comprehensive API documentation for the `Gtk.CheckButton` class, detailing its constructor, properties, methods, and signals. This class is fundamental for creating interactive toggle buttons in GTK applications.

```APIDOC
Class: Gtk.CheckButton
  Description: A widget that places a label next to an indicator. It can be toggled between "on" and "off" states. When grouped, it functions as a radio button, allowing only one button in the group to be active at a time. It also supports an "in between" or "inconsistent" state.

  Constructor:
    Gtk.CheckButton(label: str = None)
      label: The text label to display next to the indicator.

  Properties:
    props.inconsistent: bool
      Description: If TRUE, the check button is in an "in between" state, neither on nor off. This is typically used when the button represents a property that is inconsistent across a selection of items.
      Type: boolean
      Default: FALSE

  Methods:
    set_group(group: Gtk.CheckButton)
      Description: Sets the group for the check button. When grouped, only one button in the group can be active at a time, effectively turning them into radio buttons.
      Parameters:
        group: Gtk.CheckButton
          Description: An existing Gtk.CheckButton that is part of the desired group.
          Type: Gtk.CheckButton
      Returns: None

    get_active(): bool
      Description: Retrieves the current state of the check button.
      Returns:
        Type: boolean
        Values: TRUE (active/checked), FALSE (inactive/unchecked)

    set_active(is_active: bool)
      Description: Sets the active state of the check button.
      Parameters:
        is_active: bool
          Description: TRUE to activate (check) the button, FALSE to deactivate (uncheck) it.
          Type: boolean
      Returns: None

  Signals:
    "toggled"
      Description: Emitted when the check button is toggled.
      Callback Signature: (button: Gtk.CheckButton)
```

--------------------------------

### gi.PyGIWarning Class

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/api/api.rst

Similar to gi.PyGIDeprecationWarning, this warning class is visible by default.

```APIDOC
class gi.PyGIWarning
```

--------------------------------

### Accessing GObject Properties via `props` Attribute in Python

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/api/properties.rst

Explains how the `props` attribute on a `GObject` instance provides direct, attribute-like access to its properties, simplifying both reading and writing of property values. This method offers a more Pythonic syntax compared to `get_property()` and `set_property()`.

```pycon
>>> from gi.repository import Gtk
>>> button = Gtk.Button(label="foo")
>>> button.props.label
'foo'
>>> button.props.label = "bar"
>>> button.get_label()
'bar'
```

--------------------------------

### Await Gio Asynchronous Functions in PyGObject

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/asynchronous.rst

This code illustrates how PyGObject automatically makes Gio asynchronous functions awaitable when their callback parameter is omitted. This allows developers to use the `await` keyword within Python coroutines, simplifying asynchronous I/O operations like enumerating files.

```python
loop = policy.get_event_loop()


async def list_files():
    f = Gio.file_new_for_path("/")
    for info in await f.enumerate_children_async(
        "standard::*", 0, GLib.PRIORITY_DEFAULT
    ):
        print(info.get_display_name())


task = loop.create_task(list_files())
```

--------------------------------

### Accessing GObject Properties by Name or Attribute

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/subclassing.rst

This snippet demonstrates two common ways to access properties of a GObject instance. Properties can be retrieved directly as attributes (e.g., my_object.readonly) or by using the generic get_property() method with the property's string name.

```python
my_object = MyObject()
print(my_object.readonly)
print(my_object.get_property('readonly'))
```

--------------------------------

### Combining GObject.Object with Multiple Python Mixins

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/api/gobject.rst

Illustrates the inheritance rules for `GObject.Object` subclasses. While `GObject.Object` itself only supports single inheritance from another `GObject.Object` type, it can be combined with multiple standard Python classes (mixins). This allows for flexible class design where GObject functionality is extended with Python-specific behaviors.

```Python
>>> from gi.repository import GObject
>>> class MixinA(object):
...     pass
... 
>>> class MixinB(object):
...     pass
... 
>>> class MyClass(GObject.Object, MixinA, MixinB):
...     pass
... 
>>> instance = MyClass()

```

--------------------------------

### Disabling Legacy Auto-Initialization in PyGObject

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/imports.rst

For better control over initialization and to prevent automatic calls to `Gdk.init_check()` and `Gtk.init_check()`, use `gi.disable_legacy_autoinit()` before importing Gtk. This allows calling functions like `Gtk.disable_setlocale()` prior to initialization.

```Python
import gi
gi.disable_legacy_autoinit()
from gi.repository import Gtk
```

--------------------------------

### Gtk.PasswordEntry Class Properties

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/controls/entries.rst

Gtk.PasswordEntry is a specialized entry widget designed for password input, offering a convenient way to toggle password visibility.

```APIDOC
Gtk.PasswordEntry:
  Specialized entry widget for password input.
  Properties:
    show_peek_icon (bool): Whether to show a button to toggle the visibility of the text.
```

--------------------------------

### gi.require_foreign Function

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/api/api.rst

Ensures that the specified foreign marshaling module is available and loaded. An optional symbol typename can be provided to ensure a converter exists, raising an ImportError if the module cannot be loaded.

```APIDOC
gi.require_foreign(namespace: str, symbol: str or None = None)
  Parameters:
    namespace: Introspection namespace of the foreign module (e.g. "cairo")
    symbol: Optional symbol typename to ensure a converter exists.
  Raises: ImportError
```

```python
import gi
import cairo
gi.require_foreign('cairo')
gi.require_foreign('cairo', 'Surface')
```

--------------------------------

### Gtk.TextTag Common Formatting Properties

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/textview.rst

This section lists common properties available for Gtk.TextTag objects, which can be used to define various text formatting styles. These properties control aspects like colors, font styles, justification, and text wrapping.

```APIDOC
Gtk.TextTag Properties:
  background: string - Sets the background colour.
  foreground: string - Sets the foreground colour.
  underline: Pango.Underline - Sets the underline style (e.g., Pango.Underline.SINGLE).
  weight: int - Sets the font boldness (e.g., Pango.Weight.BOLD).
  style: Pango.Style - Sets the font style (e.g., Pango.Style.ITALIC).
  strikethrough: bool - Enables or disables strikethrough.
  justification: Gtk.Justification - Sets text alignment (e.g., Gtk.Justification.LEFT).
  size: int - Sets the font size in Pango units.
  size-points: float - Sets the font size in points.
  wrap-mode: Gtk.WrapMode - Sets text wrapping behavior (e.g., Gtk.WrapMode.WORD).
```

--------------------------------

### Gtk.TextMark API Reference for Position Preservation

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/textview.rst

Details Gtk.TextMark, used to preserve a position within a Gtk.TextBuffer even after modifications, unlike iterators.

```APIDOC
Gtk.TextMark:
  Description: A persistent position in a Gtk.TextBuffer that remains valid across buffer modifications.
  Methods:
    set_visible(visible: bool): None - Sets whether the mark is visible.
```

--------------------------------

### Synchronizing GTK Calls from Threaded Signal Handlers

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/threading.rst

This snippet illustrates a pattern for safely calling GTK code from a signal handler that is emitted from a different thread. It uses a `threading.Event` to synchronize the execution of the GTK-related function on the main thread and wait for its completion, preventing race conditions.

```python
# [...]

toggle_button = Gtk.ToggleButton()

def signal_handler_in_thread():

    def function_calling_gtk(event, result):
        result.append(toggle_button.get_active())
        event.set()

    event = threading.Event()
    result = []
```

--------------------------------

### Disconnect a GObject Signal Handler

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/basics.rst

To prevent a callback function from being called during future signal emissions, use the `gobject.disconnect` method. This function requires the `handler_id` obtained when the signal was initially connected.

```python
gobject.disconnect(handler_id)
```

--------------------------------

### Using Gtk.DialogFlags (GFlags) in PyGObject

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/api/flags_enums.rst

This snippet demonstrates how to interact with Gtk.DialogFlags, a subclass of GObject.GFlags. It shows accessing individual flag members, performing bitwise OR operations to combine flags, converting the combined flag value to an integer, instantiating a flag object from an integer, and verifying the type of a flag member.

```pycon
>>> Gtk.DialogFlags.MODAL
<DialogFlags.MODAL: 1>
>>> Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT
<DialogFlags.MODAL|DESTROY_WITH_PARENT: 3>
>>> int(_)
3
>>> Gtk.DialogFlags(3)
<DialogFlags.MODAL|DESTROY_WITH_PARENT: 3>
>>> isinstance(Gtk.DialogFlags.MODAL, Gtk.DialogFlags)
True
>>>
```

--------------------------------

### Define Read-Only GObject Properties using Decorator

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/subclassing.rst

This method allows defining read-only properties using the @GObject.Property decorator on a method. The method's return value becomes the property's value, and it cannot be directly set from external code.

```python
from gi.repository import GObject

class MyObject(GObject.Object):

    def __init__(self):
        super().__init__()

    @GObject.Property
    def readonly(self):
        return 'This is read-only.'
```

--------------------------------

### gi.PyGIDeprecationWarning Class

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/api/api.rst

This warning class is used for deprecations within PyGObject and its included Python overrides. It inherits from DeprecationWarning and is hidden by default.

```APIDOC
class gi.PyGIDeprecationWarning(DeprecationWarning)
```

--------------------------------

### Define GObject Property Setters for Read-Write Properties

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/subclassing.rst

Similar to Python's built-in property, GObject properties can have custom setters defined using the @property_name.setter decorator. This allows for custom logic to be executed when a property's value is assigned, such as validation or side effects.

```python
class AnotherObject(GObject.Object):
        value = 0

        @GObject.Property
        def prop(self):
            """Read only property."""
            return 1

        @GObject.Property(type=int)
        def prop_int(self):
            """Read-write integer property."""
            return self.value

        @prop_int.setter
        def prop_int(self, value):
            self.value = value
```

--------------------------------

### Defining a Custom GEnum in PyGObject

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/api/flags_enums.rst

This snippet demonstrates how to create a new enumeration type by subclassing GObject.GEnum, similar to standard Python enums. It shows how to define enum members and then access their values, value names, value nicks, and the automatically registered GType information, including the GType name.

```pycon
>>> from gi.repository import GObject
>>> class E(GObject.GEnum):
...     ONE = 1
...     TWO = 2
...
>>> E.ONE
<E.ONE: 1>
>>> E.ONE.value_name
'ONE'
>>> E.ONE.value_nick
'one'
>>> E.__gtype__
<GType __main__+E (1014834640)>
>>> E.__gtype__.name
'__main__+E'
```

--------------------------------

### Customizing GType Name for GObject Subclass in Python

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/api/gobject.rst

Explains how to explicitly define the `GType` name for a `GObject.Object` subclass by setting the `__gtype_name__` attribute. This allows developers to provide a custom, more descriptive name for the GType associated with their Python class, which can be useful for introspection and debugging.

```Python
>>> from gi.repository import GObject
>>> class B(GObject.Object):
...     __gtype_name__ = "MyName"
... 
>>> B.__gtype__
<GType MyName (94830143629776)>
>>> 
```

--------------------------------

### Specify GType Name for GObject Subclass

Source: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/subclassing.rst

When creating a new GObject subclass, you can explicitly define its GType name using the __gtype_name__ class attribute. This ensures the GObject type has a specific, recognizable name within the GObject type system.

```python
class MyWindow(Gtk.Window):
    __gtype_name__ = 'MyWindow'

    def __init__(self):
        super().__init__()
```

--------------------------------

### Temporarily Block GObject Signal Emissions (PyGObject)

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/api/signals.rst

Shows how to use `GObject.Object.handler_block` to temporarily prevent a connected signal handler from being invoked. This is demonstrated by blocking a 'notify::application-id' signal during a property change.

```pycon
>>> app = Gio.Application(application_id="foo.bar")
>>> def on_change(*args):
...     print(args)
... 
>>> c = app.connect("notify::application-id", on_change)
>>> app.props.application_id = "foo.bar"
(<Gio.Application object at 0x7f1bbb304550 (GApplication at 0x5630f1faf2b0)>, <GParamString 'application-id'>)
>>> with app.handler_block(c):
...     app.props.application_id = "no.change"
... 
>>> app.props.application_id = "change.again"
(<Gio.Application object at 0x7f1bbb304550 (GApplication at 0x5630f1faf2b0)>, <GParamString 'application-id'>)
>>>
```

=== COMPLETE CONTENT === This response contains all available snippets from this library. No additional content exists. Do not make further requests.s

--------------------------------
### Visualize Python cProfile Data with SnakeViz

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/debug_profile.rst

SnakeViz is a viewer for Python cProfile output, providing an interactive graphical representation of profiling data. It requires installation via pip and is used to visualize .prof files generated by cProfile.

```Bash
python -m cProfile -o prof.out quodlibet.py
snakeviz prof.out
```
--------------------------------
### Profile Python Application Performance with cProfile

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/debug_profile.rst

Utilize Python's built-in cProfile module to analyze application performance. It generates a detailed report of function calls and execution times, which can be sorted by various metrics like cumulative time or total time.

```Bash
python -m cProfile -s [sort_order] quodlibet.py > cprof.txt
```
--------------------------------
### Profile System-wide Performance with Sysprof

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/debug_profile.rst

Sysprof is a system-wide performance profiler for Linux, capable of capturing detailed system activity. It can be used to profile the execution of a Python application and then view the captured data.

```Bash
sysprof-cli -c "python quodlibet/quodlibet.py"
sysprof capture.syscap
```
--------------------------------
### Debug Python Applications with GDB

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/debug_profile.rst

GDB (GNU Debugger) can be used to debug Python applications, allowing users to run the application under the debugger and inspect its state. This is useful for low-level debugging or when dealing with crashes.

```Bash
gdb --args python quodlibet/quodlibet.py
# type "run" and hit enter
```
--------------------------------
### Detect GObject Instance Leaks with GOBJECT_DEBUG

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/debug_profile.rst

This method helps detect GObject instance leaks in GTK applications by enabling GObject debug mode and using the GTK Inspector's Statistics tab. It requires a debug build of glib and is recommended with jhbuild.

```Bash
jhbuild shell
GOBJECT_DEBUG=instance-count GTK_DEBUG=interactive ./quodlibet.py
```
--------------------------------
### Debug HiDPI Issues in GTK Applications

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/debug_profile.rst

Debugging HiDPI (High Dots Per Inch) issues involves simulating different display scales. This can be achieved by setting the GDK_SCALE environment variable or by using Mutter's dummy monitor features to test how an application renders at various scaling factors.

```Bash
GDK_SCALE=2 ./quodlibet/quodlibet.py
```

```Bash
MUTTER_DEBUG_NUM_DUMMY_MONITORS=2 MUTTER_DEBUG_DUMMY_MONITOR_SCALES=1,2 mutter --nested --wayland
# start your app, it should show up in the nested mutter
```
--------------------------------
### Debug Wayland Applications using Nested Compositors

Source: https://github.com/gnome/pygobject/blob/main/docs/guide/debug_profile.rst

To debug Wayland-related issues, applications can be run within a nested Wayland compositor like Mutter or Weston. This allows for isolated testing and observation of application behavior in a Wayland environment.

```Bash
mutter --nested --wayland
# start your app, it should show up in the nested mutter
```

```Bash
weston
# start your app, it should show up in the nested weston
```