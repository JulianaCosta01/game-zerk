# menu.py: tela do menu principal

import pygame
import math
import sys
import os
import asyncio
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


async def executar_menu(tela):
    """
    Executa o loop do menu principal: eventos, hover dos botões e
    renderização do fundo/título/botões, até o jogador escolher jogar
    ou sair.

    Args:
        tela: pygame.Surface principal (800 x 600)

    Returns:
        bool: True → ir para o jogo, False → encerrar o programa
    """
    relogio = pygame.time.Clock()

    # Fundo do menu
    menu_bg = None
    if os.path.exists(SPRITE_MENU_BG):
        menu_bg = pygame.image.load(SPRITE_MENU_BG).convert()
        menu_bg = pygame.transform.scale(menu_bg, (LARGURA_TELA, ALTURA_TELA))

    # Centro da tela
    cx = LARGURA_TELA // 2
    cy = ALTURA_TELA  // 2

    # Botão JOGAR
    btn_jogar_img = None
    if os.path.exists(SPRITE_BTN_JOGAR):
        btn_jogar_img = pygame.image.load(SPRITE_BTN_JOGAR).convert_alpha()

    # Botão SAIR
    btn_sair_img = None
    if os.path.exists(SPRITE_BTN_SAIR):
        btn_sair_img = pygame.image.load(SPRITE_BTN_SAIR).convert_alpha()

    # Logo do jogo
    titulo_img = None
    if os.path.exists(SPRITE_TITULO):
        titulo_img = pygame.image.load(SPRITE_TITULO).convert_alpha()


    # Dimensões dos botões (devem casar com o tamanho real dos PNGs btn_jogar/btn_sair)
    btn_l, btn_a = 280, 80

    # Posições verticais do layout (título maior no topo, botões do mesmo tamanho abaixo)
    titulo_y     = cy - 215   # topo do título
    btn_jogar_y  = cy - 4     # topo do botão JOGAR
    btn_sair_y   = cy + 96    # topo do botão SAIR

    btn_jogar = Botao(
        cx - btn_l // 2, btn_jogar_y,
        btn_l, btn_a,
        "[ JOGAR ]",
        (0, 210, 140),   # Borda verde normal
        (0, 255, 180)    # Borda verde brilhante ao hover
    )

    btn_sair = Botao(
        cx - btn_l // 2, btn_sair_y,
        btn_l, btn_a,
        "[ SAIR ]",
        (200, 40, 40),   # Borda vermelha normal
        (255, 50, 50)    # Borda vermelha brilhante ao hover
    )

    rodando = True
    while rodando:
        pos_mouse = pygame.mouse.get_pos()

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

        # Se não achar o sprite do fundo, usa o fundo antigo desenhado (grade de pontos)
        if menu_bg:
            tela.blit(menu_bg, (0, 0))
        else:
            tela.fill(COR_PRETO)
            _desenhar_grade_fundo(tela)

        if titulo_img:
            tela.blit(titulo_img, (cx - titulo_img.get_width() // 2, titulo_y))

        # JOGAR (com highlight de hover)
        if btn_jogar_img:
            img = btn_jogar_img.copy()
            if btn_jogar.com_hover:
                img.fill((60, 60, 60), special_flags=pygame.BLEND_RGB_ADD)
            tela.blit(img, (cx - img.get_width() // 2, btn_jogar_y))

        # SAIR (com highlight de hover)
        if btn_sair_img:
            img = btn_sair_img.copy()
            if btn_sair.com_hover:
                img.fill((60, 60, 60), special_flags=pygame.BLEND_RGB_ADD)
            tela.blit(img, (cx - img.get_width() // 2, btn_sair_y))

        pygame.display.flip()
        relogio.tick(60)

        # Cede o controle pro loop de eventos do navegador a cada frame. Necessário pro pygbag (build web); no desktop é um no-op.
        await asyncio.sleep(0)

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
