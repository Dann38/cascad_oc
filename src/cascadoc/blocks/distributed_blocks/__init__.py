"""
Пакет распределенных блоков (гиперболические, параболические уравнения).
"""
from cascadoc.blocks.distributed_blocks.base_distributed_block import BaseDistributedBlock
from cascadoc.blocks.distributed_blocks.hyperbolic_block import HyperbolicBlock
from cascadoc.blocks.distributed_blocks.hyperbolic_helpers import (
    create_linear_hyperbolic_system,
    create_wave_equation,
    create_transport_equation,
    add_boundary_conditions,
    add_initial_conditions
)

__all__ = [
    'BaseDistributedBlock',
    'HyperbolicBlock',
    'create_linear_hyperbolic_system',
    'create_wave_equation',
    'create_transport_equation',
    'add_boundary_conditions',
    'add_initial_conditions'
]