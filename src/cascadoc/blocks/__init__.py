"""
Пакет блоков для каскадных систем.
Содержит базовые классы и реализации различных типов блоков.
"""
from cascadoc.blocks.base_block import BaseBlock
from cascadoc.blocks.concentrated_blocks.base_concentrated_block import BaseConcentratedBlock
from cascadoc.blocks.distributed_blocks.base_distributed_block import BaseDistributedBlock

__all__ = ['BaseBlock', 'BaseConcentratedBlock', 'BaseDistributedBlock']