"""Configuración base de pytest para mcp_dev_network."""

import os
import sys
from hypothesis import settings

# Asegurar que el paquete raíz es importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Perfil hypothesis para este proyecto: 200 ejemplos por propiedad
settings.register_profile("mcp-dev-network", max_examples=200)
settings.load_profile("mcp-dev-network")
