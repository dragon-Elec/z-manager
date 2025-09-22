========================
CODE SNIPPETS
========================
TITLE: Install System-Provided PyGObject on openSUSE
DESCRIPTION: This snippet outlines how to install the system-provided PyGObject, GObject-Gdk, and GTK4 on openSUSE using `zypper`, followed by running a sample script.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/getting_started.rst#_snippet_9

LANGUAGE: Shell
CODE:
```
sudo zypper install python3-gobject python3-gobject-Gdk typelib-1_0-Gtk-4_0 libgtk-4-1
python3 hello.py
```

----------------------------------------

TITLE: Install System PyGObject and GTK 4 on Ubuntu/Debian
DESCRIPTION: This section outlines the process for installing PyGObject and GTK 4 on Ubuntu or Debian distributions using the system's package manager, apt. It includes commands to install the necessary Python GI bindings and GTK 4 libraries, followed by instructions to run the example application. This method utilizes pre-built packages for ease of installation.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/getting_started.rst#_snippet_2

LANGUAGE: shell
CODE:
```
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0
```

LANGUAGE: shell
CODE:
```
python3 hello.py
```

----------------------------------------

TITLE: Install PyGObject from PyPI on openSUSE
DESCRIPTION: This snippet details the process of installing PyGObject and Pycairo from PyPI on openSUSE, including necessary build dependencies, using `zypper` and `pip3`, followed by running a sample script.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/getting_started.rst#_snippet_10

LANGUAGE: Shell
CODE:
```
sudo zypper install cairo-devel pkg-config python3-devel gcc gobject-introspection-devel
pip3 install pycairo
pip3 install PyGObject
python3 hello.py
```

----------------------------------------

TITLE: Install System PyGObject and GTK 4 on Fedora
DESCRIPTION: This section provides instructions for installing PyGObject and GTK 4 on Fedora using the dnf package manager. It includes commands to install the necessary Python GObject bindings and GTK 4 libraries, followed by steps to run the example application. This method leverages Fedora's official repositories for stable installations.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/getting_started.rst#_snippet_4

LANGUAGE: shell
CODE:
```
sudo dnf install python3-gobject gtk4
```

LANGUAGE: shell
CODE:
```
python3 hello.py
```

----------------------------------------

TITLE: Install System PyGObject and GTK 4 on Arch Linux
DESCRIPTION: This section details the installation of PyGObject and GTK 4 on Arch Linux using the pacman package manager. It includes commands to install the necessary Python GObject bindings and GTK 4 libraries, followed by instructions to run the example application. This method utilizes Arch Linux's official repositories for a streamlined installation.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/getting_started.rst#_snippet_6

LANGUAGE: shell
CODE:
```
sudo pacman -S python-gobject gtk4
```

LANGUAGE: shell
CODE:
```
python3 hello.py
```

----------------------------------------

TITLE: Install PyGObject and GTK 4 on Windows (MSYS2)
DESCRIPTION: This section provides step-by-step instructions for installing PyGObject and GTK 4 on Windows using MSYS2. It covers downloading MSYS2, setting up the environment, installing necessary packages via pacman, and running a test application. Users should follow these commands in the MSYS2 UCRT64 terminal.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/getting_started.rst#_snippet_1

LANGUAGE: shell
CODE:
```
pacman -Suy
```

LANGUAGE: shell
CODE:
```
pacman -S mingw-w64-ucrt-x86_64-gtk4 mingw-w64-ucrt-x86_64-python3 mingw-w64-ucrt-x86_64-python3-gobject
```

LANGUAGE: shell
CODE:
```
gtk4-demo
```

LANGUAGE: shell
CODE:
```
python3 hello.py
```

----------------------------------------

TITLE: Create a Basic GTK Application with PyGObject
DESCRIPTION: This Python script demonstrates how to create a simple 'Hello World' GUI application using GTK 4.0 bindings provided by PyGObject. It initializes a Gtk.Application, sets up a main window, and presents it upon activation. This example serves as a foundational step for building more complex GTK applications.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/getting_started.rst#_snippet_0

