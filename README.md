# Z-Manager

## A Modern GTK4 / Libadwaita GUI for Managing ZRAM on Linux.

[![License: GPL v2](https://img.shields.io/badge/License-GPL%20v2-blue.svg)](https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html)

> **⚠️ Alpha Software**
>
> This application is in early development. You may encounter bugs, incomplete features, or unexpected behavior. Please test on a non-critical system and [report any issues](https://github.com/dragon-Elec/z-manager/issues) you find.

<div align="center">
  <h3>📊 Main Dashboard</h3>
  <img src="./images/status_tab.png" alt="Status Dashboard" width="600"/>
  <p><i>Monitor active ZRAM devices and system swap priority in real-time.</i></p>
</div>

<hr/>

### 🚀 Performance & Memory
| **Hibernate Management** | **System Tuning** |
|:---:|:---:|
| <img src="./images/hibernate_tab.png" alt="Hibernate" width="380"/> | <img src="./images/tune_tab.png" alt="Tune" width="380"/> |
| *Manage persistent storage for kernel resumption.* | *Real-time tuning of kernel parameters and PSI monitoring.* |

### ⚙️ Expert Configuration
| **Presets & Profiles** | **Advanced Settings** |
|:---:|:---:|
| <img src="./images/configure_tab_profiles.png" alt="Profiles" width="380"/> | <img src="./images/configure_tab_settings.png" alt="Settings" width="380"/> |
| *Fast, one-click optimization for gaming or servers.* | *Fine-grained control over the ZRAM generator parameters.* |

### 🛠️ Diagnostics & Logs
| **System Health** | **Journal Insight** |
|:---:|:---:|
| <img src="./images/health_report_details.png" alt="Health" width="380"/> | <img src="./images/system_logs_view.png" alt="Logs" width="380"/> |
| *Deep-dive into your system's swap health status.* | *Integrated viewer for ZRAM-specific systemd logs.* |

<br/>

## About The Project

Z-Manager is a user-friendly desktop application designed to simplify the configuration and monitoring of ZRAM on modern Linux systems. It acts as a graphical frontend for `zram-generator` and the underlying kernel subsystem, providing a clean interface for tasks that traditionally require the command line.

This tool is for desktop users and system tweakers who want to harness the performance benefits of ZRAM without the command-line hassle.

## Features

* **Easy Configuration:** Configure ZRAM size, compression algorithm, and swap priority through a simple interface.
* **Advanced Settings:** Manage advanced `zram-generator` options like writeback devices, filesystem mode, and host memory limits.
* **Configuration Profiles:** Use built-in profiles (e.g., "Desktop / Gaming") for quick and optimized setups.
* **Live Monitoring:** View real-time statistics for active ZRAM devices, including usage, compression ratio, and memory statistics.
* **System Health:** Get a clear overview of your entire system's swap configuration and diagnose potential conflicts (like an active ZSwap).
* **System Tuning:** Adjust related kernel parameters like CPU governors and I/O schedulers to further optimize performance.
* **Log Viewer:** Easily view ZRAM-related logs from the systemd journal to troubleshoot issues.

## Requirements

* Python 3.11+
* GTK 4
* libadwaita 1.x
* `systemd` with `zram-generator`
* `psutil`

## Project Structure

```
z-manager/
├── core/                    # Backend logic
│   ├── device_management/   # Modular device orchestration
│   │   ├── prober.py        #   Device discovery & status queries
│   │   ├── configurator.py  #   Apply/remove device & global config
│   │   ├── provisioner.py   #   Device creation & sysfs management
│   │   └── types.py         #   Shared dataclasses (DeviceInfo, etc.)
│   ├── boot_config.py       # GRUB / bootloader kernel param management
│   ├── config.py            # zram-generator INI config reader
│   ├── config_writer.py     # zram-generator INI config writer
│   ├── health.py            # System health diagnostics
│   ├── hibernate_ctl.py     # Hibernation / resume management
│   └── os_utils.py          # Low-level sysfs & subprocess helpers
├── modules/                 # Auxiliary services
│   ├── monitoring.py        # Real-time polling engine
│   └── journal.py           # Systemd journal log reader
├── ui/                      # GTK4 / Libadwaita frontend
│   ├── status_page.py       # Main dashboard
│   ├── configure_page.py    # Configuration UI
│   ├── configure_logic.py   # Configuration business logic
│   ├── live_orchestrator.py # Live-apply orchestration
│   ├── log_viewer.py        # Log viewer dialog
│   └── custom_widgets/      # Reusable widgets (CircularWidget, etc.)
└── tests/                   # Test suite
    ├── test_base.py          # Shared base class & assertions
    ├── unit/                 # Unit tests
    └── integration/          # Integration tests
```

## Installation

Installation instructions will be provided once the application reaches a more stable release.

## Contributing

Contributions are welcome and greatly appreciated! This project is developed by an individual, and community involvement can help make it better.

If you are interested in contributing, please feel free to:
* **Open an Issue:** Report bugs, suggest new features, or ask questions.
* **Submit a Pull Request:** If you'd like to contribute code, please open an issue first to discuss the proposed changes.

You can find the issue tracker on the project's GitHub page:
[https://github.com/dragon-Elec/z-manager/issues](https://github.com/dragon-Elec/z-manager/issues)

## License

This project is licensed under the **GNU General Public License v2.0**. See the `LICENSE` file for the full license text.
