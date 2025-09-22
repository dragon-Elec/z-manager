ray@ray-X450CA:~/Desktop/Link to z-manager$ ./z-manager.py 

(z-manager.py:18249): Gtk-CRITICAL **: 09:09:51.504: gtk_list_box_row_grab_focus: assertion 'box != NULL' failed

(z-manager.py:18249): Gtk-CRITICAL **: 09:09:51.504: gtk_list_box_row_grab_focus: assertion 'box != NULL' failed



✦ I've corrected the syntax error; it seems to have been a copy-paste mistake.

  Now, back to our plan. The next logical step is to re-enable the data population methods (_populate_zram_devices and _populate_swap_list) that were
  temporarily disabled in the refresh method.

  Shall I do that?

╭──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│  > even if that is the error still seems to be present.                                                              │
│                                                                                                                      │
│    ray@ray-X450CA:~/Desktop/pending/z-manager/3/z-manager$ ./z-manager.py                                            │
│                                                                                                                      │
│    (z-manager.py:31207): Gtk-CRITICAL **: 10:43:39.380: gtk_list_box_row_grab_focus: assertion 'box != NULL' failed  │
│                                                                                                                      │
│    (z-manager.py:31207): Gtk-CRITICAL **: 10:43:39.380: gtk_list_box_row_grab_focus: assertion 'box != NULL' failed  │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

✦ It seems we've fixed the most obvious causes, but the error persists. This suggests the issue is more subtle.

  To isolate the problem, could you please try running the application after commenting out the call to self._populate_event_log() inside the refresh
  method?

  If the error disappears, we'll know for sure the problem is within the _populate_event_log method, even though it seems to use a safe loop. If the
  error remains, it means it's coming from somewhere else entirely.

  I can make this change for you if you'd like.

╭──────────────────────────────────────────────────────────────────────╮
│  > make the change and run the application it will run wihtout sudo  │
╰──────────────────────────────────────────────────────────────────────╯

✦ Okay, I will comment out the line and run the application to see if the error persists.
 ╭───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
 │ ✓  Edit ui/status_page.py:         self._populate_event_l... =>         # self._populate_event...                                             │
 │                                                                                                                                               │
 │    75   # --- TEMPORARILY DISABLED TO GET THE UI RUNNING ---                                                                                  │
 │    76   # self._populate_zram_devices()                                                                                                       │
 │    77   # self._populate_swap_list()                                                                                                          │
 │    78 - self._populate_event_log()                                                                                                            │
 │    78 + # self._populate_event_log()                                                                                                          │
 │    79                                                                                                                                         │
 │    80   if not zdevice_ctl.list_devices():                                                                                                    │
 │    81       self.no_devices_status_page.set_visible(True)                                                                                     │
 ╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
✦ I've commented out the line. Now, running the application to check for the error.
 ╭────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
 │ ✓  Shell ./z-manager.py (Run the z-manager application to check if the Gtk-CRITICAL error still occurs after commenting out a function call.)  │
 ╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
✦ Okay, the application ran without errors after commenting out _populate_event_log. This confirms the problem is inside that function.

  I have a new theory. The other parts of your UI add Adw.ActionRow widgets to an Adw.PreferencesGroup (which acts like a list). However,
  _populate_event_log adds Adw.ActionRow widgets to a Gtk.Box.

  Adw.ActionRow is a special list-item widget. Using it outside of a list container can confuse GTK's focus management, which is likely the cause of
  the crash, even with the safe removal loop.

  The most consistent fix would be to refactor the UI to use an Adw.PreferencesGroup for the event log, just like for swaps and devices. However, this
  is a bit more involved as it requires changing the UI file.

  A simpler, immediate fix is to use a more standard widget instead of Adw.ActionRow for the log entries. For example, we can use a Gtk.Label inside a
  Gtk.Box with an icon. This would avoid the list-related focus problem entirely.

  Would you like me to try this simpler fix first?
