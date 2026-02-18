#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Sync Clipboard GUI
Graphical interface implemented with CustomTkinter for managing sync-clipboard application
"""

import json
import os
import platform
import sys
import threading
from dataclasses import dataclass
from pathlib import Path

import click
import customtkinter as ctk
import pystray
from PIL import Image, ImageDraw
from platformdirs import user_config_path
from pystray import MenuItem

from src.core.exceptions import (
    ClipboardAccessError,
    ClipboardConnectionError,
    ConfigurationError,
    SyncClipboardError,
)
from src.core.logging_utils import get_logger
from src.sync_clipboard_cli import ClipboardSync, __version__


@dataclass
class Config:
    mode: str = 'client'
    host: str = '127.0.0.1'
    port: int = 8765
    hostname: str = ''
    minimize_on_close: bool = False

    def __post_init__(self):
        if not self.hostname:
            self.hostname = platform.node()


class SyncClipboardGUI:
    def __init__(self, config_path: str | Path | None = None):
        self.config_path = config_path if config_path else user_config_path() / 'config.json'
        # Set theme
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('blue')

        # Initialize logger
        self.logger = get_logger('gui')

        # Create main window
        self.root = ctk.CTk()
        self.root.title(f'Sync Clipboard - v{__version__}')
        width = 600
        height = 800
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

        # Set window icon
        self.icon_photo = None
        try:
            import tkinter as tk

            icon_path = self._get_icon_path()
            if icon_path.exists():
                self.icon_photo = tk.PhotoImage(file=str(icon_path))
                self.root.wm_iconphoto(False, self.icon_photo)
                self.logger.info(f'Successfully loaded window icon: {icon_path}')
        except Exception as e:
            self.logger.warning(f'Failed to load window icon: {e}')

        # Load configuration
        self.config = self.load_config()

        # Create threads
        self.sync_thread: threading.Thread | None = None
        self.sync_instance: ClipboardSync | None = None

        # Create system tray icon
        self.tray_icon = None
        self.create_tray_icon()

        # Create UI
        self.create_widgets()
        self.log_message(f'Current config path: {self.config_path}')

        # Initialize auto-save timer
        self.auto_save_timer = None

        # Bind window close event
        self.root.protocol('WM_DELETE_WINDOW', self.on_closing)

    def create_widgets(self):
        """Create UI widgets"""
        # Top configuration area
        config_frame = ctk.CTkFrame(self.root)
        config_frame.pack(pady=10, padx=20, fill='x')

        # Mode selection
        mode_frame = ctk.CTkFrame(config_frame)
        mode_frame.pack(pady=5, padx=20, fill='x')

        mode_label = ctk.CTkLabel(mode_frame, text='Run Mode:')
        mode_label.pack(pady=5, anchor='w', padx=10)

        self.mode_var = ctk.StringVar(value=self.config.mode)
        # Add auto-save callback
        self.mode_var.trace_add('write', self.on_config_change)

        mode_server_radio = ctk.CTkRadioButton(
            mode_frame, text='Server', variable=self.mode_var, value='server'
        )
        mode_client_radio = ctk.CTkRadioButton(
            mode_frame, text='Client', variable=self.mode_var, value='client'
        )

        mode_server_radio.pack(pady=2, anchor='w', padx=30)
        mode_client_radio.pack(pady=2, anchor='w', padx=30)

        # Host configuration
        host_frame = ctk.CTkFrame(config_frame)
        host_frame.pack(pady=5, padx=20, fill='x')

        host_label = ctk.CTkLabel(host_frame, text='Host Address:')
        host_label.pack(pady=5, anchor='w', padx=10)

        self.host_entry = ctk.CTkEntry(host_frame, placeholder_text='Enter host address')
        self.host_entry.insert(0, self.config.host)
        # Add auto-save callback
        self.host_entry.bind('<FocusOut>', self.on_config_change)
        self.host_entry.bind('<KeyRelease>', self.on_config_change_delayed)
        self.host_entry.pack(pady=5, padx=20, fill='x')

        # Port configuration
        port_frame = ctk.CTkFrame(config_frame)
        port_frame.pack(pady=5, padx=20, fill='x')

        port_label = ctk.CTkLabel(port_frame, text='Port:')
        port_label.pack(pady=5, anchor='w', padx=10)

        self.port_entry = ctk.CTkEntry(port_frame, placeholder_text='Enter port number')
        self.port_entry.insert(0, str(self.config.port))
        # Add auto-save callback and validation
        self.port_entry.bind('<FocusOut>', self.on_config_change)
        self.port_entry.bind('<KeyRelease>', self.on_config_change_delayed)
        self.port_entry.pack(pady=5, padx=20, fill='x')

        # Hostname configuration
        hostname_frame = ctk.CTkFrame(config_frame)
        hostname_frame.pack(pady=5, padx=20, fill='x')

        hostname_label = ctk.CTkLabel(hostname_frame, text='Hostname:')
        hostname_label.pack(pady=5, anchor='w', padx=10)

        self.hostname_entry = ctk.CTkEntry(hostname_frame, placeholder_text='Enter hostname')
        self.hostname_entry.insert(0, self.config.hostname)
        # Add auto-save callback
        self.hostname_entry.bind('<FocusOut>', self.on_config_change)
        self.hostname_entry.bind('<KeyRelease>', self.on_config_change_delayed)
        self.hostname_entry.pack(pady=5, padx=20, fill='x')

        # Button area
        button_frame = ctk.CTkFrame(self.root)
        button_frame.pack(pady=10, padx=20, fill='x')

        self.start_button = ctk.CTkButton(
            button_frame,
            text='Start',
            command=self.on_start_btn_click,
            fg_color='green',
            hover_color='darkgreen',
        )
        self.start_button.pack(side='left', pady=10, padx=5)

        self.stop_button = ctk.CTkButton(
            button_frame,
            text='Stop',
            command=self.on_stop_btn_click,
            fg_color='orange',
            hover_color='darkorange',
        )
        self.stop_button.pack(side='left', pady=10, padx=5)

        self.exit_button = ctk.CTkButton(
            button_frame,
            text='Exit',
            command=self.exit_app,
            fg_color='red',
            hover_color='darkred',
        )
        self.exit_button.pack(side='left', pady=10, padx=5)

        # Save config button
        save_config_button = ctk.CTkButton(
            button_frame,
            text='Save Config',
            command=self.save_config,
            fg_color='gray',
            hover_color='darkgray',
        )
        save_config_button.pack(side='right', pady=10, padx=5)

        # Log area
        log_frame = ctk.CTkFrame(self.root)
        log_frame.pack(pady=10, padx=20, fill='both', expand=True)

        log_label = ctk.CTkLabel(
            log_frame, text='Runtime Logs:', font=ctk.CTkFont(size=14, weight='bold')
        )
        log_label.pack(pady=5, anchor='w', padx=10)

        # Create text box and scrollbar
        self.log_text = ctk.CTkTextbox(log_frame, height=200)
        self.log_text.pack(pady=5, padx=10, fill='both', expand=True)

    def _get_icon_path(self) -> Path:
        """Get icon file path (supports both development and packaged environments)"""
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller packaged environment
            return Path(sys._MEIPASS) / 'assets' / 'sync-clipboard-256.png'
        else:
            # Development environment
            return Path(__file__).parent.parent / 'assets' / 'sync-clipboard-256.png'

    def create_tray_icon(self):
        """Create system tray icon"""
        try:
            # Load icon file
            icon_path = self._get_icon_path()
            if icon_path.exists():
                image = Image.open(icon_path)
                self.logger.info(f'Successfully loaded tray icon: {icon_path}')
            else:
                # If icon file doesn't exist, use default icon
                self.logger.warning(f'Icon file not found: {icon_path}, using default icon')
                image = Image.new('RGB', (64, 64), color=(73, 109, 137))
                dc = ImageDraw.Draw(image)
                dc.ellipse((10, 10, 54, 54), fill=(255, 255, 255))
        except Exception as e:
            self.logger.error(f'Failed to load icon: {e}, using default icon')
            image = Image.new('RGB', (64, 64), color=(73, 109, 137))
            dc = ImageDraw.Draw(image)
            dc.ellipse((10, 10, 54, 54), fill=(255, 255, 255))

        # Create tray menu
        menu = (
            MenuItem('Show Window', self.show_window, default=True),
            MenuItem('Exit', self.exit_app),
        )

        # Create tray icon
        self.tray_icon = pystray.Icon(
            'sync_clipboard', image, 'Sync Clipboard', menu, action=self.show_window
        )

        # Run tray icon in separate thread
        tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        tray_thread.start()

    def load_config(self) -> Config:
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)

                    # Validate and clean configuration data
                    mode = config_data.get('mode', 'client')
                    if mode not in ['server', 'client']:
                        print(f"Invalid mode '{mode}', using default value 'client'")
                        mode = 'client'

                    # Validate port number
                    port = config_data.get('port', 8765)
                    try:
                        port = int(port)
                        if not (1 <= port <= 65535):
                            print(f'Invalid port number {port}, using default value 8765')
                            port = 8765
                    except (ValueError, TypeError):
                        print('Invalid port number format, using default value 8765')
                        port = 8765

                    # Validate host address
                    host = config_data.get('host', '127.0.0.1')
                    if not host or not isinstance(host, str):
                        host = '127.0.0.1'

                    # Validate hostname
                    hostname = config_data.get('hostname', platform.node())
                    if not hostname or not isinstance(hostname, str):
                        hostname = platform.node()

                    return Config(
                        mode=mode,
                        host=host,
                        port=port,
                        hostname=hostname,
                        minimize_on_close=config_data.get('minimize_on_close', False),
                    )
            else:
                # If config file doesn't exist, return default config and create file
                default_config = Config()
                print('Config file not found, using default configuration')
                # Auto-save default configuration
                self._save_config_to_file_silent(default_config)
                return default_config
        except Exception as e:
            self.logger.error(f'Failed to load configuration: {e}, using default configuration')
            default_config = Config()
            # Try to save default configuration
            try:
                self._save_config_to_file_silent(default_config)
            except Exception as save_error:
                self.logger.warning(f'Failed to save default configuration: {save_error}')
            return default_config

    def _save_config_to_file_silent(self, config: Config) -> bool:
        """Silently save configuration to file (no logging output)"""
        try:
            config_data = {
                'mode': config.mode,
                'host': config.host,
                'port': config.port,
                'hostname': config.hostname,
                'minimize_on_close': config.minimize_on_close,
            }

            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            self.log_message(str(e))
            self.logger.error(str(e))
            return False

    def save_config(self):
        """Save configuration to file"""
        try:
            # Validate input
            mode = self.mode_var.get()
            if mode not in ['server', 'client']:
                error_msg = f'Invalid mode: {mode}'
                self.log_message(error_msg)
                self.logger.error(error_msg)
                return False

            host = self.host_entry.get().strip()
            if not host:
                error_msg = 'Host address cannot be empty'
                self.log_message(error_msg)
                self.logger.error(error_msg)
                return False

            try:
                port = int(self.port_entry.get())
                if not (1 <= port <= 65535):
                    error_msg = 'Port must be between 1-65535'
                    self.log_message(error_msg)
                    self.logger.error(error_msg)
                    return False
            except ValueError:
                error_msg = 'Port must be a number'
                self.log_message(error_msg)
                self.logger.error(error_msg)
                return False

            hostname = self.hostname_entry.get().strip()
            if not hostname:
                hostname = platform.node()
                self.hostname_entry.delete(0, 'end')
                self.hostname_entry.insert(0, hostname)
                self.logger.info(f'Using default hostname: {hostname}')

            # Update configuration object
            self.config.mode = mode
            self.config.host = host
            self.config.port = port
            self.config.hostname = hostname

            # Save to file
            return self._save_config_to_file(self.config)

        except ConfigurationError as e:
            error_msg = f'Configuration error: {e}'
            self.log_message(error_msg)
            self.logger.error(error_msg)
            return False
        except Exception as e:
            error_msg = f'Unknown error while saving configuration: {e}'
            self.log_message(error_msg)
            self.logger.error(error_msg, exc_info=True)
            return False

    def _save_config_to_file(self, config: Config) -> bool:
        """Internal method: save configuration to file"""
        try:
            config_data = {
                'mode': config.mode,
                'host': config.host,
                'port': config.port,
                'hostname': config.hostname,
                'minimize_on_close': config.minimize_on_close,
            }

            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            self.log_message('Configuration saved')
            self.logger.info('Configuration successfully saved to file')
            return True
        except OSError as e:
            error_msg = f'File operation failed: {e}'
            self.log_message(error_msg)
            self.logger.error(error_msg)
            return False
        except Exception as e:
            error_msg = f'Failed to save configuration: {e}'
            self.log_message(error_msg)
            self.logger.error(error_msg, exc_info=True)
            return False

    def on_config_change(self, *args):
        """Callback when configuration changes (triggered immediately)"""
        # Cancel previous timer
        if self.auto_save_timer:
            self.root.after_cancel(self.auto_save_timer)

        # Save configuration immediately
        self.save_config()

    def on_config_change_delayed(self, *args):
        """Delayed callback when configuration changes (for keyboard input)"""
        # Cancel previous timer
        if self.auto_save_timer:
            self.root.after_cancel(self.auto_save_timer)

        # Set delayed save (after 1 second)
        self.auto_save_timer = self.root.after(1000, self.save_config)

    def on_start_btn_click(self):
        """Start synchronization"""
        try:
            # Save and validate configuration
            if not self.save_config():
                return  # Configuration validation failed, do not start

            # If already running, stop first
            if self.sync_instance and self.sync_instance.running:
                self.on_stop_btn_click()

            # Create new synchronization instance
            self.sync_instance = ClipboardSync(
                host=self.config.host,
                port=self.config.port,
                mode=self.config.mode,
                hostname=self.config.hostname,
                log_callback=self.log_message,
            )

            # Start synchronization in new thread
            def run_sync():
                try:
                    self.sync_instance.start_sync()
                except ClipboardConnectionError as e:
                    self.log_message(f'Connection error: {e}')
                    self.logger.error(f'Connection error: {e}')
                except ClipboardAccessError as e:
                    self.log_message(f'Clipboard access error: {e}')
                    self.logger.warning(f'Clipboard access error: {e}')
                except SyncClipboardError as e:
                    self.log_message(f'Synchronization error: {e}')
                    self.logger.error(f'Synchronization error: {e}')
                except Exception as e:
                    self.log_message(f'Unknown error in sync service: {e}')
                    self.logger.error(f'Unknown error in sync service: {e}', exc_info=True)

            self.sync_thread = threading.Thread(target=run_sync, daemon=True)
            self.sync_thread.start()

            self.log_message(
                f'Sync service started, mode: {self.config.mode}, address: {self.config.host}:{self.config.port}'
            )
            self.logger.info(
                f'Sync service started: {self.config.mode} mode, {self.config.host}:{self.config.port}'
            )

        except Exception as e:
            error_msg = f'Failed to start sync service: {e}'
            self.log_message(error_msg)
            self.logger.error(error_msg, exc_info=True)

    def on_stop_btn_click(self):
        """Stop synchronization"""
        try:
            if self.sync_instance:
                self.sync_instance.stop_sync()
                self.log_message('Sync service stopped')
                self.logger.info('Sync service stopped')
            else:
                self.log_message('No running sync service')
                self.logger.warning('Attempted to stop sync service, but none is running')
        except Exception as e:
            error_msg = f'Error occurred while stopping sync service: {e}'
            self.log_message(error_msg)
            self.logger.error(error_msg, exc_info=True)

    def exit_app(self):
        """Exit application"""
        try:
            # Save final configuration
            self.save_config()

            if self.sync_instance:
                self.sync_instance.stop_sync()
                self.logger.info('Sync service stopped, preparing to exit application')

            self.tray_icon.stop()
            self.root.quit()
            self.root.destroy()
            self.logger.info('Application exited')
            sys.exit()
        except Exception as e:
            self.logger.error(f'Error occurred while exiting application: {e}', exc_info=True)
            # Force exit
            sys.exit(1)

    def log_message(self, message: str):
        """Add message to log area"""
        formatted_message = f'{message}\n'
        self.log_text.insert('end', formatted_message)
        self.log_text.see('end')  # Scroll to latest message
        self.root.update_idletasks()  # Update UI immediately

    def minimize_to_tray(self):
        """Minimize to system tray"""
        self.root.withdraw()  # Hide main window

    def show_window(self, icon, item):
        """Show main window"""
        self.root.deiconify()  # Show main window
        self.root.lift()  # Bring window to front
        self.root.focus_force()  # Force focus

    def on_closing(self):
        """Window close event handler"""
        # If user set to not ask again, directly minimize to tray
        if self.config.minimize_on_close:
            self.minimize_to_tray()
            return

        # Create custom dialog with "don't show again" option
        dialog = ctk.CTkToplevel(self.root)
        dialog.title('Exit Confirmation')
        dialog.geometry('350x150')
        dialog.resizable(False, False)

        # Center dialog
        dialog.transient(self.root)
        dialog.grab_set()

        # Set dialog content
        label = ctk.CTkLabel(
            dialog, text="Do you want to minimize to tray instead of exiting?\nSelect 'No' to completely exit"
        )
        label.pack(pady=15)

        # Add "don't show again" checkbox
        dont_show_var = ctk.BooleanVar(value=False)
        checkbox = ctk.CTkCheckBox(dialog, text='Do not show this again', variable=dont_show_var)
        checkbox.pack(pady=5)

        # Button frame
        button_frame = ctk.CTkFrame(dialog)
        button_frame.pack(pady=10)

        def on_yes():
            # Save "don't show again" setting
            self.config.minimize_on_close = dont_show_var.get()
            self.save_config()
            self.minimize_to_tray()
            dialog.destroy()

        def on_no():
            # Save "don't show again" setting
            self.config.minimize_on_close = dont_show_var.get()
            self.save_config()
            self.exit_app()
            dialog.destroy()

        # Buttons
        yes_button = ctk.CTkButton(
            button_frame, text='Yes', command=on_yes, fg_color='green', hover_color='darkgreen'
        )
        yes_button.pack(side='left', padx=5)

        no_button = ctk.CTkButton(
            button_frame, text='No', command=on_no, fg_color='red', hover_color='darkred'
        )
        no_button.pack(side='left', padx=5)

    def run(self):
        """Run GUI application"""
        self.root.mainloop()


@click.command()
@click.option(
    '--config',
    '-c',
    type=click.Path(exists=False, dir_okay=False, path_type=Path),
    help='Specify the configuration file path',
)
@click.version_option(
    __version__, '--version', '-v', message='SyncClipboard GUI %(version)s - Cross-device clipboard sync tool'
)
def main(config):
    """
    SyncClipboard GUI - Graphical interface for cross-device clipboard synchronization

    Provides an intuitive GUI for managing clipboard sync service, supporting both server and client modes.

    \b
    Examples:
      Use default config: sync-clipboard-gui
      Specify config file: sync-clipboard-gui --config "D:\\config\\my_config.json"
    """
    app = SyncClipboardGUI(config_path=config)
    app.run()


if __name__ == '__main__':
    main()