LANGUAGE: python
CODE:
```
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

----------------------------------------

TITLE: Install PyGObject and Dependencies on Arch Linux
DESCRIPTION: This snippet provides instructions to install PyGObject, Pycairo, and their build dependencies on Arch Linux. It uses `pacman` for system packages and `pip3` for Python libraries, followed by running a sample script.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/getting_started.rst#_snippet_8

LANGUAGE: Shell
CODE:
```
sudo pacman -S python cairo pkgconf gobject-introspection gtk4
pip3 install pycairo
pip3 install PyGObject
python3 hello.py
```

----------------------------------------

TITLE: Building PyGObject with Meson
DESCRIPTION: This snippet provides the standard Meson commands required to build PyGObject from source. It covers configuring the build directory, compiling the project, running tests, and installing the compiled artifacts to a specified destination.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/devguide/packagingguide.rst#_snippet_0

LANGUAGE: Meson
CODE:
```
meson setup --prefix /usr --buildtype=plain _build -Dc_args=... -Dc_link_args=...
meson compile -C _build
meson test -C _build
DESTDIR=/path/to/staging/root meson install -C _build
```

----------------------------------------

TITLE: Install PyGObject and GTK 4 via Pip on Ubuntu/Debian
DESCRIPTION: This section details how to install PyGObject and GTK 4 within a Python virtual environment on Ubuntu or Debian using pip. It covers installing build dependencies, GTK, Pycairo, and PyGObject from PyPI, ensuring a self-contained development setup. This method is suitable for developers who prefer managing Python packages with pip.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/getting_started.rst#_snippet_3

LANGUAGE: shell
CODE:
```
sudo apt install libgirepository-2.0-dev gcc libcairo2-dev pkg-config python3-dev gir1.2-gtk-4.0
```

LANGUAGE: shell
CODE:
```
pip3 install pycairo
```

LANGUAGE: shell
CODE:
```
pip3 install PyGObject
```

LANGUAGE: shell
CODE:
```
python3 hello.py
```

----------------------------------------

TITLE: Install PyGObject and GTK4 on macOS with Homebrew
DESCRIPTION: This snippet provides instructions to install PyGObject and GTK4 on macOS using Homebrew, a popular package manager, followed by running a sample script.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/getting_started.rst#_snippet_11

LANGUAGE: Shell
CODE:
```
brew install pygobject3 gtk4
python3 hello.py
```

----------------------------------------

TITLE: Install PyGObject and GTK 4 via Pip on Arch Linux
DESCRIPTION: This section outlines the initial steps for installing PyGObject and GTK 4 within a Python virtual environment on Arch Linux using pip. It begins with installing build dependencies and GTK, preparing the environment for subsequent PyPI installations. This method offers flexibility for managing Python packages.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/getting_started.rst#_snippet_7

LANGUAGE: shell
CODE:
```
sudo pacman -S gcc gobject-introspection-devel cairo-gobject-devel pkg-config python-dev gtk4
```

----------------------------------------

TITLE: Create a Basic GTK4 Application Window with PyGObject
DESCRIPTION: This Python example initializes a GTK4 application using `gi.require_version` and defines a `Gtk.Application` subclass. It connects to the 'activate' signal to create and display an empty 200x200 pixel `Gtk.ApplicationWindow`, then starts the application's main loop.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/introduction.rst#_snippet_0

LANGUAGE: Python
CODE:
```
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

----------------------------------------

TITLE: Build an Extended GTK4 'Hello World' Application with PyGObject
DESCRIPTION: This Python example extends the basic GTK4 application by subclassing `Gtk.ApplicationWindow` to create a custom window. It adds a `Gtk.Button` that, when clicked, prints 'Hello World' to the console and closes the window. The application uses `Gtk.Application` for lifecycle management.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/introduction.rst#_snippet_2

LANGUAGE: Python
CODE:
```
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

----------------------------------------

TITLE: Install PyGObject and GTK 4 via Pip on Fedora
DESCRIPTION: This section describes how to install PyGObject and GTK 4 within a Python virtual environment on Fedora using pip. It covers installing build dependencies, GTK, Pycairo, and PyGObject from PyPI, providing a flexible installation option. This approach is ideal for developers who need specific versions or prefer pip for package management.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/getting_started.rst#_snippet_5

LANGUAGE: shell
CODE:
```
sudo dnf install gcc gobject-introspection-devel cairo-gobject-devel pkg-config python3-devel gtk4
```

LANGUAGE: shell
CODE:
```
pip3 install pycairo
```

LANGUAGE: shell
CODE:
```
pip3 install PyGObject
```

LANGUAGE: shell
CODE:
```
python3 hello.py
```

----------------------------------------

TITLE: Install and Configure pyenv on Linux
DESCRIPTION: Installs pyenv on Linux using the official installation script, initializes the shell, and then installs and sets Python 3.11 as the global version for environment management.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/devguide/dev_environ.rst#_snippet_6

LANGUAGE: console
CODE:
```
curl https://pyenv.run | bash
exec $SHELL
pyenv install 3.11
pyenv global 3.11
```

----------------------------------------

TITLE: Basic Gtk.Spinner Usage in Python
DESCRIPTION: This example demonstrates the fundamental usage of the `Gtk.Spinner` widget. It shows how to create a spinner, add it to a window, and control its animation using `start()` and `stop()` methods via buttons. The spinner is initially started upon window creation.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/display-widgets/spinner.rst#_snippet_0

LANGUAGE: Python
CODE:
```
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

class SpinnerWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Spinner Example")
        self.set_default_size(200, 100)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)

        self.spinner = Gtk.Spinner()
        vbox.pack_start(self.spinner, True, True, 0)

        start_button = Gtk.Button(label="Start Spinner")
        start_button.connect("clicked", self.on_start_clicked)
        vbox.pack_start(start_button, False, False, 0)

        stop_button = Gtk.Button(label="Stop Spinner")
        stop_button.connect("clicked", self.on_stop_clicked)
        vbox.pack_start(stop_button, False, False, 0)

        self.spinner.start() # Start by default

    def on_start_clicked(self, button):
        self.spinner.start()

    def on_stop_clicked(self, button):
        self.spinner.stop()

