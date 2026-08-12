# =============================================================================
# door.py: Portas automáticas dos laboratórios
# =============================================================================
'''
# ANIMAÇÃO:
    # A porta é composta por dois painéis (metade superior/esquerda e metade
    # inferior/direita, dependendo da orientação) que deslizam para dentro das
    # paredes adjacentes. 'abertura' vai de 0.0 (fechada) a 1.0 (totalmente
    # aberta), interpolando suavemente a cada frame.
'''

import pygame
from config import (
    TAMANHO_TILE, RAIO_ATIVACAO_PORTA, VELOCIDADE_PORTA
)


# Cores dos painéis da porta — tons de metal claro com faixa de alerta,
COR_PAINEL_PORTA   = (170, 180, 200)   # Painel metálico claro
COR_FAIXA_ALERTA   = (255, 180, 40)    # Faixa amarela de aviso
COR_TRILHO_PORTA   = ( 60,  70,  95)   # Trilho/vão por onde a porta desliza
COR_SOMBRA_PORTA   = (110, 118, 138)   # Sombra sutil na borda interna do painel (profundidade)


class PortaAutomatica:
    """
    Porta automática que abre quando uma entidade se aproxima.

    Atributos:
        coluna, linha (int)  : posição do tile da porta no mapa
        orientacao    (str)  : "vertical" (corredor vertical) ou
                                "horizontal" (corredor horizontal) —
                                define a direção em que os painéis deslizam
        abertura      (float): 0.0 = fechada, 1.0 = totalmente aberta
    """

    def __init__(self, coluna, linha, orientacao):
        """
        Args:
            coluna, linha (int): posição do tile no LAYOUT_MAPA
            orientacao    (str): "vertical" ou "horizontal"
        """
        self.coluna     = coluna
        self.linha      = linha
        self.orientacao = orientacao
        self.abertura   = 0.0   # Começa fechada

        # Centro do tile em pixels — usado para medir distância de entidades
        self.x = coluna * TAMANHO_TILE + TAMANHO_TILE / 2
        self.y = linha  * TAMANHO_TILE + TAMANHO_TILE / 2

    def atualizar(self, posicoes_entidades):
        """
        Atualiza o estado de abertura da porta.

        A porta abre se QUALQUER entidade (jogador ou inimigo vivo) estiver
        a menos de RAIO_ATIVACAO_PORTA pixels do seu centro. Caso contrário,
        fecha gradualmente.

        Args:
            posicoes_entidades (list[tuple]): lista de (x, y) de todas as
                entidades relevantes (jogador + inimigos vivos)
        """
        alguem_perto = False
        for (ex, ey) in posicoes_entidades:
            dx = ex - self.x
            dy = ey - self.y
            if (dx * dx + dy * dy) <= RAIO_ATIVACAO_PORTA * RAIO_ATIVACAO_PORTA:
                alguem_perto = True
                break

        alvo = 1.0 if alguem_perto else 0.0

        # Interpolação suave em direção ao alvo (abre/fecha gradualmente)
        if self.abertura < alvo:
            self.abertura = min(alvo, self.abertura + VELOCIDADE_PORTA)
        elif self.abertura > alvo:
            self.abertura = max(alvo, self.abertura - VELOCIDADE_PORTA)

    def desenhar(self, tela):
        """
        Renderiza a porta como dois painéis que deslizam para abrir.

        Orientação "vertical" (corredor vertical, paredes à esquerda/direita):
            os painéis deslizam HORIZONTALMENTE para dentro das paredes.

        Orientação "horizontal" (corredor horizontal, paredes acima/abaixo):
            os painéis deslizam VERTICALMENTE para dentro das paredes.
        """
        x = self.coluna * TAMANHO_TILE
        y = self.linha  * TAMANHO_TILE
        t = TAMANHO_TILE
        metade = t // 2

        # Desenha o "trilho" de fundo (vão por onde a porta corre)
        pygame.draw.rect(tela, COR_TRILHO_PORTA, (x, y, t, t))

        deslocamento = int(metade * self.abertura)

        if self.orientacao == "vertical":
            # Painel esquerdo desliza para a esquerda; painel direito para a direita
            self._desenhar_painel(tela, x - deslocamento, y, metade, t, faixa_vertical=True)
            self._desenhar_painel(tela, x + metade + deslocamento, y, metade, t, faixa_vertical=True)
        else:
            # Painel superior desliza para cima; painel inferior para baixo
            self._desenhar_painel(tela, x, y - deslocamento, t, metade, faixa_vertical=False)
            self._desenhar_painel(tela, x, y + metade + deslocamento, t, metade, faixa_vertical=False)

    @staticmethod
    def _desenhar_painel(tela, x, y, largura, altura, faixa_vertical):
        """Desenha um painel da porta com faixa de alerta amarela na borda
        e uma sombra sutil na borda interna (lado do vão), dando sensação
        de espessura/profundidade ao painel."""
        pygame.draw.rect(tela, COR_PAINEL_PORTA, (x, y, largura, altura))

        # Faixa de alerta fina na borda externa do painel
        espessura = 3
        if faixa_vertical:
            pygame.draw.rect(tela, COR_FAIXA_ALERTA, (x, y, espessura, altura))
            # Sombra na borda interna (lado do vão central)
            sombra_x = x + largura - 2
            pygame.draw.rect(tela, COR_SOMBRA_PORTA, (sombra_x, y, 2, altura))
        else:
            pygame.draw.rect(tela, COR_FAIXA_ALERTA, (x, y, largura, espessura))
            sombra_y = y + altura - 2
            pygame.draw.rect(tela, COR_SOMBRA_PORTA, (x, sombra_y, largura, 2))
