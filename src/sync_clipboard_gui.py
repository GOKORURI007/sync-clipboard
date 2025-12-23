#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Sync Clipboard GUI
使用 CustomTkinter 实现的图形界面，用于管理 sync-clipboard 应用
"""
import json
import os
import platform
import sys
import threading
from dataclasses import dataclass
from tkinter import messagebox

import customtkinter as ctk
import pystray
from PIL import Image, ImageDraw
from pystray import MenuItem

from sync_clipboard import __version__, ClipboardSync


@dataclass
class Config:
    mode: str = "client"
    host: str = "127.0.0.1"
    port: int = 8765
    hostname: str = ""
    minimize_on_close: bool = False

    def __post_init__(self):
        if not self.hostname:
            self.hostname = platform.node()


class SyncClipboardGUI:
    def __init__(self):
        # 设置主题
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # 创建主窗口
        self.root = ctk.CTk()
        self.root.title(f"Sync Clipboard - v{__version__}")
        width = 600
        height = 800
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

        # 读取配置
        self.config = self.load_config()

        # 创建线程
        self.sync_thread: threading.Thread | None = None
        self.sync_instance: ClipboardSync | None = None

        # 创建系统托盘图标
        self.tray_icon = None
        self.create_tray_icon()

        # 创建界面
        self.create_widgets()

        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        """创建界面组件"""
        # 顶部配置区域
        config_frame = ctk.CTkFrame(self.root)
        config_frame.pack(pady=10, padx=20, fill="x")

        # Mode 选择
        mode_frame = ctk.CTkFrame(config_frame)
        mode_frame.pack(pady=5, padx=20, fill="x")

        mode_label = ctk.CTkLabel(mode_frame, text="运行模式:")
        mode_label.pack(pady=5, anchor="w", padx=10)

        self.mode_var = ctk.StringVar(value=self.config.mode)
        mode_server_radio = ctk.CTkRadioButton(mode_frame, text="服务器 (server)",
                                               variable=self.mode_var, value="server")
        mode_client_radio = ctk.CTkRadioButton(mode_frame, text="客户端 (client)",
                                               variable=self.mode_var, value="client")
        mode_mix_radio = ctk.CTkRadioButton(mode_frame, text="混合 (mix)",
                                            variable=self.mode_var, value="mix")

        mode_server_radio.pack(pady=2, anchor="w", padx=30)
        mode_client_radio.pack(pady=2, anchor="w", padx=30)
        mode_mix_radio.pack(pady=2, anchor="w", padx=30)

        # Host 配置
        host_frame = ctk.CTkFrame(config_frame)
        host_frame.pack(pady=5, padx=20, fill="x")

        host_label = ctk.CTkLabel(host_frame, text="主机地址:")
        host_label.pack(pady=5, anchor="w", padx=10)

        self.host_entry = ctk.CTkEntry(host_frame, placeholder_text="输入主机地址")
        self.host_entry.insert(0, self.config.host)
        self.host_entry.pack(pady=5, padx=20, fill="x")

        # Port 配置
        port_frame = ctk.CTkFrame(config_frame)
        port_frame.pack(pady=5, padx=20, fill="x")

        port_label = ctk.CTkLabel(port_frame, text="端口号:")
        port_label.pack(pady=5, anchor="w", padx=10)

        self.port_entry = ctk.CTkEntry(port_frame, placeholder_text="输入端口号")
        self.port_entry.insert(0, str(self.config.port))
        self.port_entry.pack(pady=5, padx=20, fill="x")

        # Hostname 配置
        hostname_frame = ctk.CTkFrame(config_frame)
        hostname_frame.pack(pady=5, padx=20, fill="x")

        hostname_label = ctk.CTkLabel(hostname_frame, text="主机名:")
        hostname_label.pack(pady=5, anchor="w", padx=10)

        self.hostname_entry = ctk.CTkEntry(hostname_frame, placeholder_text="输入主机名")
        self.hostname_entry.insert(0, self.config.hostname)
        self.hostname_entry.pack(pady=5, padx=20, fill="x")

        # 按钮区域
        button_frame = ctk.CTkFrame(self.root)
        button_frame.pack(pady=10, padx=20, fill="x")

        self.start_button = ctk.CTkButton(button_frame, text="开始运行",
                                          command=self.on_start_btn_click,
                                          fg_color="green", hover_color="darkgreen")
        self.start_button.pack(side="left", pady=10, padx=5)

        self.stop_button = ctk.CTkButton(button_frame, text="停止运行",
                                         command=self.on_stop_btn_click,
                                         fg_color="orange", hover_color="darkorange")
        self.stop_button.pack(side="left", pady=10, padx=5)

        self.exit_button = ctk.CTkButton(button_frame, text="完全退出",
                                         command=self.exit_app,
                                         fg_color="red", hover_color="darkred")
        self.exit_button.pack(side="left", pady=10, padx=5)

        # 保存配置按钮
        save_config_button = ctk.CTkButton(button_frame, text="保存配置",
                                           command=self.save_config,
                                           fg_color="gray", hover_color="darkgray")
        save_config_button.pack(side="right", pady=10, padx=5)

        # 日志区域
        log_frame = ctk.CTkFrame(self.root)
        log_frame.pack(pady=10, padx=20, fill="both", expand=True)

        log_label = ctk.CTkLabel(log_frame, text="运行日志:",
                                 font=ctk.CTkFont(size=14, weight="bold"))
        log_label.pack(pady=5, anchor="w", padx=10)

        # 创建文本框和滚动条
        self.log_text = ctk.CTkTextbox(log_frame, height=200)
        self.log_text.pack(pady=5, padx=10, fill="both", expand=True)

    def create_tray_icon(self):
        """创建系统托盘图标"""
        # 创建一个简单的图标
        image = Image.new('RGB', (64, 64), color=(73, 109, 137))
        dc = ImageDraw.Draw(image)
        dc.ellipse((10, 10, 54, 54), fill=(255, 255, 255))

        # 创建托盘菜单
        menu = (MenuItem('打开主界面', self.show_window, default=True),
                MenuItem('退出程序', self.exit_app))

        # 创建托盘图标
        self.tray_icon = pystray.Icon("sync_clipboard", image, "Sync Clipboard", menu,
                                      action=self.show_window)

        # 在单独的线程中运行托盘图标
        tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        tray_thread.start()

    def load_config(self) -> Config:
        """从配置文件加载配置"""
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    return Config(
                        mode=config_data.get('mode', 'client'),
                        host=config_data.get('host', '127.0.0.1'),
                        port=config_data.get('port', 8765),
                        hostname=config_data.get('hostname', platform.node()),
                        minimize_on_close=config_data.get('minimize_on_close', False)
                    )
            else:
                # 如果配置文件不存在，返回默认配置
                return Config()
        except Exception as e:
            print(f"加载配置失败: {e}")
            return Config()

    def save_config(self):
        """保存配置到文件"""
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        try:
            config_data = {
                'mode': self.mode_var.get(),
                'host': self.host_entry.get(),
                'port': int(self.port_entry.get()),
                'hostname': self.hostname_entry.get(),
                'minimize_on_close': self.config.minimize_on_close
            }

            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            self.log_message("配置已保存")
        except Exception as e:
            self.log_message(f"保存配置失败: {e}")

    def on_start_btn_click(self):
        """开始同步"""
        # 更新配置
        try:
            self.config.mode = self.mode_var.get()
            self.config.host = self.host_entry.get()
            self.config.port = int(self.port_entry.get())
            self.config.hostname = self.hostname_entry.get()
        except ValueError:
            messagebox.showerror("错误", "端口号必须是数字！")
            return

        # 保存配置
        self.save_config()

        # 如果已经在运行，则先停止
        if self.sync_instance and self.sync_instance.running:
            self.on_stop_btn_click()

        # 创建新的同步实例
        self.sync_instance = ClipboardSync(
            host=self.config.host,
            port=self.config.port,
            mode=self.config.mode,
            hostname=self.config.hostname,
            log_callback=self.log_message
        )

        # 在新线程中启动同步
        def run_sync():
            self.sync_instance.start_sync()

        self.sync_thread = threading.Thread(target=run_sync, daemon=True)
        self.sync_thread.start()

        self.log_message(
            f"已启动同步服务，模式: {self.config.mode}, 地址: {self.config.host}:{self.config.port}")

    def on_stop_btn_click(self):
        """停止同步"""
        if self.sync_instance:
            self.sync_instance.stop_sync()
            self.log_message("同步服务已停止")
        else:
            self.log_message("没有运行中的同步服务")

    def exit_app(self):
        """退出应用程序"""
        if self.sync_instance:
            self.sync_instance.stop_sync()
        self.tray_icon.stop()
        self.root.quit()
        self.root.destroy()
        sys.exit()

    def log_message(self, message: str):
        """在日志区域添加消息"""
        formatted_message = f"[{ctk.get_appearance_mode()}] {message}\n"
        self.log_text.insert("end", formatted_message)
        self.log_text.see("end")  # 滚动到最新消息
        self.root.update_idletasks()  # 立即更新界面

    def minimize_to_tray(self):
        """最小化到托盘"""
        self.root.withdraw()  # 隐藏主窗口

    def show_window(self, icon, item):
        """显示主窗口"""
        self.root.deiconify()  # 显示主窗口
        self.root.lift()  # 将窗口置于最前
        self.root.focus_force()  # 强制获得焦点

    def on_closing(self):
        """窗口关闭事件处理"""
        # 如果用户设置了不再询问，则直接最小化到托盘
        if self.config.minimize_on_close:
            self.minimize_to_tray()
            return

        # 创建一个带"不再显示"选项的自定义对话框
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("退出确认")
        dialog.geometry("350x150")
        dialog.resizable(False, False)

        # 居中显示对话框
        dialog.transient(self.root)
        dialog.grab_set()

        # 设置对话框内容
        label = ctk.CTkLabel(dialog,
                             text="是否要最小化到托盘而不是退出程序？\n选择'否'将完全退出程序")
        label.pack(pady=15)

        # 添加"不再显示"复选框
        dont_show_var = ctk.BooleanVar(value=False)
        checkbox = ctk.CTkCheckBox(dialog, text="不再显示此提示", variable=dont_show_var)
        checkbox.pack(pady=5)

        # 按钮框架
        button_frame = ctk.CTkFrame(dialog)
        button_frame.pack(pady=10)

        def on_yes():
            # 保存"不再显示"的设置
            self.config.minimize_on_close = dont_show_var.get()
            self.save_config()
            self.minimize_to_tray()
            dialog.destroy()

        def on_no():
            # 保存"不再显示"的设置
            self.config.minimize_on_close = dont_show_var.get()
            self.save_config()
            self.exit_app()
            dialog.destroy()

        # 按钮
        yes_button = ctk.CTkButton(button_frame, text="是", command=on_yes,
                                   fg_color="green", hover_color="darkgreen")
        yes_button.pack(side="left", padx=5)

        no_button = ctk.CTkButton(button_frame, text="否", command=on_no,
                                  fg_color="red", hover_color="darkred")
        no_button.pack(side="left", padx=5)

    def run(self):
        """运行GUI应用"""
        self.root.mainloop()


def main():
    app = SyncClipboardGUI()
    app.run()


if __name__ == "__main__":
    main()
