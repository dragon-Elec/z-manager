# Libadwaita 1.4/1.5 Complete Reference

> **Target:** Libadwaita <= 1.5 (Ubuntu 24.04, Fedora 40).
> **Avoid:** 1.6+ widgets like `AdwSpinner`, `AdwButtonRow`, `AdwMultiLayoutView`.

---

## 1. Application & Window Structure

### AdwApplication (Use instead of GtkApplication)
```python
# Python
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio

class MyApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.example.ZManager",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = self.props.active_window
        if not win:
             win = MainWindow(self)
        win.present()
```

### AdwWindow & AdwToolbarView (The modern window layout)
Replaces `GtkBox` for header/content/footer.
```xml
<object class="AdwWindow">
  <property name="width-request">360</property>
  <property name="height-request">294</property>
  <property name="content">
    <object class="AdwToolbarView">
      <child type="top">
        <object class="AdwHeaderBar"/>
      </child>
      <property name="content">
        <!-- Main View -->
      </property>
      <child type="bottom">
        <object class="GtkActionBar"/>
      </child>
    </object>
  </property>
</object>
```

---

## 2. Dialogs (1.5+)

### AdwAlertDialog (Simple Alerts/Confirmations)
Replaces `GtkMessageDialog`.
```python
dialog = Adw.AlertDialog(heading="Confirm Action?", body="This cannot be undone.")
dialog.add_response("cancel", "_Cancel")
dialog.add_response("confirm", "_Confirm")
dialog.set_response_appearance("confirm", Adw.ResponseAppearance.DESTRUCTIVE)
dialog.choose(parent, None, on_response_callback)
```

### Custom AdwDialog (Complex Popups)
For device pickers, custom forms, etc.
```xml
<object class="AdwDialog">
  <property name="content-width">400</property>
  <property name="content-height">500</property>
  <property name="child">
    <object class="AdwToolbarView">
      <child type="top"><object class="AdwHeaderBar"/></child>
      <property name="content"><!-- Your custom list/form --></property>
    </object>
  </property>
</object>
```

---

## 3. Navigation & Views

### AdwViewStack + AdwViewSwitcher (Tab Pages)
Used for Status/Configure/Tune pages.
```xml
<object class="AdwViewStack" id="main_stack">
  <child>
    <object class="AdwViewStackPage">
      <property name="name">status</property>
      <property name="title">Status</property>
      <property name="icon-name">utilities-system-monitor-symbolic</property>
      <property name="child"><!-- StatusPage widget --></property>
    </object>
  </child>
</object>
<!-- In HeaderBar: -->
<object class="AdwViewSwitcher">
  <property name="stack">main_stack</property>
  <property name="policy">wide</property>
</object>
```

### AdwNavigationSplitView (Sidebar/Content)
For list-detail views. Collapses on mobile.
```xml
<object class="AdwNavigationSplitView" id="split_view">
  <property name="sidebar">
    <object class="AdwNavigationPage">
      <property name="title">Devices</property>
      <property name="child"><!-- Device List --></property>
    </object>
  </property>
  <property name="content">
    <object class="AdwNavigationPage">
      <property name="title">Details</property>
      <property name="child"><!-- Device Details --></property>
    </object>
  </property>
</object>
```

---

## 4. Lists & Rows

### Boxed List Pattern
```xml
<object class="GtkListBox">
  <property name="selection-mode">none</property>
  <style><class name="boxed-list"/></style>
  <!-- AdwActionRow, AdwSwitchRow, etc. -->
</object>
```

### AdwPreferencesGroup (Grouped Settings)
Provides a title + boxed list.
```xml
<object class="AdwPreferencesGroup">
  <property name="title">ZRAM Configuration</property>
  <property name="description">Adjust device parameters.</property>
  <!-- Rows go here -->
</object>
```

### Row Types (All 1.4+)
| Widget | Use Case |
|--------|----------|
| `AdwActionRow` | Basic row with title, subtitle, prefix/suffix widgets |
| `AdwSwitchRow` | Boolean toggle (on/off) |
| `AdwSpinRow` | Numeric input (e.g., Swappiness 0-100) |
| `AdwComboRow` | Dropdown selection |
| `AdwEntryRow` | Text input with apply button |
| `AdwExpanderRow` | Collapsible section with child rows |

**AdwSpinRow Example:**
```xml
<object class="AdwSpinRow">
  <property name="title">Swappiness</property>
  <property name="subtitle">0 (aggressive) to 100 (passive)</property>
  <property name="adjustment">
    <object class="GtkAdjustment">
      <property name="lower">0</property>
      <property name="upper">100</property>
      <property name="value">60</property>
      <property name="step-increment">1</property>
    </object>
  </property>
</object>
```

**AdwEntryRow Example:**
```xml
<object class="AdwEntryRow">
  <property name="title">Writeback Device Path</property>
  <property name="text">/dev/loop0</property>
  <property name="show-apply-button">True</property>
  <signal name="apply" handler="on_writeback_path_apply"/>
</object>
```

**`.property` Style (Read-only display):**
```xml
<object class="AdwActionRow">
  <property name="title">Compression Ratio</property>
  <property name="subtitle">3.2x</property>
  <property name="subtitle-selectable">True</property>
  <style><class name="property"/></style>
</object>
```

---

## 5. Empty States & Feedback

### AdwStatusPage (Empty/Error States)
```xml
<object class="AdwStatusPage">
  <property name="icon-name">drive-harddisk-symbolic</property>
  <property name="title">No ZRAM Devices Found</property>
  <property name="description">Create a new device to get started.</property>
  <property name="child">
    <object class="GtkButton">
      <property name="label">Create Device</property>
      <property name="halign">center</property>
      <style><class name="pill"/><class name="suggested-action"/></style>
    </object>
  </property>
</object>
```

