from constants import COLORS


def draw_text_with_shadow(screen, font, text, pos, color, center=False):
    if not font:
        return

    shadow_surf = font.render(text, True, COLORS['SHADOW'])
    text_surf = font.render(text, True, color)
    if center:
        text_rect = text_surf.get_rect(center=pos)
        shadow_rect = shadow_surf.get_rect(center=(pos[0] + 1, pos[1] + 1))
    else:
        text_rect = text_surf.get_rect(topleft=pos)
        shadow_rect = shadow_surf.get_rect(topleft=(pos[0] + 1, pos[1] + 1))

    screen.blit(shadow_surf, shadow_rect)
    screen.blit(text_surf, text_rect)
