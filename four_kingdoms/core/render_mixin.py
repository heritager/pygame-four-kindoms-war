"""Compatibility shim for older imports."""

from ..ui.renderer import Renderer

RenderMixin = Renderer

__all__ = ['Renderer', 'RenderMixin']
