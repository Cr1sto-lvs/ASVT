#!/usr/bin/env python3
"""
Графическое приложение для построения и симуляции логических схем.
Основные возможности:
* Создание логических элементов (AND, OR, XOR, NOT и др.).
* Подключение элементов друг к другу.
* Установка состояний входных сигналов (двойной клик для смены 0/1).
* Автоматический расчёт выходных значений схемы.
* Таблица истинности для каждой комбинации входных сигналов.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set

# Яркая цветовая палитра для блоков
BRIGHT_BLOCK_COLORS: Dict[str, str] = {
    "SOURCE": "#FFD700",  # Золотистый цвет для входов
    "TERMINATOR": "#00FFFF",  # Голубой цвет для выходов
    "AND_GATE": "#FF6347",  # Томатно-красный цвет для AND
    "OR_GATE": "#ADFF2F",  # Светло-зелёный цвет для OR
    "XOR_GATE": "#EE82EE",  # Фиолетово-розовый цвет для XOR
    "NOT_GATE": "#CD5C5C",  # Терракотово-коричневый цвет для NOT
    "NAND_GATE": "#FFFACD",  # Кремовый цвет для NAND
    "NOR_GATE": "#ADD8E6",  # Бледно-голубой цвет для NOR
}

# Спецификация логических элементов
LOGICAL_ELEMENTS_CONFIG: Dict[str, Dict[str, object]] = {
    "AND_GATE": {"inputs": 2, "func": lambda values: all(values)},  # AND
    "OR_GATE": {"inputs": 2, "func": lambda values: any(values)},  # OR
    "XOR_GATE": {"inputs": 2, "func": lambda values: sum(values) % 2},  # XOR
    "NOT_GATE": {"inputs": 1, "func": lambda values: not values[0]},  # NOT
    "NAND_GATE": {"inputs": 2, "func": lambda values: not all(values)},  # NAND
    "NOR_GATE": {"inputs": 2, "func": lambda values: not any(values)},  # NOR
    "TERMINATOR": {"inputs": 1, "func": lambda values: values[0]},  # Output
}

@dataclass
class WireLink:
    """
    Класс представляет связь (провода) между логическими элементами.
    """
    sender: "LogicNode"
    receiver: "LogicNode"
    wire_id: int
    receiver_slot: Optional[int] = None

    def refresh_link(self) -> None:
        """
        Обновляет линию провода на канвасе.
        """
        x1, y1 = self.sender.output_anchor()
        x2, y2 = self.receiver.input_anchor(self.receiver_slot)
        self.sender.app.gui_canvas.coords(self.wire_id, x1, y1, x2, y2)

@dataclass
class LogicNode:

    app: "SimulatorApp"
    node_type: str
    pos_x: int = 40  # Установите начальные значения по умолчанию
    pos_y: int = 40
    width: int = 100
    height: int = 50
    box_id: Optional[int] = None
    text_id: Optional[int] = None
    signal_value: Optional[bool] = False
    active_status: bool = False
    incoming_links: List[WireLink] = field(default_factory=list)
    outgoing_links: List[WireLink] = field(default_factory=list)
    connector_ids: List[int] = field(default_factory=list)
    slot_map: Dict[int, WireLink] = field(default_factory=dict)
    indicator_id: Optional[int] = None

    


    def __post_init__(self) -> None:
        """
        Создаёт графическое представление узла на экране.
        """
        self.draw_node()

    def draw_node(self) -> None:
        """
        Рисует прямоугольник и текст узла на холсте.
        """
        canvas = self.app.gui_canvas
        self.box_id = canvas.create_rectangle(
            self.pos_x,
            self.pos_y,
            self.pos_x + self.width,
            self.pos_y + self.height,
            fill=BRIGHT_BLOCK_COLORS.get(self.node_type, "#DDDDDD"),  # Яркий фон
            outline="#FFFFFF",  # Белый контур
            width=2
        )
        self.text_id = canvas.create_text(
            self.pos_x + self.width // 2,
            self.pos_y + self.height // 2,
            text=self.label_text(),
            font=("Helvetica", 11, "bold"),
            fill="#000000"  # Чёрный шрифт текста
        )
        self.bind_interactions(self.box_id)
        self.bind_interactions(self.text_id)
        self.draw_connectors()
        self.update_appearance()

    def label_text(self) -> str:
        """
        Возвращает текстовую подпись узла.
        """
        if self.node_type == "SOURCE":
            status = "ON" if self.active_status else "OFF"
            return f"SOURCE {status}"
        if self.node_type == "TERMINATOR":
            return "END"
        return self.node_type

    def bind_interactions(self, widget_id: int) -> None:
        """
        Присваивает обработчики событий элементу.
        """
        canvas = self.app.gui_canvas
        canvas.tag_bind(widget_id, "<Button-1>", self.on_click)
        canvas.tag_bind(widget_id, "<B1-Motion>", self.on_drag)
        canvas.tag_bind(widget_id, "<ButtonRelease-1>", self.on_release)
        canvas.tag_bind(widget_id, "<Double-1>", self.on_double_click)
        canvas.tag_bind(widget_id, "<Button-3>", self.on_right_click)

    def on_click(self, event: tk.Event) -> None:
        """
        Обработчик одиночного клика мыши.
        """
        if self.app.mode == "CONNECTION":
            self.app.process_link_request(self)
            return
        self.app.select_node(self)
        self.drag_offset = (event.x - self.pos_x, event.y - self.pos_y)
        self.being_dragged = False

    def on_drag(self, event: tk.Event) -> None:
        """
        Обработчик движения мыши с удерживаемой кнопкой.
        """
        if self.drag_offset is None or self.app.mode == "CONNECTION":
            return
        self.being_dragged = True
        dx, dy = self.drag_offset
        self.move_to(event.x - dx, event.y - dy)

    def on_release(self, _event: tk.Event) -> None:
        """
        Обработчик отпускания кнопки мыши.
        """
        if self.app.mode != "CONNECTION" and self.node_type == "SOURCE" and not self.being_dragged:
            self.active_status = not self.active_status
            self.update_appearance()
            self.app.update_logic()
        self.drag_offset = None
        self.being_dragged = False

    def on_double_click(self, _event: tk.Event) -> None:
        """
        Обработчик двойного клика мыши.
        """
        if self.node_type == "SOURCE":
            self.active_status = not self.active_status
            self.signal_value = not bool(self.signal_value)
            self.update_label()
            self.app.update_logic()
        elif self.node_type == "TERMINATOR":
            self.app.update_logic()

    def on_right_click(self, _event: tk.Event) -> None:
        """
        Обработчик правого клика мыши.
        """
        if self.node_type == "SOURCE":
            self.active_status = not self.active_status
            self.update_appearance()
            self.app.update_logic()

    def move_to(self, new_x: int, new_y: int) -> None:
        """
        Изменяет положение узла на холсте.
        """
        self.pos_x = max(10, new_x)
        self.pos_y = max(10, new_y)
        canvas = self.app.gui_canvas
        canvas.coords(
            self.box_id,
            self.pos_x,
            self.pos_y,
            self.pos_x + self.width,
            self.pos_y + self.height
        )
        canvas.coords(
            self.text_id,
            self.pos_x + self.width // 2,
            self.pos_y + self.height // 2
        )
        self.draw_connectors()
        self.update_indicator()
        for link in self.incoming_links + self.outgoing_links:
            link.refresh_link()

    def supports_output(self) -> bool:
        """
        Проверяет, поддерживает ли узел вывод сигнала.
        """
        return True

    def max_input_slots(self) -> int:
        """
        Максимально возможное количество входов для данного узла.
        """
        if self.node_type == "SOURCE":
            return 0
        return LOGICAL_ELEMENTS_CONFIG.get(self.node_type, {}).get("inputs", 2)

    def has_available_input(self) -> bool:
        """
        Проверяет доступность свободных входов.
        """
        return len(self.slot_map) < self.max_input_slots()

    def input_anchor(self, slot_idx: Optional[int] = None) -> tuple[int, int]:
        """
        Определяет точку крепления входящей линии.
        """
        positions = self.input_slot_positions()
        if slot_idx is not None and 0 <= slot_idx < len(positions):
            anchor_y = positions[slot_idx]
        else:
            anchor_y = positions[0] if positions else self.pos_y + self.height // 2
        return (self.pos_x - 14, anchor_y)

    def output_anchor(self) -> tuple[int, int]:
        """
        Определяет точку вывода сигнала.
        """
        return (self.pos_x + self.width + 14, self.pos_y + self.height // 2)

    def remove_link(self, link: WireLink) -> None:
        """
        Удаляет ссылку из списков входящих и исходящих.
        """
        if link in self.incoming_links:
            self.incoming_links.remove(link)
            self.free_input_slot(link)
        if link in self.outgoing_links:
            self.outgoing_links.remove(link)

    def update_label(self) -> None:
        """
        Обновляет текстовую надпись узла.
        """
        if self.text_id is not None:
            self.app.gui_canvas.itemconfigure(self.text_id, text=self.label_text())

    def draw_connectors(self) -> None:
        """
        Рисует соединители (точки контактов) для входов и выходов.
        """
        canvas = self.app.gui_canvas
        for cid in self.connector_ids:
            canvas.delete(cid)
        self.connector_ids.clear()
        connector_color = "#AAAAAA"
        for anchor_y in self.input_slot_positions():
            cid = canvas.create_line(
                self.pos_x - 14,
                anchor_y,
                self.pos_x,
                anchor_y,
                width=4,
                fill=connector_color,
                capstyle=tk.ROUND
            )
            self.connector_ids.append(cid)
        anchor_y = self.pos_y + self.height // 2
        cid = canvas.create_line(
            self.pos_x + self.width,
            anchor_y,
            self.pos_x + self.width + 14,
            anchor_y,
            width=4,
            fill=connector_color,
            capstyle=tk.ROUND
        )
        self.connector_ids.append(cid)

    def input_slot_positions(self) -> List[float]:
        """
        Рассчитывает позиции точек для входов.
        """
        slots = self.max_input_slots()
        if slots <= 0:
            return []
        return [
            self.pos_y + (i + 1) * self.height / (slots + 1)
            for i in range(slots)
        ]

    def allocate_input_slot(self, link: WireLink) -> Optional[int]:
        """
        Выделяет свободный слот для входящей линии.
        """
        slots = self.max_input_slots()
        if slots <= 0:
            return None
        for idx in range(slots):
            if idx not in self.slot_map:
                self.slot_map[idx] = link
                return idx
        return None

    def free_input_slot(self, link: WireLink) -> None:
        """
        Освобождает занятую ранее ячейку для входящей линии.
        """
        for idx, l in list(self.slot_map.items()):
            if l == link:
                del self.slot_map[idx]
                break

    def update_appearance(self) -> None:
        """
        Обновляет внешний вид узла (цвет фона и надписи).
        """
        if self.box_id is None:
            return
        fill_color = BRIGHT_BLOCK_COLORS.get(self.node_type, "#DDDDDD")
        if self.node_type == "SOURCE":
            fill_color = "#00FF00" if self.active_status else "#FF0000"
        self.app.gui_canvas.itemconfigure(self.box_id, fill=fill_color)
        self.update_label()
        self.update_indicator()

    def update_indicator(self) -> None:
        """
        Обновляет индикатор сигнала на выходе узла.
        """
        canvas = self.app.gui_canvas
        if self.node_type != "TERMINATOR":
            if hasattr(self, 'indicator_id'):
                canvas.delete(self.indicator_id)
                self.indicator_id = None
            return
        radius = 9
        center_x = self.pos_x + self.width - 18
        center_y = self.pos_y + self.height - 14
        if self.indicator_id is None:
            self.indicator_id = canvas.create_oval(
                center_x - radius,
                center_y - radius,
                center_x + radius,
                center_y + radius,
                outline="",
                width=0
            )
        else:
            canvas.coords(
                self.indicator_id,
                center_x - radius,
                center_y - radius,
                center_x + radius,
                center_y + radius
            )
        if self.signal_value is None:
            color = "#CCCCCC"
        elif bool(self.signal_value):
            color = "#FFD700"
        else:
            color = "#A9A9A9"
        canvas.itemconfigure(self.indicator_id, fill=color)

class SimulatorApp:
    """
    Главный класс приложения для моделирования логических схем.
    """
    def __init__(self) -> None:
        self.window = tk.Tk()
        self.window.title("Симулятор логических схем")
        self.window.geometry("1100x650")
        self.mode = "SELECTION"
        self.nodes: List[LogicNode] = []
        self.links: List[WireLink] = []
        self.selected_node: Optional[LogicNode] = None
        self.link_origin: Optional[LogicNode] = None
        self.step_size = 80
        self.start_pos = {
            "SOURCE": (80, 80),
            "GATES": (320, 80),
            "TERMINATOR": (560, 80),
        }
        self.counter = {
            "SOURCE": 0,
            "GATES": 0,
            "TERMINATOR": 0,
        }
        self.build_gui()

    def build_gui(self) -> None:
        """
        Настраивает графический интерфейс приложения.
        """
        main_frame = ttk.Frame(self.window, padding=8)
        main_frame.pack(fill=tk.BOTH, expand=True)

        side_pane = ttk.Frame(main_frame)
        side_pane.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Label(
            side_pane,
            text="Панель инструментов:",
            font=("Helvetica", 12, "bold"),
            foreground="#FFFFFF",
            background="#333333"
        ).pack(pady=(0, 4))

        for node_type in ["SOURCE", "AND_GATE", "OR_GATE", "XOR_GATE", "NOT_GATE", "NAND_GATE", "NOR_GATE", "TERMINATOR"]:
            button = ttk.Button(
                side_pane,
                text=node_type,
                style="DarkButton.TButton",
                command=lambda n=node_type: self.create_node(n)
            )
            button.pack(fill=tk.X, pady=2)

        ttk.Separator(side_pane, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)

        ttk.Label(
            side_pane,
            text="Управление схемой:",
            font=("Helvetica", 12, "bold"),
            foreground="#FFFFFF",
            background="#333333"
        ).pack(pady=(0, 4))

        ttk.Button(
            side_pane,
            text="Подключить узлы",
            style="DarkButton.TButton",
            command=self.enter_connection_mode
        ).pack(fill=tk.X, pady=2)

        ttk.Button(
            side_pane,
            text="Удалить выделенный",
            style="DarkButton.TButton",
            command=self.delete_selected_node
        ).pack(fill=tk.X, pady=2)

        ttk.Button(
            side_pane,
            text="Очистить рабочую зону",
            style="DarkButton.TButton",
            command=self.clear_workarea
        ).pack(fill=tk.X, pady=2)

        ttk.Separator(side_pane, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)

        ttk.Label(
            side_pane,
            text="Информация:",
            font=("Helvetica", 12, "bold"),
            foreground="#FFFFFF",
            background="#333333"
        ).pack(pady=(0, 4))

        self.status_variable = tk.StringVar(value="Начните добавлять узлы и подключать их.")
        info_label = ttk.Label(
            side_pane,
            textvariable=self.status_variable,
            wraplength=220,
            foreground="#FFFFFF",
            background="#333333"
        )
        info_label.pack(fill=tk.X, pady=(8, 0))

        workarea = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        workarea.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        drawing_area = ttk.Frame(workarea)
        workarea.add(drawing_area, weight=3)

        self.gui_canvas = tk.Canvas(
            drawing_area,
            background="#333333",  # Темный фон рабочего пространства
            highlightthickness=1,
            highlightbackground="#555555"
        )
        self.gui_canvas.pack(fill=tk.BOTH, expand=True)

        table_frame = ttk.Frame(workarea, padding=(10, 0, 0, 0))
        workarea.add(table_frame, weight=1)

        ttk.Label(
            table_frame,
            text="Таблица истинности:",
            font=("Helvetica", 12, "bold"),
            foreground="#FFFFFF",
            background="#333333"
        ).pack(pady=(0, 4))

        scrollable_container = ttk.Frame(table_frame)
        scrollable_container.pack(fill=tk.BOTH, expand=True)

        # Определение стиля для Treeview
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("DarkTreeview", parent="Treeview", background="#333333", foreground="#ffffff", fieldbackground="#333333")
        style.map("DarkTreeview", background=[('selected', '#555555')], foreground=[('selected', '#ffffff')])


    # Далее создаётся дерево Treeview с указанным стилем
        self.data_table = ttk.Treeview(
        scrollable_container,
        columns=("DATA",),
        show="headings",
        height=18,
        # style="DarkTreeview" 
        ) # Здесь используем созданный стиль
        self.data_table.heading("DATA", text="Данные")
        self.data_table.column("DATA", width=260, anchor=tk.CENTER, stretch=True)
        

        v_scrollbar = ttk.Scrollbar(
            scrollable_container,
            orient=tk.VERTICAL,
            command=self.data_table.yview,
            style="DarkScrollbar.Vertical.TScrollbar"
        )
        h_scrollbar = ttk.Scrollbar(
            scrollable_container,
            orient=tk.HORIZONTAL,
            command=self.data_table.xview,
            style="DarkScrollbar.Horizontal.TScrollbar"
        )
        self.data_table.configure(
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set
        )
        self.data_table.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.update_data_table()


    def determine_category(self, node_type: str) -> str:
        """
        Категоризирует тип узла для дальнейшего расположения.
        """
        if node_type == "SOURCE":
            return "SOURCE"
        if node_type == "TERMINATOR":
            return "TERMINATOR"
        return "GATES"

    def next_spawn_position(self, node_type: str) -> tuple[int, int]:
        """
        Определяет следующее свободное местоположение для добавления узла.
        """
        category = self.determine_category(node_type)
        base_x, base_y = self.start_pos[category]
        offset = self.counter[category] * self.step_size
        self.counter[category] += 1
        return base_x, base_y + offset

    def create_node(self, node_type: str) -> None:
        x, y = self.next_spawn_position(node_type)
        new_node = LogicNode(self, node_type, pos_x=x, pos_y=y)  # Теперь правильно передаем позиционные аргументы
        self.nodes.append(new_node)
        self.status_variable.set(f"Добавлен узел {node_type}. Можно перемещать.")
        self.update_data_table()

    def select_node(self, node: LogicNode) -> None:
        """
        Выбирает указанный узел на рабочем пространстве.
        """
        if self.selected_node == node:
            return
        if self.selected_node:
            self.gui_canvas.itemconfigure(self.selected_node.box_id, width=2)
        self.selected_node = node
        self.gui_canvas.itemconfigure(node.box_id, width=3)

    def enter_connection_mode(self) -> None:
        """
        Переключается в режим подключения узлов.
        """
        if self.mode == "CONNECTION":
            self.mode = "SELECTION"
            self.link_origin = None
            self.status_variable.set("Режим выбора. Двойной клик по SOURCE активирует его.")
        else:
            self.mode = "CONNECTION"
            self.link_origin = None
            self.status_variable.set("Режим подключения: нажмите на отправляющий узел, затем на принимающий.")

    def process_link_request(self, node: LogicNode) -> None:
        """
        Устанавливает новое соединение между узлами.
        """
        if self.link_origin is None:
            if node.max_input_slots() == 0:
                self.link_origin = node
                self.status_variable.set("Источник выбран. Нажмите на цель.")
            elif node.supports_output():
                self.link_origin = node
                self.status_variable.set("Источник выбран. Нажмите на цель.")
            else:
                messagebox.showinfo("Ошибка", "Узел не может стать источником.")
            return
        if node == self.link_origin:
            self.status_variable.set("Самоподключение невозможно.")
            return
        if not node.has_available_input():
            messagebox.showinfo("Ошибка", "Цель не имеет свободных входов.")
            return
        new_link = WireLink(
            sender=self.link_origin,
            receiver=node,
            wire_id=self.gui_canvas.create_line(
                *self.link_origin.output_anchor(),
                *node.input_anchor(),
                width=2,
                fill="#FFFFFF",
                smooth=True
            )
        )
        slot = node.allocate_input_slot(new_link)
        if slot is None:
            self.gui_canvas.delete(new_link.wire_id)
            messagebox.showinfo("Ошибка", "Цель не имеет свободных входов.")
            self.link_origin = None
            self.mode = "SELECTION"
            self.status_variable.set("Ошибка: выбрана цель без свободных входов.")
            return
        new_link.receiver_slot = slot
        self.links.append(new_link)
        self.link_origin.outgoing_links.append(new_link)
        node.incoming_links.append(new_link)
        new_link.refresh_link()
        self.status_variable.set("Соединение установлено.")
        self.update_data_table()
        self.enter_connection_mode()

    def remove_node(self, node: LogicNode) -> None:
        """
        Полностью удаляет узел и связанные с ним линии.
        """
        for link in list(node.incoming_links):
            self.delete_link(link, silently=True)
        for link in list(node.outgoing_links):
            self.delete_link(link, silently=True)
        if node.box_id:
            self.gui_canvas.delete(node.box_id)
        if node.text_id:
            self.gui_canvas.delete(node.text_id)
        for cid in node.connector_ids:
            self.gui_canvas.delete(cid)
        if hasattr(node, 'indicator_id') and node.indicator_id:
            self.gui_canvas.delete(node.indicator_id)
        self.nodes.remove(node)
        self.update_data_table()

    def delete_link(self, link: WireLink, silently: bool = False) -> None:
        """
        Удаляет соединение между узлами.
        """
        link.sender.remove_link(link)
        link.receiver.remove_link(link)
        self.gui_canvas.delete(link.wire_id)
        if link in self.links:
            self.links.remove(link)
        if not silently:
            self.update_data_table()

    def delete_selected_node(self) -> None:
        """
        Удаляет выделенный узел.
        """
        if not self.selected_node:
            self.status_variable.set("Узел не выбран.")
            return
        self.remove_node(self.selected_node)
        self.selected_node = None
        self.status_variable.set("Узел удалён.")

    def clear_workarea(self) -> None:
        """
        Очищает всю рабочую область.
        """
        for node in list(self.nodes):
            self.remove_node(node)
        self.links.clear()
        self.selected_node = None
        self.link_origin = None
        self.mode = "SELECTION"
        for cat in self.counter.keys():
            self.counter[cat] = 0
        self.update_data_table()
        self.status_variable.set("Рабочее пространство очищено.")

    def calculate_nodes(self, overrides: Optional[Dict[int, bool]] = None) -> Dict[int, Optional[bool]]:
        """
        Вычисляет значения всех узлов схемы.
        """
        override_values = overrides or {}
        processed_values: Dict[int, Optional[bool]] = {}

        def traverse_node(node: LogicNode, path: Set[int]) -> Optional[bool]:
            node_id = id(node)
            if node_id in processed_values:
                return processed_values[node_id]
            if node_id in path:
                raise ValueError("Обнаружен цикл в соединениях.")
            if node.node_type == "SOURCE":
                if not node.active_status:
                    processed_values[node_id] = None
                    return None
                result = override_values.get(node_id, bool(node.signal_value))
                processed_values[node_id] = result
                return result
            path.add(node_id)
            input_signals: List[bool] = []
            for link in node.incoming_links:
                prev_result = traverse_node(link.sender, path)
                if prev_result is None:
                    path.remove(node_id)
                    processed_values[node_id] = None
                    return None
                input_signals.append(prev_result)
            required_inputs = node.max_input_slots()
            if len(input_signals) < required_inputs:
                processed_values[node_id] = None
                path.remove(node_id)
                return None
            function: Optional[Callable[[List[bool]], bool]] = LOGICAL_ELEMENTS_CONFIG.get(node.node_type, {}).get("func")  # type: ignore[assignment]
            if function is None:
                processed_values[node_id] = None
            else:
                processed_values[node_id] = bool(function(input_signals))
            path.remove(node_id)
            return processed_values[node_id]

        for node in self.nodes:
            traverse_node(node, set())
        return processed_values

    def update_logic(self) -> None:
        """
        Пересчитывает значения всех узлов и обновляет экран.
        """
        try:
            results = self.calculate_nodes()
            for node in self.nodes:
                node.signal_value = results.get(id(node))
                node.update_label()
                node.update_indicator()
            self.status_variable.set("Пересчёт выполнен.")
            self.update_data_table()
        except ValueError as e:
            messagebox.showerror("Ошибка", str(e))
            self.status_variable.set("Ошибка: обнаружены циклические соединения.")

    def update_data_table(self, notify_user: bool = False) -> None:
        """
        Обновляет таблицу истинности на экране.
        """
        sources = [n for n in self.nodes if n.node_type == "SOURCE"]
        terminators = [n for n in self.nodes if n.node_type == "TERMINATOR"]

        if not hasattr(self, "data_table"):
            return

        active_sources = [src for src in sources if src.active_status]

        if not sources or not terminators:
            if notify_user:
                msg = "Нужно добавить хотя бы один SOURCE." if not sources else "Нужно добавить хотя бы один TERMINATOR."
                messagebox.showinfo("Таблица истинности", msg)
            self.data_table.configure(columns=("DATA",))
            self.data_table.heading("DATA", text="Информация")
            self.data_table.column("DATA", width=260, anchor=tk.CENTER, stretch=True)
            for item in self.data_table.get_children():
                self.data_table.delete(item)
            placeholder = "Добавьте SOURCE и TERMINATOR."
            self.data_table.insert("", tk.END, values=(placeholder,))
            return

        if not active_sources:
            self.data_table.configure(columns=("DATA",))
            self.data_table.heading("DATA", text="Информация")
            self.data_table.column("DATA", width=260, anchor=tk.CENTER, stretch=True)
            for item in self.data_table.get_children():
                self.data_table.delete(item)
            placeholder = "Активируйте SOURCE двойным кликом."
            self.data_table.insert("", tk.END, values=(placeholder,))
            if notify_user:
                messagebox.showinfo("Таблица истинности", "Активируйте хотя бы один SOURCE.")
            return

        max_sources = 10
        if len(sources) > max_sources:
            if notify_user:
                messagebox.showwarning("Таблица истинности", f"Количество SOURCE превышает ограничение ({max_sources}).")
            self.status_variable.set("Ошибка: слишком много входов.")
            self.data_table.configure(columns=("DATA",))
            self.data_table.heading("DATA", text="Информация")
            self.data_table.column("DATA", width=260, anchor=tk.CENTER, stretch=True)
            for item in self.data_table.get_children():
                self.data_table.delete(item)
            self.data_table.insert("", tk.END, values=("Ограничение: максимум 10 входов.",))
            return

        rows: List[List[str]] = []
        combinations = 1 << len(active_sources)

        try:
            for mask in range(combinations):
                overrides = {
                    id(active_sources[i]): bool((mask >> i) & 1)
                    for i in range(len(active_sources))
                }
                computed_results = self.calculate_nodes(overrides)
                row: List[str] = [
                    str(int(overrides.get(id(src)))) for src in active_sources
                ]
                for term in terminators:
                    val = computed_results.get(id(term))
                    row.append("-" if val is None else str(int(bool(val))))
                rows.append(row)
        except ValueError as e:
            if notify_user:
                messagebox.showerror("Ошибка", str(e))
            self.status_variable.set("Ошибка: ошибка обработки схемы.")
            return

        headers = ([f"SRC_{i+1}" for i in range(len(active_sources))] +
                  [f"TGT_{j+1}" for j in range(len(terminators))])
        self.data_table.configure(columns=headers)
        for header in headers:
            self.data_table.heading(header, text=header)
            self.data_table.column(header, width=90, anchor=tk.CENTER, stretch=True)

        for item in self.data_table.get_children():
            self.data_table.delete(item)

        for row in rows:
            self.data_table.insert("", tk.END, values=row)

        if notify_user:
            self.status_variable.set("Таблица истинности обновлена.")

    def launch_simulator(self) -> None:
        """
        Запускает главное окно приложения.
        """
        self.window.mainloop()

if __name__ == "__main__":
    simulator = SimulatorApp()
    simulator.launch_simulator()