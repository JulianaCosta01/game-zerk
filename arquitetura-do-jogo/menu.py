# =============================================================================
# menu.py: Tela do Menu Principal
# =============================================================================


import pygame
import math
import sys
import os
from config import (
    LARGURA_TELA, ALTURA_TELA,
    COR_PRETO, COR_HUD_DESTAQUE, COR_HUD_FRACO,
    COR_VITORIA, COR_DERROTA, SPRITE_MENU_BG, SPRITE_BTN_JOGAR, SPRITE_BTN_SAIR, SPRITE_TITULO
)


class Botao:
    """
    Botão clicável para o menu.
    Detecta quando o mouse passa por cima (hover) e quando é clicado.
    Muda a aparência visual ao interagir.
    """

    def __init__(self, x, y, largura, altura, texto, cor_normal, cor_hover):
        """
        Args:
            x, y          : posição do canto superior esquerdo
            largura, altura: dimensões do botão em pixels
            texto         : texto exibido dentro do botão
            cor_normal    : cor da borda quando o mouse NÃO está em cima
            cor_hover     : cor da borda quando o mouse está em cima
        """
        self.rect       = pygame.Rect(x, y, largura, altura)
        self.texto      = texto
        self.com_hover  = False   # True quando o mouse está sobre o botão

    def atualizar(self, pos_mouse):
        """Verifica se o mouse está sobre o botão (para efeito hover)."""
        self.com_hover = self.rect.collidepoint(pos_mouse)

    def foi_clicado(self, evento):
        """
        Verifica se este botão foi clicado.

        Args:
            evento: pygame.event para verificar

        Returns:
            bool: True se clique esquerdo do mouse dentro do botão
        """
        return (evento.type == pygame.MOUSEBUTTONDOWN and
                evento.button == 1 and
                self.rect.collidepoint(evento.pos))


def executar_menu(tela):
    """
    Executa o loop do menu principal.

    LOOP DO MENU:
      1. Captura eventos (fechar janela, teclas, cliques)
      2. Atualiza estado dos botões (hover)
      3. Renderiza o fundo e os elementos do menu
      4. Controla FPS

    Args:
        tela: pygame.Surface principal (800 x 600)

    Returns:
        bool: True → ir para o jogo, False → encerrar o programa
    """
    relogio = pygame.time.Clock()

    #Carrega a tela do background
    menu_bg = None
    if os.path.exists(SPRITE_MENU_BG):
        menu_bg = pygame.image.load(SPRITE_MENU_BG).convert()
        menu_bg = pygame.transform.scale(menu_bg, (LARGURA_TELA, ALTURA_TELA))
    # Centro da tela
    cx = LARGURA_TELA // 2
    cy = ALTURA_TELA  // 2

    #Botao JOGAR
    btn_jogar_img = None
    if os.path.exists(SPRITE_BTN_JOGAR):
        btn_jogar_img = pygame.image.load(SPRITE_BTN_JOGAR).convert_alpha()

    #Botao SAIR
    btn_sair_img = None
    if os.path.exists(SPRITE_BTN_SAIR):
        btn_sair_img = pygame.image.load(SPRITE_BTN_SAIR).convert_alpha()

    #Logo do Jogo
    titulo_img = None
    if os.path.exists(SPRITE_TITULO):
        titulo_img = pygame.image.load(SPRITE_TITULO).convert_alpha()


    # Dimensões dos botões
    btn_l, btn_a = 220, 50

    # Botao JOGAR, desenhado se arquivo não existir
    btn_jogar = Botao(
        cx - btn_l // 2, cy + 20,
        btn_l, btn_a,
        "[ JOGAR ]",
        (0, 210, 140),   # Borda verde normal
        (0, 255, 180)      # Borda verde brilhante ao hover
    )

    # Botao SAIR, desenhado se arquivo não existir
    btn_sair = Botao(
        cx - btn_l // 2, cy + 90,
        btn_l, btn_a,
        "[ SAIR ]",
        (200, 40, 40),   # Borda vermelha normal
        (255, 50, 50)    # Borda vermelha brilhante ao hover
    )

    #loop
    rodando = True
    while rodando:
        pos_mouse = pygame.mouse.get_pos()

        # Eventos 
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                return False  

            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_RETURN:
                    return True    
                if evento.key == pygame.K_ESCAPE:
                    return False  
            # Clique nos botões
            if btn_jogar.foi_clicado(evento):
                return True
            if btn_sair.foi_clicado(evento):
                return False

        # Atualiza estado de hover dos botões
        btn_jogar.atualizar(pos_mouse)
        btn_sair.atualizar(pos_mouse)

        # Renderização , se não achar arquivo do bg, utiliza bg antigo desenhado (pontos)
        if menu_bg:
            tela.blit(menu_bg, (0, 0))
        else:
            tela.fill(COR_PRETO)
            _desenhar_grade_fundo(tela)

        

        # Título
        if titulo_img:
            tela.blit(titulo_img, (cx - titulo_img.get_width() // 2, cy - 220))
        #JOGAR
        if btn_jogar_img:
            tela.blit(btn_jogar_img, (cx - btn_jogar_img.get_width() // 2, cy + 20))
        #SAIR
        if btn_sair_img:
            tela.blit(btn_sair_img, (cx - btn_sair_img.get_width() // 2, cy + 90))

        #Highlight JOGAR
        if btn_jogar_img:
            img = btn_jogar_img.copy()
            if btn_jogar.com_hover:
                img.fill((60, 60, 60), special_flags=pygame.BLEND_RGB_ADD)
            tela.blit(img, (cx - img.get_width() // 2, cy + 20))

        #Highlight SAIR
        if btn_sair_img:
            img = btn_sair_img.copy()
            if btn_sair.com_hover:
                img.fill((60, 60, 60), special_flags=pygame.BLEND_RGB_ADD)
            tela.blit(img, (cx - img.get_width() // 2, cy + 90))
        

        pygame.display.flip()
        relogio.tick(60)

    return False


def _desenhar_grade_fundo(tela):
    """
    Desenha pontos decorativos em grade no fundo do menu.
    Cada ponto pulsa individualmente criando efeito de "onda".
    """
    cor_ponto    = (15, 25, 50)
    espacamento  = 32
    t            = pygame.time.get_ticks()

    for gx in range(0, LARGURA_TELA + espacamento, espacamento):
        for gy in range(0, ALTURA_TELA + espacamento, espacamento):
            # Pulso com base na posição — cria efeito de onda diagonal
            pulso = math.sin(t * 0.001 + gx * 0.05 + gy * 0.05)
            raio  = 1 if pulso < 0 else 2
            pygame.draw.circle(tela, cor_ponto, (gx, gy), raio)
