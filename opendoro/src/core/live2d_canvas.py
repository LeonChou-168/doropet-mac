from typing import Callable

import numpy as np
import OpenGL.GL as GL
from live2d.utils.opengl_functions import create_canvas_framebuffer, create_program


class CompatibleCanvas:
    """OpenGL 2.1 compatible Live2D opacity canvas."""

    def __init__(self):
        self._canvas_opacity = 1.0
        self._canvas_framebuffer = 0
        self._canvas_texture = 0
        self._width = 0
        self._height = 0
        self._create_program()
        self._create_buffers()

    def _create_program(self):
        vertex_shader = """#version 120
        attribute vec2 a_position;
        attribute vec2 a_texCoord;
        varying vec2 v_texCoord;
        void main() {
            gl_Position = vec4(a_position, 0.0, 1.0);
            v_texCoord = a_texCoord;
        }
        """
        frag_shader = """#version 120
        varying vec2 v_texCoord;
        uniform sampler2D canvas;
        uniform float opacity;
        void main() {
            vec4 color = texture2D(canvas, v_texCoord);
            color.rgb *= color.a;
            color *= opacity;
            gl_FragColor = color;
        }
        """
        self._program = create_program(vertex_shader, frag_shader)
        self._position_loc = GL.glGetAttribLocation(self._program, "a_position")
        self._tex_coord_loc = GL.glGetAttribLocation(self._program, "a_texCoord")
        self._opacity_loc = GL.glGetUniformLocation(self._program, "opacity")
        self._canvas_loc = GL.glGetUniformLocation(self._program, "canvas")

    def _create_buffers(self):
        self._vertices = np.array([
            -1, 1,
            -1, -1,
            1, -1,
            -1, 1,
            1, -1,
            1, 1,
        ], dtype=np.float32)
        self._uvs = np.array([
            0, 1,
            0, 0,
            1, 0,
            0, 1,
            1, 0,
            1, 1,
        ], dtype=np.float32)
        self._vertex_vbo = GL.glGenBuffers(1)
        self._uv_vbo = GL.glGenBuffers(1)

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._vertex_vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self._vertices.nbytes, self._vertices, GL.GL_STATIC_DRAW)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._uv_vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self._uvs.nbytes, self._uvs, GL.GL_STATIC_DRAW)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

    def SetSize(self, true_width, true_height):
        self._width = max(1, int(true_width))
        self._height = max(1, int(true_height))
        self._create_canvas_framebuffer()

    def _create_canvas_framebuffer(self):
        if self._canvas_framebuffer:
            GL.glDeleteFramebuffers(1, np.array([self._canvas_framebuffer], dtype=np.uint32))
        if self._canvas_texture:
            GL.glDeleteTextures(1, np.array([self._canvas_texture], dtype=np.uint32))
        self._canvas_framebuffer, self._canvas_texture = create_canvas_framebuffer(self._width, self._height)

    def _draw_on_canvas(self, on_draw):
        old_fbo = GL.glGetIntegerv(GL.GL_FRAMEBUFFER_BINDING)
        old_viewport = GL.glGetIntegerv(GL.GL_VIEWPORT)

        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self._canvas_framebuffer)
        GL.glViewport(0, 0, self._width, self._height)
        on_draw()

        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, int(old_fbo))
        GL.glViewport(*[int(v) for v in old_viewport])

    def Draw(self, on_draw: Callable[[], None]):
        if not self._canvas_framebuffer:
            on_draw()
            return

        self._draw_on_canvas(on_draw)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_ONE, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glUseProgram(self._program)
        GL.glUniform1f(self._opacity_loc, self._canvas_opacity)
        GL.glUniform1i(self._canvas_loc, 0)

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._vertex_vbo)
        GL.glVertexAttribPointer(self._position_loc, 2, GL.GL_FLOAT, False, 0, None)
        GL.glEnableVertexAttribArray(self._position_loc)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._uv_vbo)
        GL.glVertexAttribPointer(self._tex_coord_loc, 2, GL.GL_FLOAT, False, 0, None)
        GL.glEnableVertexAttribArray(self._tex_coord_loc)

        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self._canvas_texture)
        GL.glClearColor(0, 0, 0, 0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, 6)

        GL.glDisableVertexAttribArray(self._position_loc)
        GL.glDisableVertexAttribArray(self._tex_coord_loc)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
        GL.glUseProgram(0)

    def SetOutputOpacity(self, value):
        self._canvas_opacity = max(0.0, min(1.0, float(value)))