### AdwToast (Notifications)
```python
toast = Adw.Toast.new("Configuration saved!")
toast.set_timeout(3)
# Requires AdwToastOverlay wrapping your main view:
toast_overlay.add_toast(toast)
```
```xml
<object class="AdwToastOverlay">
  <property name="child"><!-- Your main content --></property>
</object>
```

---

## 6. Responsiveness (Breakpoints)

Change UI properties based on window size.
```xml
<object class="AdwWindow">
  <child>
    <object class="AdwBreakpoint">
      <condition>max-width: 500sp</condition>
      <setter object="split_view" property="collapsed">True</setter>
      <setter object="mobile_button" property="visible">True</setter>
    </object>
  </child>
  <!-- ... -->
</object>
```

---

## 7. Theming & Style

### AdwStyleManager (Dark Mode)
```python
manager = Adw.StyleManager.get_default()
manager.set_color_scheme(Adw.ColorScheme.PREFER_DARK)  # or FORCE_DARK, PREFER_LIGHT
```

### CSS Variables
```css
/* Accent Colors */
my-widget {
  background-color: var(--accent-bg-color);
  color: var(--accent-fg-color);
}

/* Destructive Colors */
.destructive-action {
  background-color: var(--destructive-bg-color);
  color: var(--destructive-fg-color);
}

/* Window Background */
.background {
  background-color: var(--window-bg-color);
  color: var(--window-fg-color);
}
```

---

## 8. About Dialog (1.5+)

```python
Adw.show_about_dialog(
    parent,
    application_name="Z-Manager",
    application_icon="com.example.zmanager",
    developer_name="Your Name",
    version="1.0.0",
    website="https://github.com/...",
    issue_url="https://github.com/.../issues",
    license_type=Gtk.License.GPL_3_0,
)
```

---

## 9. Button Styling

### AdwButtonContent (Icon + Label)
```xml
<object class="GtkButton">
  <property name="child">
    <object class="AdwButtonContent">
      <property name="icon-name">list-add-symbolic</property>
      <property name="label">Add Device</property>
    </object>
  </property>
</object>
```

### Style Classes
- `.suggested-action` - Primary action (blue)
- `.destructive-action` - Dangerous action (red)
- `.pill` - Rounded button
- `.circular` - Circular icon button
- `.flat` - No background
- `.opaque` - Force opaque background

---

## 10. AdwClamp (Content Max Width)

Constrains content width for readability.
```xml
<object class="AdwClamp">
  <property name="maximum-size">600</property>
  <property name="child">
    <object class="GtkBox"><!-- Your content --></object>
  </property>
</object>
```

---

## 11. Core PyGObject Patterns

### Gtk.Template with Python Classes
Connecting Python classes to `.ui` files.
```python
@Gtk.Template(filename=get_ui_path("status_page.ui"))
class StatusPage(Adw.Bin):
    __gtype_name__ = "StatusPage"
    
    # Binding children defined in XML with `id="my_button"`
    my_button = Gtk.Template.Child()
    
    # Binding signals defined in XML with `handler="on_clicked"`
    @Gtk.Template.Callback()
    def on_clicked(self, widget):
        print("Clicked!")
```

### Custom Signals (@GObject.Signal)
Define events for your components.
```python
from gi.repository import GObject

class MyWidget(Gtk.Widget):
    # Define signal: "name", flags, return_type, argument_types
    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=(str,))
    def data_changed(self, new_data):
        print(f"Data changed check: {new_data}")

    def update(self, data):
        self.emit("data_changed", data)
```

### Asyncio Integration
```python
import asyncio
from gi.events import GLibEventLoopPolicy

# Allow Asyncio to work with GTK loop
asyncio.set_event_loop_policy(GLibEventLoopPolicy())
# Usage:
# loop.create_task(my_async_func())
```

---

## 12. Advanced Integrations

### 1. Cairo Custom Drawing
Essential for custom charts like `CompressionRing`.
```python
import cairo

# 1. Enable Cairo Foreign Support
try:
    gi.require_foreign("cairo")
except ImportError:
    print("Warning: PyCairo not available")

# 2. In your Gtk.DrawingArea
def draw(self, area, cr, width, height, data):
    cr.set_source_rgba(1, 0, 0, 1)
    cr.arc(width/2, height/2, 50, 0, 2 * 3.14)
    cr.stroke()
```

### 2. Clipboard Handling (Async)
GTK4 uses asynchronous clipboard access.
```python
clipboard = Gdk.Display.get_default().get_clipboard()

# Writing
clipboard.set("Hello World")

# Reading
def on_read(clipboard, result):
    text = clipboard.read_text_finish(result)
    print(text)

clipboard.read_text_async(None, on_read)
```

### 3. Drag and Drop
Use `Gtk.DragSource` and `Gtk.DropTarget` controllers (not widget signals).
```python
# Source
source = Gtk.DragSource()
source.set_content(Gdk.ContentProvider.new_for_value("My Payload"))
widget.add_controller(source)

# Target
target = Gtk.DropTarget.new(GObject.TYPE_STRING, Gdk.DragAction.COPY)
target.connect("drop", on_drop)
widget.add_controller(target)
```

---

## 13. Debugging Tips

### GObject Debugging
Run your app with these flags to find leaks or issues:
```bash
GOBJECT_DEBUG=instance-count GTK_DEBUG=interactive ./main.py
```

### Profiling
To see why the UI is lagging:
```bash
python -m cProfile -s cumulative main.py > profile.log
# View with 'snakeviz' if installed
```

### Wayland/HiDPI Testing
Test how your app looks on 2x scaling:
```bash
GDK_SCALE=2 ./main.py
```
