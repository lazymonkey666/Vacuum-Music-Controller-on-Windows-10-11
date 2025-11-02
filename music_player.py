import os
import sys
import time
import threading
import pygame
import winreg
import re
import bisect
from PIL import Image, ImageFilter
import io
from PyQt5.QtWidgets import (QApplication, QLineEdit, QWidget, QCheckBox, 
                            QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, 
                            QLabel, QFileDialog, QMessageBox, QProgressBar, 
                            QGraphicsDropShadowEffect,)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QColor,QPixmap
import keyboard
from AcrylicEffect import WindowEffect  
from mutagen.id3 import ID3, USLT ,APIC

c=0

class MusicPlayer(QWidget):
    # 自定义信号，用于更新UI
    update_ui_signal = pyqtSignal(int, int)  # 当前时间(ms)，总时间(ms)
    progress_update_signal = pyqtSignal(int, int)

    def __init__(self):
        super().__init__()
        pygame.mixer.init()
        
        # 设置窗口透明相关属性
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        
        # 设置窗口位置和大小
        self.setGeometry(0, 0, 700, 230)
        
        self.init_ui()
        self.playlist = []
        self.current_index = 0
        self.is_playing = False
        self.music_long = 0  # 总时长(ms)
        self.quit_flag = 0
        self.show_flag = 1  # 初始化为显示状态
        
        # 主题相关属性
        self.bg_color = ""
        self.text_color = ""
        self.scroll_bg = ""
        self.scroll_handle = ""
        self.scroll_handle_hover = ""
        self.theme_color = ""
        self.theme_color2 = ""
        self.is_dark = False
        
        # 设置窗口效果
        self.windowEffect = WindowEffect()
        self.setAttribute(Qt.WA_NoSystemBackground)
        
        # 更新UI主题
        self.update_ui_theme()
        
        # 关键修复：连接UI更新信号到处理函数
        self.update_ui_signal.connect(self.update_ui_handler)
        
        self.load_music_playlist()
        self.start_music_thread()
        
        # 创建定时器线程，用于刷新UI

        self.refresh_timer=QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_ui)
        self.refresh_timer.start(500)  # 每500ms刷新一次

        
        self.hotkey_timer=QTimer(self)
        self.hotkey_timer.timeout.connect(self.hotkey)
        self.hotkey_timer.start(100)  # 每100ms检查一次热键
        
        # 初始化显示状态
        if self.show_flag:
            self.show()
        else:
            self.hide()
        self.raise_()
        self.activateWindow()
        self.start_progress_update()
        
        # 新增搜索窗口相关
        self.search_window = None
         
    def quit_musicplayer(self):
        self.quit_flag = 1
        pygame.mixer.music.stop()
        self.close()
        
    def init_ui(self):
        self.setWindowTitle("音乐播放器")
        
        _main_layout = QHBoxLayout(self)

        main_layout = QVBoxLayout(self)
        _main_layout.addLayout(main_layout)

        self.image_label=QLabel("",self)
        self.image_label.setFixedSize(230, 230)
        self.image_label.move(470,0)

        self.list_widget = QListWidget(self)
        self.list_widget.itemClicked.connect(self.play_selected_song)
        main_layout.addWidget(self.list_widget)

        button_layout = QHBoxLayout()

        self.play_button = QPushButton("播放", self)
        self.play_button.clicked.connect(self.toggle_play_pause)
        button_layout.addWidget(self.play_button)

        self.hide_show_button = QPushButton("隐藏/显示", self)
        self.hide_show_button.clicked.connect(self.hide_show_window)
        button_layout.addWidget(self.hide_show_button)

        self.move_button = QPushButton("滚动到当前播放", self)
        self.move_button.clicked.connect(self.to_now_playing)
        button_layout.addWidget(self.move_button)

        self.search_button = QPushButton("搜索", self)
        self.search_button.clicked.connect(self.search)
        button_layout.addWidget(self.search_button)

        main_layout.addLayout(button_layout)

        self.lyric_view = QListWidget(self)
        _main_layout.addWidget(self.lyric_view)
        
        progress_layout = QHBoxLayout()


        self.now_time_label = QLabel("00:00", self)
        self.now_time_label.setStyleSheet("color: white; font-weight: bold;")
        # 添加阴影效果
        shadow1 = QGraphicsDropShadowEffect()
        shadow1.setBlurRadius(10)
        shadow1.setXOffset(2)
        shadow1.setYOffset(2)
        shadow1.setColor(QColor(0, 0, 0, 180))
        self.now_time_label.setGraphicsEffect(shadow1)
        progress_layout.addWidget(self.now_time_label)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setFixedWidth(400)
        self.progress_bar.setTextVisible(False)
        # 允许进度条接收鼠标点击事件
        self.progress_bar.mousePressEvent = self.progress_bar_clicked
        progress_layout.addWidget(self.progress_bar)

        self.total_time_label = QLabel("00:00", self)
        self.total_time_label.setStyleSheet("color: white; font-weight: bold;")
        # 添加阴影效果
        shadow2 = QGraphicsDropShadowEffect()
        shadow2.setBlurRadius(10)
        shadow2.setXOffset(2)
        shadow2.setYOffset(2)
        shadow2.setColor(QColor(0, 0, 0, 180))
        self.total_time_label.setGraphicsEffect(shadow2)
        progress_layout.addWidget(self.total_time_label)

        main_layout.addLayout(progress_layout)

        self.setLayout(main_layout)

    def update_ui_theme(self):
        self.is_dark = self.is_darkmode()
        if self.is_dark:
            self.bg_color = "rgba(40, 40, 40, 100)"
            self.text_color = "rgba(255, 255, 255, 230)"
            self.scroll_bg = "rgba(40, 40, 40, 150)"
            self.scroll_handle = "rgba(100, 100, 100, 150)"
            self.scroll_handle_hover = "rgba(120, 120, 120, 180)"
            # 设置深色模式下的亚克力效果
            self.windowEffect.setAcrylicEffect(int(self.winId()), gradientColor="404040A0")
        else:
            self.bg_color = "rgba(255, 255, 255, 100)"
            self.text_color = "rgba(0, 0, 0, 230)"
            self.scroll_bg = "rgba(240, 240, 240, 100)"
            self.scroll_handle = "rgba(200, 200, 200, 150)"
            self.scroll_handle_hover = "rgba(180, 180, 180, 180)"
            # 设置浅色模式下的亚克力效果
            self.windowEffect.setAcrylicEffect(int(self.winId()), gradientColor="FFFFFFA0")
        
        # 获取 Windows 主题色
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Accent")
            accent_data = winreg.QueryValueEx(key, "AccentColorMenu")[0]
            # 转换为 RGB 格式
            r = max(0, min(255, accent_data & 0xFF))
            g = max(0, min(255, (accent_data >> 8) & 0xFF))
            b = max(0, min(255, (accent_data >> 16) & 0xFF))
            self.theme_color = f"rgba({r}, {g}, {b}, 150)"
            if self.is_dark:
                r2 = max(0, min(255, (accent_data & 0xFF) - 100))
                g2 = max(0, min(255, ((accent_data >> 8) & 0xFF) - 100))
                b2 = max(0, min(255, ((accent_data >> 16) & 0xFF) - 100))
                self.theme_color2 = f"rgba({r2}, {g2}, {b2}, 150)"
            else:
                r2 = max(0, min(255, (accent_data & 0xFF) + 100))
                g2 = max(0, min(255, ((accent_data >> 8) & 0xFF) + 100))
                b2 = max(0, min(255, ((accent_data >> 16) & 0xFF) + 100))
                self.theme_color2 = f"rgba({r2}, {g2}, {b2}, 150)"
        except:
            # 如果获取失败，使用默认蓝色
            self.theme_color = "rgba(100, 150, 255, 150)"
            self.theme_color2 = "rgba(120, 150, 255, 150)"
        
        # 全局字体样式
        base_style = f"""
            * {{
                font-family: "Microsoft YaHei", "微软雅黑";
            }}
        """
        
        # 列表样式
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {self.bg_color};
                color: {self.text_color};
                border: none;
                border-radius: 5px;
                font-family: "Microsoft YaHei", "微软雅黑";
                font-size: 12px;
            }}
            QListWidget::item:selected {{
                background-color: qlineargradient(x1:0, y1:0 , x2:1 ,y2:0 stop:0 {self.theme_color2} ,stop:1 {self.theme_color});
                color:{self.text_color};
                border: none;
                border-radius: 5px;
            }}
            QListWidget::item:hover {{
                background-color: rgba(80, 80, 80, 80);
            }}
        """)
        
        # 滚动条样式
        scroll_style = f"""
            QScrollBar:vertical {{
                background: {self.scroll_bg};
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {self.scroll_handle};
                min-height: 20px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {self.scroll_handle_hover};
            }}
            QScrollBar::add-line:vertical {{
                height: 0px;
            }}
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
            /* 水平滚动条 */
            QScrollBar:horizontal {{
                background: {self.scroll_bg};
                height: 8px;
                margin: 0px;
                border-radius: 4px;
            }}
            QScrollBar::handle:horizontal {{
                background: {self.scroll_handle};
                min-width: 20px;
                border-radius: 4px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {self.scroll_handle_hover};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: none;
            }}
        """
        self.list_widget.setStyleSheet(self.list_widget.styleSheet() + scroll_style)
        self.lyric_view.setStyleSheet(self.list_widget.styleSheet() + scroll_style)
        
        # 按钮样式
        button_style = f"""
            QPushButton {{
                background-color: {self.bg_color};
                color: {self.text_color};
                border: none;
                border-radius: 3px;
                padding: 5px;
                font-family: "Microsoft YaHei", "微软雅黑";
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: rgba(120, 120, 120, 150);
            }}
        """
        self.play_button.setStyleSheet(button_style)
        self.hide_show_button.setStyleSheet(button_style)
        self.move_button.setStyleSheet(button_style)
        self.search_button.setStyleSheet(button_style)

        # 标签样式
        label_style = f"""
            QLabel {{
                color: {self.text_color};
                background: transparent;
                font-family: "consolas","Microsoft YaHei", "微软雅黑";
                font-size: 14px;
            }}
        """
        self.now_time_label.setStyleSheet(label_style)
        self.total_time_label.setStyleSheet(label_style)

        # 进度条样式
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {self.bg_color};
                border: none;
                border-radius: 10px;
                font-family: "Microsoft YaHei", "微软雅黑";
                font-size: 12px;
            }}
            QProgressBar::chunk {{
                background-color: {self.theme_color};
                border-radius: 10px;
            }}
        """)

        # 应用全局样式
        self.setStyleSheet(base_style)

    def is_darkmode(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            d, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return d == 0
        except FileNotFoundError:
            return False
            
    def to_now_playing(self):
        self.list_widget.scrollToItem(self.list_widget.item(self.current_index))
        
    def hotkey(self):
        self.hotkey_states = {
            'ctrl+alt+x': False,
            'ctrl+alt+>': False,
            'ctrl+alt+<': False,
            'ctrl+alt+/': False,
            'ctrl+alt+l': False
        }
        hotkeys = [
            ('ctrl+alt+x', self.quit_musicplayer),
            ('ctrl+alt+>', self.next_song),
            ('ctrl+alt+<', self.prev_song),
            ('ctrl+alt+/', self.toggle_play_pause),
            ('ctrl+alt+l', self.hide_show_window)
        ]
        
        for hotkey, action in hotkeys:
            if keyboard.is_pressed(hotkey):
                # 如果按键刚刚按下（之前状态为False）
                if not self.hotkey_states[hotkey]:
                    self.hotkey_states[hotkey] = True
                    # 执行对应的操作
                    action()
                    # 添加短暂延迟，避免连续触发
                    time.sleep(0.3)  # 300ms防抖延迟
            else:
                # 按键释放，重置状态
                self.hotkey_states[hotkey] = False
            
    def init_playlist(self, playpath):
        global lyric_files
        music_files = []
        lyric_files = []
        for name in os.listdir(playpath):
            parts = name.split('.')
            if len(parts) > 1 and (parts[-1].lower() == "mp3" or parts[-1].lower() == "wav"):
                file_path = os.path.join(playpath, name)
                creation_time = os.path.getctime(file_path)
                music_files.append((name, creation_time))
            if len(parts) > 1 and (parts[-1].lower() == "lrc" ):
                lyric_files.append((parts[0], name))
            if os.path.isdir(os.path.join(playpath, name)):
                if name in ["lyrics", "Lyrics", "LYRICS", "歌词", "LYRIC", "Lyric"]:
                    lyric_dir = os.path.join(playpath, name)  # 歌词目录的完整路径
                    for lyric_name in os.listdir(lyric_dir):
                        parts = lyric_name.split('.')
                        if len(parts) > 1 and (parts[-1].lower() == "lrc"):
                            lyric_path = os.path.join(lyric_dir, lyric_name)  # 歌词文件的完整路径
                            lyric_files.append((parts[0], lyric_path))  # 存储完整路径而不是文件名
        # 按创建时间倒序排序
        music_files.sort(key=lambda x: x[1], reverse=True)
        # 只保留文件名
        self.playlist = [file[0] for file in music_files]
            
        
    def load_music_playlist(self):
        config_path = "config.ini"
        if not os.path.exists(config_path):
            music_path = QFileDialog.getExistingDirectory(self, "请选择音乐文件夹（第一次启动配置）")
            with open(config_path, 'w') as file:
                file.write(music_path)
        
        with open(config_path, 'r') as f:
            playpath = f.read()
            
        try:
            # 创建包含文件名和创建时间的列表
            self.init_playlist(playpath)
        except FileNotFoundError:
            QMessageBox.warning(self, "警告", "路径不存在")
            music_path = QFileDialog.getExistingDirectory(self, "请选择音乐文件夹")
            with open(config_path, 'w') as file:
                file.write(music_path)
            self.init_playlist(music_path)
            
        self.update_list_widget()
        # 设置当前索引为0（第一首歌）并播放
        if self.playlist:
            self.current_index = 0
            self.play_music()

    def search(self):
        print("[info] 歌曲搜索")
        # 检查窗口是否已存在且未关闭
        if self.search_window is not None and self.search_window.isVisible():
            self.search_window.raise_()
            self.search_window.activateWindow()
            return
        # 否则新建
        self.search_window = SearchWindow(parent=self)
        self.search_window.show()
        self.search_window.raise_()
        self.search_window.activateWindow()
        
    def search_exec_runner(self, keyword, iscap):
        thread_search = threading.Thread(target=self.search_exec, args=(keyword, iscap))
        thread_search.daemon = True
        thread_search.start()
        
    def search_exec(self, keyword, iscap):
        """根据关键字搜索列表框中的项目"""
        # 清除之前的高亮
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setBackground(QColor(255, 255, 255, 0))
            QApplication.processEvents()
            if self.quit_flag == 1:
                break
        x=self.list_widget.count()
        # 查找匹配项
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if self.quit_flag == 1:
                break
            e=item.text()
            if iscap:
                if keyword.lower() in item.text()[:-4].lower():
                    item.setBackground(QColor(100, 150, 255, 100))
            else:
                if keyword in item.text()[:-4]:
                    item.setBackground(QColor(100, 150, 255, 100))
            QApplication.processEvents()
            self.update()
    
    def clear_highlight(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setBackground(QColor(255, 255, 255, 0))
            time.sleep(0.001)
            if self.quit_flag == 1:
                break
                
    def update_list_widget(self):
        self.list_widget.clear()
        for index, song in enumerate(self.playlist, 1):
            song_name = os.path.basename(song)
            if len(song_name) >= 60:
                song_name = song_name[0:60] + "..."
            display_text = f" {song_name}"
            self.list_widget.addItem(display_text)

    def play_selected_song(self):
            global c
        #try:
            c = 0
            selected_items = self.list_widget.selectedItems()
            if selected_items:
                selected_index = self.list_widget.row(selected_items[0])
                self.current_index = selected_index
                self.play_music()
            '''except Exception as e:
            print(f"选择歌曲错误: {str(e)}")
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("错误")
            msg_box.setText("选择歌曲时发生错误")
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.setModal(True)
            msg_box.exec_()'''
    def get_lyrics_on_file(self,path):
        path=path.replace(".mp3","")
        for i in range(len(lyric_files)):
                if path.split("\\")[-1].replace(".mp3","")==lyric_files[i][1].split("\\")[-1].replace(".lrc",""):
                    with open(lyric_files[i][1], encoding='utf-8') as file:
                        lyrics_f = file.read()
                        print(lyrics_f)
                        return lyrics_f
            
    def get_lyrics(self, path):
        try:
            # 加载 MP3 文件的 ID3 标签
            audio = ID3(path)
            
            # 查找 USLT 帧（歌词帧）
            # USLT 帧可能有多个（不同语言），这里取第一个
            for frame in audio.values():
                if isinstance(frame, USLT):
                    # frame.text 即为歌词内容
                    # frame.lang 是语言代码（如 'eng' 表示英文）
                    # frame.description 是描述（通常为空）
                    return frame.text
            
            # 若没有 USLT 帧，返回无歌词
            return self.get_lyrics_on_file(path)
        except:
            return self.get_lyrics_on_file(path)
    
    def process_album_art_fast(self,image_data, output_size=(230, 230)):
        """
        快速版本：使用预计算和批量操作
        """
        # 打开和预处理图片（同上）
        if isinstance(image_data, str):
            img = Image.open(image_data)
        elif isinstance(image_data, bytes):
            img = Image.open(io.BytesIO(image_data))
        elif isinstance(image_data, Image.Image):
            img = image_data
        else:
            raise ValueError("不支持的图片数据类型")
        
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        img = img.resize(output_size, Image.Resampling.LANCZOS)
        
        # 使用更高效的方法：一次性处理所有条带
        width, height = img.size
        
        # 预计算所有模糊半径
        num_strips = 30  # 减少条带数量提高速度
        strip_width = width // num_strips
        
        result_strips = []
        for i in range(num_strips):
            start_x = i * strip_width
            end_x = (i + 1) * strip_width if i < num_strips - 1 else width
            
            progress = start_x / width
            blur_radius = max(0.5, 8 * (1 - progress))  # 降低最大模糊半径
            
            strip = img.crop((start_x, 0, end_x, height))
            
            if blur_radius > 0.5:
                # 使用更快的模糊方法
                blurred_strip = strip.filter(ImageFilter.GaussianBlur(blur_radius))
            else:
                blurred_strip = strip
            
            result_strips.append(blurred_strip)
        
        # 合并所有条带
        result = Image.new('RGBA', (width, height))
        x_offset = 0
        for strip in result_strips:
            result.paste(strip, (x_offset, 0))
            x_offset += strip.width

        # 添加从左到右的 alpha 渐变：左侧完全透明（0%），在宽度的70%处达到完全不透明（100%），之后保持不透明
        try:
            gradient_end = int(width * 0.7)
            if gradient_end <= 0:
                # 退化情况：直接全不透明
                mask = Image.new('L', (width, height), 255)
            else:
                # 先创建 1px 高度的水平渐变，再放大到目标高度，提高效率
                row = Image.new('L', (width, 1))
                for x in range(width):
                    if x <= gradient_end:
                        alpha = int((x / gradient_end) * 255)
                    else:
                        alpha = 255
                    row.putpixel((x, 0), alpha)
                mask = row.resize((width, height), Image.Resampling.BILINEAR)

            # 将 mask 作为 alpha 通道设置到结果图片
            result.putalpha(mask)
        except Exception as e:
            # 如果渐变出错，不影响图片本身，仅记录警告并返回原图
            print(f"[warn] apply alpha gradient failed: {e}")

        return result
    def play_songs(self):
        global lyrics_lines,lyrics
        if 0 <= self.current_index < len(self.playlist):
            music_folder = self.get_playpath()
            current_song = os.path.join(music_folder, self.playlist[self.current_index])
            print(f"正在播放: {current_song}")
            lyrics = self.get_lyrics(current_song)
            lyrics_lines = lyrics.split("\n")
            self.lyric_view.clear()
            lyrics,lyric_list=self.parse_lrc(lyrics)
            #这里放置图片
            audio=ID3(current_song)
            try:
                    for tag in audio.values():
                        if isinstance(tag, APIC):
                            album_image_original = tag.data
                            # 处理为 PIL.Image
                            pil_img = self.process_album_art_fast(album_image_original)
                            try:
                                # 将 PIL.Image 保存为 PNG 字节，然后由 QPixmap 从数据加载
                                buf = io.BytesIO()
                                pil_img.save(buf, format='PNG')
                                data = buf.getvalue()
                                pixmap = QPixmap()
                                if pixmap.loadFromData(data):
                                    # 保留对 pixmap 的引用，避免被垃圾回收导致显示问题
                                    self._current_album_pixmap = pixmap
                                    self.image_label.setPixmap(pixmap)
                                else:
                                    print("[warn] pixmap.loadFromData failed")
                                    self.image_label.clear()
                            except Exception as e:
                                print(f"[warn] album art conversion failed: {e}")
                                self.image_label.clear()
                            break
            except:
                self.image_label.clear()
            for line in lyric_list:
                self.lyric_view.addItem(line)

            
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
            
            pygame.mixer.music.load(current_song)
            pygame.mixer.music.play()
            self.is_playing = True
            self.play_button.setText("暂停")  
            self.list_widget.setCurrentRow(self.current_index)
            
            # 重置乐时长，让refresh_ui重新计算
            self.music_long = 0
            
    def play_music(self):
        global lyric_index
        if not self.playlist:
            return
            
        '''try:'''
        self.play_songs()
        lyric_index = 0
        '''except Exception as e:
            for i in range(5):
                print("[warn] 播放错误，正在重试...")
                try:
                    self.play_songs()
                    break
                except:
                    pass
                time.sleep(1)
            else:
                print(f"播放错误: {str(e)}")
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setWindowTitle("错误")
                msg_box.setText(f"无法播放当前歌曲: {str(e)}")
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.setModal(True)
                msg_box.exec_()'''

    def get_playpath(self):
        with open('config.ini', 'r') as f:
            return f.read().strip()
    def parse_lrc(self,lrc_content: str):
        """
        解析LRC文件格式
        
        Args:
            lrc_content: LRC文件内容字符串
            
        Returns:
            Tuple[List[int], List[str]]: (时间列表(毫秒), 歌词列表)
        """
        # 存储解析结果
        time_list = []
        lyric_list = []
        
        # 存储元数据
        metadata = {}
        
        # 正则表达式匹配时间标签和歌词
        time_pattern = re.compile(r'\[(\d+):(\d+)\.?(\d+)?\](.*)')
        # 正则表达式匹配元数据标签
        metadata_pattern = re.compile(r'\[(ti|ar|al|by|offset):(.*)\]', re.I)
        
        lines = lrc_content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 检查是否是元数据标签
            metadata_match = metadata_pattern.match(line)
            if metadata_match:
                tag_type = metadata_match.group(1).lower()
                tag_value = metadata_match.group(2).strip()
                metadata[tag_type] = tag_value
                continue
                
            # 检查是否是时间标签
            time_match = time_pattern.match(line)
            if time_match:
                minutes = int(time_match.group(1))
                seconds = int(time_match.group(2))
                milliseconds = int(time_match.group(3)) if time_match.group(3) else 0
                
                # 处理毫秒位数（可能是2位或3位）
                if time_match.group(3):
                    if len(time_match.group(3)) == 2:  # 百分秒
                        milliseconds = milliseconds * 10
                    # 如果是3位，已经是毫秒，不需要转换
                
                # 计算总毫秒数
                total_ms = (minutes * 60 + seconds) * 1000 + milliseconds
                
                lyric = time_match.group(4).strip()
                
                # 只添加有歌词的时间点
                if lyric:
                    time_list.append(total_ms)
                    lyric_list.append(lyric)
        
        # 处理偏移量（如果有）
        if 'offset' in metadata:
            try:
                offset = int(metadata['offset'])
                time_list = [max(0, time + offset) for time in time_list]
            except ValueError:
                pass  # 如果offset不是有效数字，忽略
        
        return time_list, lyric_list


    def toggle_play_pause(self):
        if not self.playlist:
            return
            
        if self.is_playing:
            pygame.mixer.music.pause()
            self.is_playing = False
            self.play_button.setText("播放")  # 修复按钮文字显示
        else:
            pygame.mixer.music.unpause()
            self.is_playing = True
            self.play_button.setText("暂停")  # 修复按钮文字显示

    def prev_song(self):
        global c
        if not self.playlist:
            return
            
        c = 0
        self.current_index = (self.current_index - 1) % len(self.playlist)
        self.play_music()

    def next_song(self):
        global c
        if not self.playlist:
            return
            
        c = 0
        self.current_index = (self.current_index + 1) % len(self.playlist)
        self.play_music()

    def hide_show_window(self):
        if self.show_flag == 0:
            self.show()
            self.show_flag = 1
        else:
            self.hide()
            self.show_flag = 0

    def start_progress_update(self):
        update_thread = threading.Thread(target=self.update_progress)
        update_thread.daemon = True
        update_thread.start()

    def update_progress(self):
        global c
        while True:
            if self.quit_flag == 1:
                break
                
            if self.is_playing:
                current_pos = pygame.mixer.music.get_pos()
                self.progress_update_signal.emit(current_pos, self.music_long)
                if not pygame.mixer.music.get_busy() and self.playlist:
                    c = 0
                    # 当一首歌曲播放完毕，自动播放下一首
                    self.current_index = (self.current_index + 1) % len(self.playlist)
                    self.play_music()

            time.sleep(0.1)

    def start_music_thread(self):
        music_thread = threading.Thread(target=self.control_music)
        music_thread.daemon = True
        music_thread.start()

    def control_music(self):
        # 等待初始化完成
        time.sleep(1)
        if self.playlist:
            self.play_music()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 检查鼠标点击的位置是否在子控件上
            child = self.childAt(event.pos())
            if not child:  # 只有当点击的不是子控件时才允许拖动
                self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event):
        if hasattr(self, 'drag_position') and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def refresh_ui(self):
            global lyric_index
            if self.is_playing and pygame.mixer.music.get_busy() and self.playlist:
                a = pygame.mixer.music.get_pos()
                current_pos = a + c
                lyric_index=bisect.bisect_left(lyrics,current_pos)-1
                self.lyric_view.setCurrentRow(lyric_index)
                self.lyric_view.scrollToItem(self.lyric_view.item(lyric_index))

                # 确保current_pos不超过总时长
                if self.music_long > 0 and current_pos > self.music_long:
                    current_pos = self.music_long
                
                # 发送信号到主线程更新UI（关键修复：确保信号持续发射）
                self.update_ui_signal.emit(current_pos, self.music_long)
                
                # 首次获取总时长
                if self.music_long == 0:
                    try:
                        music_folder = self.get_playpath()
                        current_song = os.path.join(music_folder, self.playlist[self.current_index])
                        audio = pygame.mixer.Sound(current_song)
                        self.music_long = int(audio.get_length() * 1000)
                        # 立即发送一次信号，确保总时长显示
                        self.update_ui_signal.emit(current_pos, self.music_long)
                    except Exception as e:
                        print(f"[warn] 获取音乐时长失败: {str(e)}")
            elif self.is_playing and not pygame.mixer.music.get_busy():
                # 播放结束但未切换歌曲时，强制更新进度条到100%
                if self.music_long > 0:
                    self.update_ui_signal.emit(self.music_long, self.music_long)
    lyric_index=0
    def update_ui_handler(self, current_pos, total_pos):
        global lyric_index
        """主线程中处理UI更新（关键修复：确保此函数被正确调用）"""
        # 更新当前时间标签
        minutes = current_pos // 60000
        seconds = (current_pos % 60000) // 1000

        self.now_time_label.setText(f"{minutes:02d}:{seconds:02d}")
        


        # 更新进度条
        if total_pos > 0:
            self.progress_bar.setMaximum(total_pos)
            self.progress_bar.setValue(current_pos)
            self.progress_bar.update() 
        # 更新总时间标签
        if total_pos > 0:
            total_minutes = total_pos // 60000
            total_seconds = (total_pos % 60000) // 1000
            self.total_time_label.setText(f"{total_minutes:02d}:{total_seconds:02d}")

    def closeEvent(self, event):
        """窗口关闭时清理资源"""
        self.quit_flag = 1
        pygame.mixer.quit()
        event.accept()

    def progress_bar_clicked(self, event):
        # 计算点击位置对应的音乐时间
        global c
        if self.music_long <= 0:
            return
            
        width = self.progress_bar.width()
        x = event.x()
        ratio = x / width
        target_time = int(self.music_long * ratio)
        c = target_time - pygame.mixer.music.get_pos()
        
        try:
            # 设置音乐播放位置（毫秒转换为秒）
            pygame.mixer.music.set_pos(target_time / 1000.0)
            
            # 立即更新UI
            self.update_ui_signal.emit(target_time + c, self.music_long)
        except Exception as e:
            print(f"设置播放位置失败: {str(e)}")


class SearchWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_player = parent  # 保存主窗口引用
        self.initUI()
        self.update_ui_theme()
     
    def initUI(self):
        # 设置窗口属性
        self.setWindowTitle("搜索窗口")
        self.setWindowFlags(Qt.Window |Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowStaysOnTopHint)
        self.setGeometry(400, 400,300,100)
        
        # 创建布局
        layout = QVBoxLayout()

        # 创建搜索输入框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入搜索关键词")
        layout.addWidget(self.search_input)
        
        h_layout = QHBoxLayout()
        layout.addLayout(h_layout)
        
        # 创建搜索按钮
        self.search_button = QPushButton("搜索")
        self.search_button.clicked.connect(self.perform_search)
        h_layout.addWidget(self.search_button)

        self.close_button = QPushButton("关闭")
        self.close_button.clicked.connect(self.close)
        h_layout.addWidget(self.close_button)

        self.iscap_checkbox = QCheckBox("不区分大小写")
        layout.addWidget(self.iscap_checkbox)
        self.iscap_checkbox.setChecked(True)
        
        # 设置布局
        self.setLayout(layout)
        
        # 设置窗口效果
        self.windowEffect = WindowEffect()
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.move(500,500)
    
    def update_ui_theme(self):
        # 从父窗口获取主题设置
        if self.parent_player:
            is_dark = self.parent_player.is_dark
            bg_color = self.parent_player.bg_color
            text_color = self.parent_player.text_color
        else:
            # 默认主题
            is_dark = False
            bg_color = "rgba(255, 255, 255, 100)"
            text_color = "rgba(0, 0, 0, 230)"
        
        # 设置亚克力效果
        if is_dark:
            self.windowEffect.setAcrylicEffect(int(self.winId()), gradientColor="404040A0")
        else:
            self.windowEffect.setAcrylicEffect(int(self.winId()), gradientColor="FFFFFFA0")
        
        # 设置按钮样式
        button_style = f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border: none;
                border-radius: 3px;
                padding: 5px;
                font-family: "Microsoft YaHei", "微软雅黑";
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: rgba(120, 120, 120, 150);
            }}
        """
        self.search_button.setStyleSheet(button_style)
        self.close_button.setStyleSheet(button_style)
        
        # 设置复选框样式
        self.iscap_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {text_color};
                font-family: "Microsoft YaHei", "微软雅黑";
                font-size: 12px;
            }}
        """)
        
        # 设置输入框样式
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {bg_color};
                color: {text_color};
                border: none;
                border-radius: 3px;
                padding: 5px;
                font-family: "Microsoft YaHei", "微软雅黑";
                font-size: 12px;
            }}
        """)
    
    def perform_search(self):
        keyword = self.search_input.text()
        iscap = self.iscap_checkbox.isChecked()
        
        if keyword and self.parent_player:
            print(f"搜索关键词: {keyword}")
            self.parent_player.search_exec_runner(keyword, iscap)

    def closeEvent(self, event):
        # 清除搜索高亮
        if self.parent_player:
            self.parent_player.clear_highlight()
            self.parent_player.search_window = None  # 关键：关闭时清理引用
        event.accept()


if __name__ == "__main__":
    # 确保中文显示正常
    import matplotlib
    matplotlib.rcParams["font.family"] = ["consolas","SimHei", "WenQuanYi Micro Hei", "Heiti TC"]
    
    app = QApplication(sys.argv)
    player = MusicPlayer()
    sys.exit(app.exec_())