win = SpinnerWindow()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
```

----------------------------------------

TITLE: Python: Class Docstring with __init__ Arguments and Example
DESCRIPTION: Illustrates a Python class docstring that explains the class purpose, documents `__init__` arguments, and includes a nested code example demonstrating class usage, following reStructuredText conventions.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/devguide/style_guide.rst#_snippet_4

LANGUAGE: Python
CODE:
```
class Bacon(CookedFood):
    """Bacon is a breakfast food.

    :param CookingType cooking_type:
        Enum for the type of cooking to use.
    :param float cooking_time:
        Amount of time used to cook the Bacon in minutes.

    Use Bacon in combination with other breakfast foods for
    a complete breakfast. For example, combine Bacon with
    other items in a list to make a breakfast:

    .. code-block:: python

        breakfast = [Bacon(), Spam(), Spam(), Eggs()]

    """
    def __init__(self, cooking_type=CookingType.BAKE, cooking_time=15.0):
        super(Bacon, self).__init__(cooking_type, cooking_time)
```

----------------------------------------

TITLE: Set up PyGObject Development with PDM
DESCRIPTION: Initializes the PyGObject project using PDM, a modern Python package manager, to install dependencies and then demonstrates how to run the unit tests.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/devguide/dev_environ.rst#_snippet_9

LANGUAGE: console
CODE:
```
pdm install
```

LANGUAGE: console
CODE:
```
pdm run pytest
```

----------------------------------------

TITLE: Set up PyGObject Development with Pip Virtual Environment
DESCRIPTION: Creates a Python virtual environment for PyGObject development, activates it, and prepares it for installing Meson-related tools required for editable installs.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/devguide/dev_environ.rst#_snippet_10

LANGUAGE: console
CODE:
```
python3 -m venv .venv
source .venv/bin/activate
```

----------------------------------------

TITLE: Install and Configure pyenv on macOS
DESCRIPTION: Installs pyenv on macOS using Homebrew, then installs and sets Python 3.11 as the global version for managing multiple Python environments.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/devguide/dev_environ.rst#_snippet_7

LANGUAGE: console
CODE:
```
brew install pyenv
pyenv install 3.11
pyenv global 3.11
```

----------------------------------------

TITLE: Run PyGObject Tests Using Meson Build System
DESCRIPTION: These commands demonstrate how to set up the Meson build directory and then execute PyGObject tests through Meson. The `meson setup` command initializes the build directory, and `meson test` runs the tests, which still rely on Pytest.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/devguide/dev_environ.rst#_snippet_16

LANGUAGE: console
CODE:
```
meson setup _build
```

LANGUAGE: console
CODE:
```
meson test -C _build
```

----------------------------------------

TITLE: Install PyGObject using pip
DESCRIPTION: This command installs the PyGObject package from PyPI using pip. Note that PyGObject is distributed as a source distribution, requiring a C compiler to be installed on the host system.

SOURCE: https://github.com/gnome/pygobject/blob/main/README.rst#_snippet_0

LANGUAGE: Python
CODE:
```
pip install PyGObject
```

----------------------------------------

TITLE: Install PyGObject Development Dependencies on openSUSE
DESCRIPTION: Installs necessary packages for PyGObject development on openSUSE, covering Python wheel, gobject-introspection, Cairo, and core development tools.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/devguide/dev_environ.rst#_snippet_3

LANGUAGE: console
CODE:
```
sudo zypper install -y python3-wheel gobject-introspection-devel \
  python3-cairo-devel openssl zlib git
sudo zypper install --type pattern devel_basis
```

----------------------------------------

TITLE: Install Pre-commit Hooks for PyGObject Contributions
DESCRIPTION: This command installs the pre-commit hooks configured for the PyGObject repository. These hooks automatically run linting and code formatting tools before each commit, ensuring code quality and consistency for contributions.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/devguide/dev_environ.rst#_snippet_17

LANGUAGE: console
CODE:
```
pre-commit install
```

----------------------------------------

TITLE: Example Gtk.Application with Actions and Menus in Python
DESCRIPTION: This Python code demonstrates the basic structure of a GTK application using `Gtk.Application`. It sets up a main window, defines simple actions ('about', 'quit') using `Gio.SimpleAction`, and creates an application menu from an XML string using `Gio.Menu` and `Gtk.Builder`. It also includes a basic command-line handler.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/application.rst#_snippet_0

LANGUAGE: Python
CODE:
```
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio

