# =============================================================================
# hud.py: Interface do Usuário (HUD) e Telas de Início/Fim
# =============================================================================


import pygame
import math
import os
from config import (
    LARGURA_TELA, ALTURA_TELA, LARGURA_MAPA, ALTURA_MAPA,
    COR_HUD_BG, COR_HUD_TEXTO, COR_HUD_FRACO, COR_HUD_DESTAQUE,
    COR_COMBO, COR_INIMIGO, COR_JOGADOR, COR_ZONA_BORDA,
    COR_VITORIA, COR_DERROTA, COR_BRANCO, COR_PRETO, 
    DURACAO_POWERUP
)

class HUD:
    """
    Gerencia e renderiza toda a interface do jogo durante a partida.

    As fontes são criadas UMA ÚNICA VEZ no __init__ para não recriar
    a cada frame (criar fontes é uma operação lenta no Pygame).
    """

    def __init__(self):
        # Fontes monoespaçadas 
        self.fonte_grande  = pygame.font.SysFont("couriernew", 28, bold=True)
        self.fonte_media   = pygame.font.SysFont("couriernew", 20, bold=True)
        self.fonte_pequena = pygame.font.SysFont("couriernew", 15)
        self.fonte_minima  = pygame.font.SysFont("couriernew",  12)

        # Altura da barra superior do HUD
        self.altura_barra = 44


    def desenhar(self, tela, estado_jogo):
        """
        Renderiza todos os elementos do HUD sobre o jogo.

        Args:
            tela       : pygame.Surface principal
            estado_jogo: objeto EstadoJogo com todos os dados da partida
        """
        self._desenhar_barra_superior(tela, estado_jogo)
        self._desenhar_powerups(tela, estado_jogo)
        if estado_jogo.zona.ativa:
            self._desenhar_aviso_zona(tela, estado_jogo)

    
    # BARRA SUPERIOR
    def _desenhar_barra_superior(self, tela, ej):
        """Renderiza a barra de status no topo da tela."""
        # Fundo semi-transparente
        surf_fundo = pygame.Surface((LARGURA_TELA, self.altura_barra), pygame.SRCALPHA)
        surf_fundo.fill((*COR_HUD_BG, 210))
        tela.blit(surf_fundo, (0, 0))

        # Linha divisória na base da barra
        pygame.draw.line(tela, COR_HUD_DESTAQUE,
                         (0, self.altura_barra - 1),
                         (LARGURA_TELA, self.altura_barra - 1), 1)

        # Colunas de posição dos indicadores
        posicoes = [10, 140, 260, 370, 530, 660]

        # Pontuação 
        self._rotulo(tela, "PONTOS",  posicoes[0], 4)
        self._valor(tela, str(ej.pontuacao), posicoes[0], 18)

        # Tempo
        self._rotulo(tela, "TEMPO", posicoes[1], 4)
        m  = int(ej.segundos_decorridos // 60)
        s  = int(ej.segundos_decorridos % 60)
        self._valor(tela, f"{m:02d}:{s:02d}", posicoes[1], 18)

        # Inimigos restantes
        vivos = sum(1 for e in ej.inimigos if e.vivo)
        self._rotulo(tela, "INIMIGOS", posicoes[2], 4)
        self._valor(tela, f"{vivos}/{ej.total_inimigos}", posicoes[2], 18,
                    cor=COR_INIMIGO if vivos > 0 else COR_VITORIA)

        # Barra de progresso (inimigos eliminados)
        self._rotulo(tela, "PROGRESSO", posicoes[3], 4)
        rect_barra = pygame.Rect(posicoes[3], 20, 140, 12)
        pygame.draw.rect(tela, (20, 30, 50), rect_barra, border_radius=3)
        if ej.total_inimigos > 0:
            pct        = (ej.total_inimigos - vivos) / ej.total_inimigos
            rect_fill  = pygame.Rect(posicoes[3], 20, int(140 * pct), 12)
            pygame.draw.rect(tela, self._cor_progresso(pct), rect_fill, border_radius=3)
        pygame.draw.rect(tela, COR_HUD_FRACO, rect_barra, 1, border_radius=3)

        # Multiplicador de combo
        self._rotulo(tela, "COMBO", posicoes[4], 4)
        cor_combo  = COR_COMBO if ej.combo > 1 else COR_HUD_FRACO
        tam_fonte  = 20 if ej.combo > 3 else 16
        fonte_cmb  = pygame.font.SysFont("ocrextended", tam_fonte, bold=True)
        surf_combo = fonte_cmb.render(f"x{ej.combo}", True, cor_combo)
        tela.blit(surf_combo, (posicoes[4], 16))

        # Recorde
        self._rotulo(tela, "RECORDE", posicoes[5], 4)
        self._valor(tela, str(ej.recorde), posicoes[5], 18, cor=COR_HUD_FRACO)

    def _rotulo(self, tela, texto, x, y):
        """Renderiza um rótulo pequeno e discreto."""
        surf = self.fonte_minima.render(texto, True, COR_HUD_FRACO)
        tela.blit(surf, (x, y))

    def _valor(self, tela, texto, x, y, cor=None):
        """Renderiza um valor em destaque."""
        surf = self.fonte_media.render(texto, True, cor or COR_HUD_DESTAQUE)
        tela.blit(surf, (x, y))

    @staticmethod
    def _cor_progresso(pct):
        """Cor da barra de progresso: ciano (início) → verde (completo)."""
        if pct < 0.5:
            return (0, 160 + int(pct * 190), 200)
        return (0, 200, int((1 - pct) * 200))


   
    # INDICADORES DE POWER-UP
    def _desenhar_powerups(self, tela, ej):
        """Renderiza os ícones dos power-ups ativos no canto inferior esquerdo."""
        ativos = [(k, v) for k, v in ej.jogador.powerups.items() if v > 0]
        if not ativos:
            return

        rotulos = {
            "velocidade": "VEL",
            "duplo":      "DBL",
            "escudo":     "ESC",
            "congelar":   "FRZ"
        }
        cores = {
            "velocidade": (255, 221,  68),
            "duplo":      (255, 107,  53),
            "escudo":     (  0, 212, 255),
            "congelar":   (136, 238, 255),
        }

        base_y = ALTURA_TELA - 28
        for i, (tipo, restante) in enumerate(ativos):
            x   = 8 + i * 54
            cor = cores.get(tipo, COR_HUD_DESTAQUE)

            # Caixa de fundo semi-transparente
            caixa = pygame.Surface((50, 22), pygame.SRCALPHA)
            caixa.fill((*COR_HUD_BG, 200))
            tela.blit(caixa, (x, base_y))
            pygame.draw.rect(tela, cor, (x, base_y, 50, 22), 1)

            # Rótulo do power-up
            lbl = self.fonte_minima.render(rotulos.get(tipo, "???"), True, cor)
            tela.blit(lbl, (x + 3, base_y + 2))

            # Barra de duração restante
            pct = restante / DURACAO_POWERUP
            pygame.draw.rect(tela, (20, 30, 50), (x + 2, base_y + 14, 46, 5))
            pygame.draw.rect(tela, cor, (x + 2, base_y + 14, int(46 * pct), 5))

    
    # AVISO DE ZONA
    def _desenhar_aviso_zona(self, tela, ej):
        """Exibe aviso pulsante quando a zona vermelha está avançando."""
        if ej.zona.margem < 30:
            return
        pulso      = abs(math.sin(pygame.time.get_ticks() * 0.004))
        alpha      = int(100 + 155 * pulso)
        surf_texto = self.fonte_media.render("⚠ ZONA FECHANDO", True, COR_ZONA_BORDA)
        surf_aviso = pygame.Surface(surf_texto.get_size(), pygame.SRCALPHA)
        surf_aviso.blit(surf_texto, (0, 0))
        surf_aviso.set_alpha(alpha)
        x = (LARGURA_TELA - surf_texto.get_width()) // 2
        tela.blit(surf_aviso, (x, self.altura_barra + 4))

    
    # MINI-RADAR
    def _desenhar_radar(self, tela, ej):
        """
        Mini-radar no canto inferior direito da tela.
        Mostra posição do jogador (ciano) e inimigos (vermelho) no mapa.

        ESCALA:
        escala_x = tamanho_radar / largura_mapa
        posicao_no_radar = posicao_no_mapa × escala
        """
        rx, ry = self.radar_x, self.radar_y
        rs     = self.tamanho_radar

        # Fundo do radar
        surf_radar = pygame.Surface((rs, rs), pygame.SRCALPHA)
        surf_radar.fill((*COR_HUD_BG, 200))
        pygame.draw.circle(surf_radar, COR_HUD_FRACO, (rs // 2, rs // 2), rs // 2, 1)

        # Fator de escala: converte posição no mapa para posição no radar
        escala_x = rs / LARGURA_MAPA
        escala_y = rs / ALTURA_MAPA

        # Zona vermelha no radar (retângulo vermelho)
        if ej.zona.margem > 0:
            m  = ej.zona.margem
            zx = int(m * escala_x)
            zy = int(m * escala_y)
            zl = int((LARGURA_MAPA - m * 2) * escala_x)
            za = int((ALTURA_MAPA  - m * 2) * escala_y)
            pygame.draw.rect(surf_radar, (180, 30, 30, 120), (zx, zy, zl, za))
            pygame.draw.rect(surf_radar, (*COR_ZONA_BORDA, 200), (zx, zy, zl, za), 1)

        # Inimigos vivos (pontos vermelhos)
        for inimigo in ej.inimigos:
            if not inimigo.vivo:
                continue
            ex = int(inimigo.x * escala_x)
            ey = int(inimigo.y * escala_y)
            pygame.draw.circle(surf_radar, COR_INIMIGO, (ex, ey), 2)

        # Jogador (ponto ciano maior)
        px = int(ej.jogador.x * escala_x)
        py = int(ej.jogador.y * escala_y)
        pygame.draw.circle(surf_radar, COR_JOGADOR, (px, py), 3)
        pygame.draw.circle(surf_radar, COR_BRANCO,  (px, py), 1)

        tela.blit(surf_radar, (rx, ry))
        pygame.draw.rect(tela, COR_HUD_FRACO, (rx - 1, ry - 1, rs + 2, rs + 2), 1)

        # Label "RADAR"
        lbl = self.fonte_minima.render("RADAR", True, COR_HUD_FRACO)
        tela.blit(lbl, (rx + rs // 2 - lbl.get_width() // 2, ry - 13))



_controls_img = None
_menu_bg       = None
#TELA ANTES DA PARTIDA
#Renderiza controls.png e aguarda ENTER.
def desenhar_tela_inicial(tela):
    global _controls_img, _menu_bg

    # Carregar controls.png uma vez
    if _controls_img is None:
        from config import SPRITE_CONTROLS
        if os.path.exists(SPRITE_CONTROLS):
            _controls_img = pygame.image.load(SPRITE_CONTROLS).convert()
            _controls_img = pygame.transform.scale(_controls_img, (LARGURA_TELA, ALTURA_TELA))

    # quickhaxs = control.png eh um background
    if _controls_img:
        tela.blit(_controls_img, (0, 0))
    else:
        tela.fill(COR_PRETO)

    # IMPUT ENTER
    fonte_sub  = pygame.font.SysFont("ocraextended", 16)
    pulso      = abs(math.sin(pygame.time.get_ticks() * 0.002))
    cor_inicio = tuple(int(c + (255 - c) * pulso) for c in COR_HUD_DESTAQUE)
    inicio     = fonte_sub.render("[ ENTER ] para iniciar", True, cor_inicio)
    tela.blit(inicio, ((LARGURA_TELA - inicio.get_width()) // 2, ALTURA_TELA - 100))



# TELA DE FIM — exibida ao vencer ou perder
def desenhar_tela_fim(tela, fonte_grande, fonte_media, fonte_pequena,
                      vitoria, pontuacao, recorde, segundos,
                      eliminacoes, total, precisao, numero_sessao):
    """
    Renderiza o overlay de fim de jogo com estatísticas da partida.

    Args:
        tela          : pygame.Surface principal
        fonte_*       : fontes pré-carregadas do HUD
        vitoria       : True = vitória, False = derrota
        pontuacao     : pontuação final da partida
        recorde       : maior pontuação já registrada
        segundos      : duração da partida em segundos
        eliminacoes   : número de inimigos eliminados
        total         : número total de inimigos da partida
        precisao      : percentual de acerto dos disparos
        numero_sessao : número da sessão atual (conta partidas)
    """
    # Overlay escuro cobrindo toda a tela
    overlay = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)
    overlay.fill((5, 8, 16, 220))
    tela.blit(overlay, (0, 0))

    # Painel central de resultados
    painel_l, painel_a = 420, 320
    painel_x = (LARGURA_TELA - painel_l) // 2
    painel_y = (ALTURA_TELA  - painel_a) // 2

    surf_painel = pygame.Surface((painel_l, painel_a), pygame.SRCALPHA)
    surf_painel.fill((10, 16, 32, 240))
    tela.blit(surf_painel, (painel_x, painel_y))

    # Borda colorida conforme resultado
    cor_acento = COR_VITORIA if vitoria else COR_DERROTA
    pygame.draw.rect(tela, cor_acento, (painel_x, painel_y, painel_l, painel_a), 2)

    # Título do resultado
    fonte_titulo  = pygame.font.SysFont("ocrextended", 28, bold=True)
    texto_titulo  = "VOCÊ VENCEU!" if vitoria else "VOCÊ PERDEU!"
    surf_titulo   = fonte_titulo.render(texto_titulo, True, cor_acento)
    tela.blit(surf_titulo,
              (painel_x + (painel_l - surf_titulo.get_width()) // 2, painel_y + 20))

    # Subtítulo descritivo
    fonte_sub   = pygame.font.SysFont("ocrextended", 20)
    texto_sub   = "Todos os robôs foram eliminados!" if vitoria else "VOCÊ foi eliminado!"
    surf_sub    = fonte_sub.render(texto_sub, True, (255, 255, 255))
    tela.blit(surf_sub,
              (painel_x + (painel_l - surf_sub.get_width()) // 2, painel_y + 56))

    # Linha separadora
    pygame.draw.line(tela, (30, 50, 90),
                     (painel_x + 20, painel_y + 74),
                     (painel_x + painel_l - 20, painel_y + 74), 1)

    # Estatísticas da partida
    m  = int(segundos // 60)
    s  = int(segundos % 60)
    estatisticas = [
        ("TEMPO",        f"{m:02d}:{s:02d}"),
        ("PONTUAÇÃO",    str(pontuacao)),
        ("ELIMINAÇÕES",  f"{eliminacoes}/{total}"),
        ("PRECISÃO",     f"{precisao}%"),
        ("RECORDE",      str(recorde)),
        ("SESSÃO Nº",    str(numero_sessao)),
    ]

    fonte_valor  = pygame.font.SysFont("ocrextended", 13, bold=True)
    fonte_rotulo = pygame.font.SysFont("ocrextended", 11)
    inicio_y     = painel_y + 88

    for i, (rotulo, valor) in enumerate(estatisticas):
        linha_y   = inicio_y + i * 28
        col_rot_x = painel_x + 30
        col_val_x = painel_x + painel_l - 30

        surf_rot = fonte_rotulo.render(rotulo, True, COR_HUD_FRACO)
        surf_val = fonte_valor.render(valor, True, COR_HUD_DESTAQUE)

        tela.blit(surf_rot, (col_rot_x, linha_y))
        tela.blit(surf_val, (col_val_x - surf_val.get_width(), linha_y))

        # Linha pontilhada entre rótulo e valor
        x_inicio_pts = col_rot_x + surf_rot.get_width() + 6
        x_fim_pts    = col_val_x - surf_val.get_width() - 6
        for dot_x in range(x_inicio_pts, x_fim_pts, 6):
            pygame.draw.circle(tela, (30, 50, 80), (dot_x, linha_y + 7), 1)

    # Instrução para continuar
    fonte_inst = pygame.font.SysFont("ocrextended", 12, bold=True)
    surf_inst  = fonte_inst.render("[ENTER] Jogar Novamente", True, COR_HUD_FRACO)
    tela.blit(surf_inst,
              (painel_x + (painel_l - surf_inst.get_width()) // 2,
               painel_y + painel_a - 28))
