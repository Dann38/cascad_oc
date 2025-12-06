"""
Классы для соединения блоков между собой.
Определяет связи между границами разных блоков.
"""
from typing import Any, Callable, Optional

class BoundaryConnection:
    """Соединение между границами двух блоков"""
    
    def __init__(self, source_block: 'BaseBlock', source_boundary: str,
                 target_block: 'BaseBlock', target_boundary: str):
        self.source_block = source_block
        self.source_boundary = source_boundary
        self.target_block = target_block
        self.target_boundary = target_boundary
        self.ready_until = 0.0  # До какого времени данные готовы
    
    def get_value(self, t: float) -> Any:
        """Получение значения от источника в момент времени t"""
        # В реальной реализации здесь будет обращение к решению source_block
        # Пока заглушка
        return None
    
    def is_ready(self, t: float) -> bool:
        """Проверка готовности данных до времени t"""
        return t <= self.ready_until
    
    def mark_ready(self, until_time: float) -> None:
        """Отметка времени до которого данные готовы"""
        self.ready_until = until_time

class ConnectionManager:
    """Менеджер для управления соединениями между блоками"""
    
    def __init__(self):
        self.connections = []
    
    def connect_blocks(self, source_block: 'BaseBlock', source_boundary: str,
                      target_block: 'BaseBlock', target_boundary: str) -> BoundaryConnection:
        """Создание соединения между блоками"""
        connection = BoundaryConnection(source_block, source_boundary,
                                      target_block, target_boundary)
        self.connections.append(connection)
        
        # Добавляем соединение в целевой блок
        target_block.connect(connection)
        
        return connection
    
    def get_connections_for_block(self, block: 'BaseBlock') -> list:
        """Получение всех соединений для блока"""
        return [conn for conn in self.connections 
                if conn.source_block == block or conn.target_block == block]