class Application(Gtk.Application):
    def __init__(self):
        Gtk.Application.__init__(self, application_id="org.example.GtkApplication",
                                 flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.connect("activate", self.on_activate)
        self.connect("command-line", self.on_command_line)

    def on_activate(self, app):
        self.window = Gtk.ApplicationWindow(application=app, title="Gtk.Application Example")
        self.window.set_default_size(400, 300)

        # Create actions
        action_about = Gio.SimpleAction.new("about", None)
        action_about.connect("activate", self.on_about)
        self.add_action(action_about)

        action_quit = Gio.SimpleAction.new("quit", None)
        action_quit.connect("activate", self.on_quit)
        self.add_action(action_quit)

        # Set up menu
        menu_xml = """
        <?xml version="1.0" encoding="UTF-8"?>
        <interface>
          <menu id="app-menu">
            <section>
              <item>
                <title>_About</title>
                <action>app.about</action>
              </item>
              <item>
                <title>_Quit</title>
                <action>app.quit</action>
                <accel>_Q</accel>
              </item>
            </section>
          </menu>
        </interface>
        """
        builder = Gtk.Builder()
        builder.add_from_string(menu_xml)
        app_menu = builder.get_object("app-menu")
        self.set_app_menu(app_menu)

        # Add a header bar for the menu button
        header_bar = Gtk.HeaderBar()
        header_bar.set_show_close_button(True)
        header_bar.props.title = "Gtk.Application Example"
        self.window.set_titlebar(header_bar)

        menu_button = Gtk.MenuButton()
        menu_button.set_direction(Gtk.ArrowType.NONE)
        menu_button.set_image(Gtk.Image.new_from_icon_name("open-menu-symbolic", Gtk.IconSize.MENU))
        menu_button.set_popover(Gtk.Popover.new_from_model(app_menu))
        header_bar.pack_end(menu_button)

        self.window.show_all()

    def on_about(self, action, param):
        dialog = Gtk.AboutDialog()
        dialog.set_program_name("Gtk.Application Example")
        dialog.set_version("1.0")
        dialog.set_copyright("© 2023 Example")
        dialog.set_comments("A simple Gtk.Application example.")
        dialog.set_website("http://www.example.com")
        dialog.set_authors(["Your Name"])
        dialog.set_transient_for(self.window)
        dialog.run()
        dialog.destroy()

    def on_quit(self, action, param):
        self.quit()

    def on_command_line(self, app, command_line):
        options = command_line.get_options_dict()
        if options.contains("version"):
            print("Gtk.Application Example Version 1.0")
            return 0
        self.activate()
        return 0

if __name__ == "__main__":
    import sys
    app = Application()
    exit_status = app.run(sys.argv)
    sys.exit(exit_status)
```

----------------------------------------

TITLE: Basic GTK Application with PyGObject
DESCRIPTION: This snippet demonstrates how to create a basic 'Hello World' GTK application using PyGObject. It initializes a GTK application, sets its ID and name, and creates a simple window that is presented upon activation. This example illustrates the fundamental structure for a PyGObject-based GUI application.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/index.rst#_snippet_0

LANGUAGE: python
CODE:
```
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

----------------------------------------

TITLE: Install Core Development Dependencies for PyGObject
DESCRIPTION: This command installs essential Python packages required for developing and testing PyGObject, including build tools like meson and ninja, and testing frameworks like pytest. It ensures the environment is set up for compilation and quality assurance.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/devguide/dev_environ.rst#_snippet_11

LANGUAGE: console
CODE:
```
python3 -m pip install meson-python meson ninja pycairo pytest pre-commit
```

----------------------------------------

TITLE: Display a Minimal GTK4 Window without Gtk.Application in Python
DESCRIPTION: This Python snippet demonstrates creating a basic GTK4 window without relying on `Gtk.Application`. It manually iterates the GLib main context to keep the window open until all top-level windows are closed. This approach is generally recommended only for specific use cases like testing.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/introduction.rst#_snippet_1

LANGUAGE: Python
CODE:
```
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import GLib, Gtk

win = Gtk.Window()
win.present()

while (len(Gtk.Window.get_toplevels()) > 0):
    GLib.MainContext.default().iteration(True)
```

----------------------------------------

TITLE: Adw.Application Class Overview
DESCRIPTION: Documents the core `Adw.Application` class, its inheritance from `Gtk.Application`, and its automatic initialization of the Adwaita library, ensuring proper setup of translations, types, themes, icons, and stylesheets.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/tutorials/libadwaita/application.rst#_snippet_0

LANGUAGE: APIDOC
CODE:
```
Adw.Application:
  Extends: Gtk.Application
  Purpose: Eases tasks related to creating applications for GNOME.
  Automatic Initialization: Calls Adw.init() upon instantiation, setting up translations, types, themes, icons, and stylesheets.
```

----------------------------------------

TITLE: Build, Tag, and Upload PyGObject Release
DESCRIPTION: Provides a sequence of commands to build a new PyGObject distribution, create a signed Git tag for the release version, push the tag to the remote repository, and optionally upload the distribution to PyPI for stable releases.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/devguide/maintguide.rst#_snippet_0

LANGUAGE: Shell
CODE:
```
python3 -m build --sdist
```

LANGUAGE: Shell
CODE:
```
git tag -s 3.X.Y -m "release 3.X.Y"
```

LANGUAGE: Shell
CODE:
```
git push origin 3.X.Y
```

LANGUAGE: Shell
CODE:
```
twine upload dist/pygobject-3.X.Y.tar.gz
```

----------------------------------------

TITLE: Set GObject Properties During Initialization in Python
DESCRIPTION: Properties can be set as keyword arguments when creating a GObject instance. This example creates a right-aligned Gtk.Label with 'Hello World' text.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/basics.rst#_snippet_1

LANGUAGE: python
CODE:
```
label = Gtk.Label(label='Hello World', halign=Gtk.Align.END)
```

----------------------------------------

TITLE: Install PyGObject Development Dependencies on Arch Linux
DESCRIPTION: Installs essential packages for PyGObject development on Arch Linux, including Python wheel, base development tools, and gobject-introspection libraries.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/devguide/dev_environ.rst#_snippet_2

LANGUAGE: console
CODE:
```
sudo pacman -S --noconfirm python-wheel
sudo pacman -S --noconfirm base-devel openssl zlib git gobject-introspection
```

----------------------------------------

TITLE: Install PyGObject Development Dependencies on macOS (Homebrew)
DESCRIPTION: Installs core dependencies for PyGObject development on macOS using Homebrew, including Python 3, gobject-introspection, and libffi, then sets the PKG_CONFIG_PATH.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/devguide/dev_environ.rst#_snippet_5

LANGUAGE: console
CODE:
```
brew update
brew install python3 gobject-introspection libffi
export PKG_CONFIG_PATH=$(brew --prefix libffi)/lib/pkgconfig  # use /usr/local/ for older Homebrew installs
```

----------------------------------------

TITLE: Install PyGObject Development Dependencies on Ubuntu/Debian
DESCRIPTION: Installs necessary packages for compiling Python and PyGObject on Ubuntu or Debian, including build tools, introspection libraries, and development headers required for the project.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/devguide/dev_environ.rst#_snippet_0

LANGUAGE: console
CODE:
```
sudo apt-get install -y python3-venv python3-wheel python3-dev
sudo apt-get install -y gobject-introspection libgirepository-2.0-dev \
  gir1.2-girepository-3.0 build-essential libbz2-dev libreadline-dev \
  libssl-dev zlib1g-dev libsqlite3-dev wget curl llvm libncurses-dev \
  xz-utils tk-dev libcairo2-dev
```

----------------------------------------

TITLE: PyGObject Gtk.Grid Layout Example
DESCRIPTION: An example demonstrating the use of Gtk.Grid for arranging widgets, typically showing how to attach children with specific column and row spans.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/layout-widgets.rst#_snippet_7

LANGUAGE: Python
CODE:
```
# Code for Gtk.Grid layout example (from examples/layout_grid.py)
# This content is typically a Python script demonstrating Gtk.Grid usage.
# Example: grid.attach(widget, left, top, width, height)
```

----------------------------------------

TITLE: Install PyGObject Development Dependencies on Windows (MSYS2)
DESCRIPTION: Installs required development tools and libraries within MSYS2 for PyGObject development on Windows, including Python, PyCairo, gobject-introspection, and libffi.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/devguide/dev_environ.rst#_snippet_4

LANGUAGE: console
CODE:
```
pacman -S --needed --noconfirm base-devel mingw-w64-ucrt-x86_64-toolchain git \
       mingw-w64-ucrt-x86_64-python mingw-w64-ucrt-x86_64-pycairo \
       mingw-w64-ucrt-x86_64-gobject-introspection mingw-w64-ucrt-x86_64-libffi
```

----------------------------------------

TITLE: Run PyGObject Unit Tests with Pytest
DESCRIPTION: This command executes the PyGObject unit tests using the pytest framework. It's a quick way to verify the integrity and functionality of the installed PyGObject library and any local changes.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/devguide/dev_environ.rst#_snippet_15

LANGUAGE: console
CODE:
```
pytest
```

----------------------------------------

TITLE: Install PyGObject in Editable Development Mode
DESCRIPTION: This command installs PyGObject in an editable development mode, disabling build isolation to allow dynamic rebuilds. It also enables the 'tests' build option, making it suitable for active development and testing.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/devguide/dev_environ.rst#_snippet_12

LANGUAGE: console
CODE:
```
pip install --no-build-isolation --config-settings=setup-args="-Dtests=true" -e '.[dev]'
```

----------------------------------------

TITLE: PyGObject Gtk.FlowBox Layout Example
DESCRIPTION: An example demonstrating the use of Gtk.FlowBox for arranging widgets in a flowing grid, typically showing how to add and manage flow box children.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/layout-widgets.rst#_snippet_11

LANGUAGE: Python
CODE:
```
# Code for Gtk.FlowBox layout example (from examples/layout_flowbox.py)
# This content is typically a Python script demonstrating Gtk.FlowBox usage.
# Example: flowbox.append(Gtk.Button("Click Me"))
```

----------------------------------------

TITLE: Install PyGObject Development Dependencies on Fedora
DESCRIPTION: Installs required packages for PyGObject development on Fedora, including Python wheel, GCC, and various development libraries for introspection and GUI components.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/devguide/dev_environ.rst#_snippet_1

LANGUAGE: console
CODE:
```
sudo dnf install -y python3-wheel
sudo dnf install -y gcc zlib-devel bzip2 bzip2-devel readline-devel \
  sqlite sqlite-devel openssl-devel tk-devel git python3-cairo-devel \
  cairo-gobject-devel gobject-introspection-devel
```

----------------------------------------

TITLE: Gtk.Switch Widget Usage Example (Python)
DESCRIPTION: Demonstrates the correct implementation and signal handling for a Gtk.Switch widget in PyGObject. It highlights the recommended practice of connecting to the 'notify::active' signal to respond to state changes, rather than the 'activate' signal.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/controls/switch.rst#_snippet_0

LANGUAGE: Python
CODE:
```
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

class MyWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Switch Example")
        self.set_border_width(10)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)

        label = Gtk.Label(label="Toggle the switch:")
        vbox.pack_start(label, False, False, 0)

        self.switch = Gtk.Switch()
        self.switch.set_active(True) # Initial state
        self.switch.connect("notify::active", self.on_switch_activated)
        vbox.pack_start(self.switch, False, False, 0)

    def on_switch_activated(self, switch, gparam):
        if switch.get_active():
            print("Switch is ON")
        else:
            print("Switch is OFF")

win = MyWindow()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
```

----------------------------------------

TITLE: Arrange Widgets with GTK CenterBox
DESCRIPTION: Demonstrates the use of Gtk.CenterBox to arrange three children (start, center, end) in a row or column, ensuring the middle child is centered. This example sets up a window with a horizontal CenterBox containing a start button, a centered label, and an end button.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/layout-widgets.rst#_snippet_4

LANGUAGE: Python
CODE:
```
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

class MyWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="CenterBox Example")
        self.set_default_size(400, 200)

        center_box = Gtk.CenterBox(orientation=Gtk.Orientation.HORIZONTAL)
        self.add(center_box)

        start_button = Gtk.Button(label="Start")
        center_label = Gtk.Label(label="Centered Content")
        end_button = Gtk.Button(label="End")

        center_box.set_start_widget(start_button)
        center_box.set_center_widget(center_label)
        center_box.set_end_widget(end_button)

win = MyWindow()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
```

----------------------------------------

TITLE: Import GObject from PyGObject
DESCRIPTION: This Python snippet demonstrates how to import the GObject module from the gi.repository, which is the entry point for accessing GTK and GLib functionalities in PyGObject applications. It's a fundamental step to start using PyGObject.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/devguide/dev_environ.rst#_snippet_14

LANGUAGE: python
CODE:
```
from gi.repository import GObject
```

----------------------------------------

TITLE: PyGObject Gtk.ListBox Layout Example
DESCRIPTION: An example demonstrating the use of Gtk.ListBox for creating a scrollable list of items, typically showing how to add and manage list rows.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/layout-widgets.rst#_snippet_9

LANGUAGE: Python
CODE:
```
# Code for Gtk.ListBox layout example (from examples/layout_listbox.py)
# This content is typically a Python script demonstrating Gtk.ListBox usage.
# Example: listbox.append(Gtk.Label("Item"))
```

----------------------------------------

TITLE: Install PyGObject with Debug Symbols Enabled
DESCRIPTION: Use this command to install PyGObject with C libraries compiled in 'debug' mode, including debug symbols. This is useful for debugging C-level issues within the PyGObject bindings, while also enabling tests.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/devguide/dev_environ.rst#_snippet_13

LANGUAGE: console
CODE:
```
pip install --no-build-isolation --config-settings=setup-args="-Dbuildtype=debug" --config-settings=setup-args="-Dtests=true" -e '.[dev]'
```

----------------------------------------

TITLE: Getting and Setting GObject Properties in Python
DESCRIPTION: Illustrates the use of `get_property()` and `set_property()` methods to retrieve and modify property values of a `GObject` instance. The example demonstrates that both underscore and hyphenated property names can be used with `get_property()`, but `set_property()` typically expects the Pythonic underscore version if the constructor used it.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/guide/api/properties.rst#_snippet_2

LANGUAGE: pycon
CODE:
```
>>> app = Gio.Application(application_id="foo.bar")
>>> app
<Gio.Application object at 0x7f7499284fa0 (GApplication at 0x564b571e7c00)>
>>> app.get_property("application_id")
'foo.bar'
>>> app.set_property("application_id", "a.b")
>>> app.get_property("application-id")
'a.b'
```

----------------------------------------

TITLE: Implement a GTK HeaderBar as Window Titlebar
DESCRIPTION: Shows how to create and use a Gtk.HeaderBar as a custom window titlebar. It allows placement of widgets at the start and end, and a centered title. This example configures a HeaderBar with a custom title and adds 'Menu' and 'Settings' buttons.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/layout-widgets.rst#_snippet_5

LANGUAGE: Python
CODE:
```
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

class MyWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="HeaderBar Example")
        self.set_default_size(400, 200)

        header_bar = Gtk.HeaderBar()
        header_bar.set_show_title_buttons(True)
        header_bar.set_title("My Application")
        self.set_titlebar(header_bar)

        # Add a button to the start
        start_button = Gtk.Button(label="Menu")
        header_bar.pack_start(start_button)

        # Add a button to the end
        end_button = Gtk.Button(label="Settings")
        header_bar.pack_end(end_button)

win = MyWindow()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
```

----------------------------------------

TITLE: Define a GObject Signal Callback Function
DESCRIPTION: This example shows the basic structure for defining a callback function that will be executed when a signal is emitted. The callback typically receives the GObject instance that triggered the signal and any optional data passed during connection. Subsequent arguments depend on the specific signal.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/basics.rst#_snippet_12

LANGUAGE: python
CODE:
```
def on_event(gobject, data):
    ...

my_object.connect('event', on_event, data)
```

----------------------------------------

TITLE: Python: Function Docstring with reStructuredText
DESCRIPTION: Provides an example of a Python function docstring adhering to PEP 257 and reStructuredText (reST) annotations, including parameters with types, return types, and raised exceptions for comprehensive documentation.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/devguide/style_guide.rst#_snippet_3

LANGUAGE: Python
CODE:
```
def spam(amount):
    """Creates a Spam object with the given amount.

    :param int amount:
        The amount of spam.
    :returns:
        A new Spam instance with the given amount set.
    :rtype: Spam
    :raises ValueError:
        If amount is not a numeric type.

    More complete description.
    """
```

----------------------------------------

TITLE: Create and Push PyGObject Stable Branch
DESCRIPTION: Details the commands required to create a new local stable branch from the current state and push it to the remote repository, typically done after a feature freeze to allow continued development on the main branch.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/devguide/maintguide.rst#_snippet_1

LANGUAGE: Shell
CODE:
```
git checkout -b pygobject-3-2
```

LANGUAGE: Shell
CODE:
```
git push origin pygobject-3-2
```

----------------------------------------

TITLE: Using Gtk.PopoverMenu with Gio.MenuModel in PyGObject
DESCRIPTION: This example demonstrates how to create and display a `Gtk.PopoverMenu` from a `Gio.MenuModel`, often used in conjunction with `Gtk.MenuButton`. It illustrates how to define menu actions and associate them with the popover, providing a dynamic and structured way to present menu options to the user.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/popovers.rst#_snippet_1

LANGUAGE: Python
CODE:
```
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

----------------------------------------

TITLE: Displaying an Image with Gtk.Picture in Python
DESCRIPTION: This Python example demonstrates how to create a `Gtk.Picture` widget, load an image (either from a file or as a resource), and configure its display properties such as `content_fit` and alignment within a `Gtk.ApplicationWindow`. This snippet requires GTK 4.8 or newer.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/display-widgets/picture.rst#_snippet_1

LANGUAGE: Python
CODE:
```
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

----------------------------------------

TITLE: Defining Custom GObject Properties with Decorator in Python
DESCRIPTION: Presents a Python example demonstrating how to use the `GObject.Property` decorator to define custom properties within a `GObject.Object` subclass. It shows examples of both a read-only property and a read-write integer property with a setter method.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/guide/api/properties.rst#_snippet_6

LANGUAGE: python
CODE:
```
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

----------------------------------------

TITLE: Define Gtk.Template with XML String and Basic Widgets
DESCRIPTION: This example demonstrates the fundamental usage of Gtk.Template by embedding the GtkBuilder UI definition directly as a string. It shows how to decorate a Gtk.Box subclass with @Gtk.Template, define the __gtype_name__, declare a Gtk.Template.Child for a GtkButton, and connect a signal handler using @Gtk.Template.Callback.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/guide/gtk_template.rst#_snippet_0

LANGUAGE: python
CODE:
```
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

----------------------------------------

TITLE: Subclassing GObject with Constructor Arguments
DESCRIPTION: This example illustrates how to pass arguments to the parent GObject's constructor using super().__init__(). This allows for initializing or modifying properties of the parent GObject, such as setting a window title during instantiation.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/subclassing.rst#_snippet_1

LANGUAGE: python
CODE:
```
class MyWindow(Gtk.Window):

    def __init__(self):
        super().__init__(title='Custom title')
```

----------------------------------------

TITLE: Bind GObject Properties with Custom Transformations in Python
DESCRIPTION: Demonstrates using `bind_property` with custom transformation functions (`transform_to`, `transform_from`) to handle incompatible property types or apply logic during binding. This example converts between integer and boolean types bidirectionally.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/basics.rst#_snippet_6

LANGUAGE: python
CODE:
```
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

----------------------------------------

TITLE: PyGObject Automatic Type Mappings Reference
DESCRIPTION: A reference guide to how PyGObject automatically converts various Glib and C data types into their corresponding Python equivalents, covering number, text, and common collection types.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/guide/api/basic_types.rst#_snippet_1

LANGUAGE: APIDOC
CODE:
```
PyGObject Type Mappings:
- Glib integer types <-> Python int, float (OverflowError for out-of-range values)
- Text types <-> Python str
- GList <-> Python list
- GSList <-> Python list
- GHashTable <-> Python dict
- arrays <-> Python list
```

----------------------------------------

TITLE: Synchronous File Content Loading Example
DESCRIPTION: This snippet presents a synchronous approach to loading file contents from a URI using `Gio.File.load_contents()`. It serves as a comparison to asynchronous methods, demonstrating a blocking operation that fetches data directly and handles potential `GLib.GError` exceptions.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/guide/asynchronous.rst#_snippet_3

LANGUAGE: python
CODE:
```
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

----------------------------------------

TITLE: Visualize Python cProfile Data with SnakeViz
DESCRIPTION: SnakeViz is a viewer for Python cProfile output, providing an interactive graphical representation of profiling data. It requires installation via pip and is used to visualize .prof files generated by cProfile.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/guide/debug_profile.rst#_snippet_2

LANGUAGE: Bash
CODE:
```
python -m cProfile -o prof.out quodlibet.py
snakeviz prof.out
```

----------------------------------------

TITLE: Ensuring Specific Library Versions in PyGObject
DESCRIPTION: To guarantee that a specific version of a library is used, this example shows how to employ `gi.require_version()` before importing the desired modules like Gtk and GLib.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/guide/imports.rst#_snippet_1

LANGUAGE: Python
CODE:
```
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('GLib', '2.0')
from gi.repository import Gtk, GLib
```

----------------------------------------

TITLE: Set Gtk.Label Markup with Hyperlink
DESCRIPTION: This Python example demonstrates how to set the text of a `Gtk.Label` using Pango Markup to include a clickable hyperlink. The `set_markup` method is used, allowing HTML-like `<a>` tags with `href` for the URL and `title` for the tooltip. This enables interactive text display within the label.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/display-widgets/label.rst#_snippet_0

LANGUAGE: Python
CODE:
```
label.set_markup("Go to <a href=\"https://www.gtk.org\" title=\"Our website\">GTK+ website</a> for more")
```

----------------------------------------

TITLE: Subclassing GObject.Object in Python
DESCRIPTION: Demonstrates the basic process of subclassing `GObject.Object` in Python. This operation automatically creates a new `GObject.GType` that is linked to the Python class, making it compatible with GObject APIs. The example shows how to instantiate the subclass and inspect its automatically generated `__gtype__` and `__gtype__.name`.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/guide/api/gobject.rst#_snippet_0

LANGUAGE: Python
CODE:
```
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

----------------------------------------

TITLE: Create and Pack Widgets in a GTK Box Container
DESCRIPTION: Demonstrates how to create a Gtk.Box and pack multiple Gtk.Button widgets into it. The box arranges children horizontally or vertically, and its size is determined by its contents. This example sets up a basic window with a horizontal box containing two buttons.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/layout-widgets.rst#_snippet_1

LANGUAGE: Python
CODE:
```
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

class MyWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Box Example")
        self.set_default_size(400, 200)

        # Create a horizontal box with 6 pixels spacing
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.add(hbox)

        # Add two buttons to the box
        button1 = Gtk.Button(label="Button 1")
        button2 = Gtk.Button(label="Button 2")

        hbox.pack_start(button1, True, True, 0)
        hbox.pack_start(button2, True, True, 0)

win = MyWindow()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
```

----------------------------------------

TITLE: Gtk.Template with Custom Subclass as XML Object
DESCRIPTION: This example shows how to integrate a custom Gtk.Button subclass (HelloButton) directly into the Gtk.Template XML definition. It highlights that any subclass declaring a __gtype_name__ can be instantiated as an object within the UI template, allowing for reusable custom widgets.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/guide/gtk_template.rst#_snippet_2

LANGUAGE: python
CODE:
```
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

----------------------------------------

TITLE: GObject.Object.weak_ref Method
DESCRIPTION: Registers a callback to be called when the underlying GObject gets finalized. The callback will receive the given `user_data`. To unregister the callback, call the `unref()` method of the returned GObjectWeakRef object.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/guide/api/weakrefs.rst#_snippet_0

LANGUAGE: APIDOC
CODE:
```
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

----------------------------------------

TITLE: Verifying Instance Consistency with GObject Subclasses and Gio.ListStore
DESCRIPTION: Demonstrates how `GObject.Object` ensures instance consistency when working with GObject containers like `Gio.ListStore`. The example shows creating a `Gio.ListStore` for a custom `GObject.Object` subclass, appending an instance, and then retrieving it. It verifies that the Python instance returned from the store is precisely the same object that was originally added, highlighting the robust wrapping mechanism.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/guide/api/gobject.rst#_snippet_3

LANGUAGE: Python
CODE:
```
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

----------------------------------------

TITLE: Create GObject Signals using @GObject.Signal Decorator
DESCRIPTION: This example illustrates how to define new signals in a PyGObject class using the `@GObject.Signal` decorator. It shows how to create signals with and without arguments, specify signal flags (e.g., `RUN_LAST`), and connect Python functions as callbacks. The snippet also demonstrates how to emit the defined signals.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gobject/subclassing.rst#_snippet_10

LANGUAGE: Python
CODE:
```
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

----------------------------------------

TITLE: Create and Manage Asyncio Tasks with GLib Event Loop
DESCRIPTION: After configuring the GLib event loop policy, this example shows how to retrieve the active event loop and create an asynchronous task using `loop.create_task()`. It highlights the process of scheduling a coroutine for execution within the GLib-integrated `asyncio` environment.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/guide/asynchronous.rst#_snippet_1

LANGUAGE: python
CODE:
```
loop = policy.get_event_loop()


async def do_some_work():
    await asyncio.sleep(2)
    print("Done working!")


task = loop.create_task(do_some_work())
```

----------------------------------------

TITLE: Define and Emit Custom GObject Signals (PyGObject)
DESCRIPTION: Provides a practical example of defining custom signals within a `GObject.Object` subclass using the `GObject.Signal` decorator. It demonstrates how to connect a handler to a custom signal and then emit the signal with arguments.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/guide/api/signals.rst#_snippet_4

LANGUAGE: python
CODE:
```
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

----------------------------------------

TITLE: Creating and Displaying a Custom Gtk.Popover in PyGObject
DESCRIPTION: This example demonstrates how to create a custom `Gtk.Popover`, set its child widget, and attach it to a parent widget. It shows how to configure its position and visibility, and how to open and hide it programmatically. The popover is typically used for displaying contextual information or custom controls.

SOURCE: https://github.com/gnome/pygobject/blob/main/docs/tutorials/gtk4/popovers.rst#_snippet_0

LANGUAGE: Python
CODE:
```
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