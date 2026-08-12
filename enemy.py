# enemy.py: impostores (inimigos)

import pygame
import os
import math
import random
from config import (
    TAMANHO_INIMIGO, COR_INIMIGO, COR_NUCLEO_INIMIGO, COR_BRILHO_INIMIGO,
    PASTA_ENEMY, ENEMY_IDLE_FRAMES, ENEMY_WALK_FRAMES,
    LARGURA_MAPA, ALTURA_MAPA,
)
from tilemap import Labirinto

# Intervalo entre mudanças aleatórias de direção (~800ms)
INTERVALO_MUDANCA_DIRECAO = 800

# Cooldown mínimo após colidir (evita troca de direção muito rápida)
COOLDOWN_COLISAO = 150


class Inimigo:
    """
    Impostor — entidade inimiga que patrulha o labirinto.

    Contato com o jogador → game over imediato.
    Contato com a zona vermelha → inimigo morre.

    Atributos:
        x, y   → posição do centro em pixels
        vel    → velocidade em pixels por frame
        vivo   → False quando eliminado por projétil ou zona
    """

    def __init__(self, coluna, linha, velocidade, alcance=150, agressividade=0.1):
        """
        Inicializa o inimigo no centro do tile especificado.

        Args:
            coluna        (int)  : coluna de spawn no mapa
            linha         (int)  : linha de spawn no mapa
            velocidade    (float): velocidade em pixels por frame
            alcance       (int)  : reservado para uma futura IA de perseguição (ainda não usado)
            agressividade (float): reservado para uma futura IA de perseguição (ainda não usado)
        """
        self.x, self.y = Labirinto.tile_para_pixel_centro(coluna, linha)
        self.vel       = velocidade
        self.tamanho   = TAMANHO_INIMIGO
        self.vivo      = True
        self.alcance       = alcance
        self.agressividade = agressividade

        # Direção atual como vetor unitário, em ângulo aleatório para cada inimigo ser diferente
        angulo_inicial = random.uniform(0, 2 * math.pi)
        self.dir_x = math.cos(angulo_inicial)
        self.dir_y = math.sin(angulo_inicial)

        # Animação de sprite
        self.frame_atual   = 0
        self.timer_frame   = 0
        self.frame_duracao_idle = 400  # ms por frame parado
        self.frame_duracao_walk = 150  # ms por frame andando
        self.em_movimento = True

        self.frames_idle = []
        for i in range(ENEMY_IDLE_FRAMES):
            path = os.path.join(PASTA_ENEMY, f"enemy_idle_{i}.png")
            if os.path.exists(path):
                self.frames_idle.append(pygame.image.load(path).convert_alpha())

        self.frames_walk = []
        for i in range(ENEMY_WALK_FRAMES):
            path = os.path.join(PASTA_ENEMY,f"enemy_walk_{i}.png")
            if os.path.exists(path):
                self.frames_walk.append(pygame.image.load(path).convert_alpha())


        # Contadores de movimentação aleatória
        self.tempo_desde_mudanca = 0    # ms desde a última mudança de direção
        self.cooldown_colisao    = 0    # ms restantes do cooldown pós-colisão

        # Efeitos visuais: cada inimigo tem fase de animação diferente
        self.offset_flutuacao = random.uniform(0, math.pi * 2)
        self.timer_flutuacao  = 0.0

        # Variação de cor individual: impostores têm tons ligeiramente diferentes
        variacao = random.randint(-20, 20)
        self.cor = (
            min(255, max(0, COR_INIMIGO[0] + variacao)),
            min(255, max(0, COR_INIMIGO[1] + variacao // 4)),
            min(255, max(0, COR_INIMIGO[2] + variacao // 4)),
        )

    # ATUALIZAÇÃO
    def atualizar(self, dt, margem_zona, congelado, labirinto):
        """
        Atualiza posição e estado do inimigo a cada frame: movimento
        aleatório com chance de trocar de direção, colisão com o
        labirinto e verificação de morte pela zona vermelha.

        Args:
            dt          (float): delta time em ms
            margem_zona (float): espessura atual da zona vermelha em pixels
            congelado   (bool) : True se power-up freeze está ativo
        """
        if not self.vivo:
            return

        # Flutuação visual continua mesmo congelado
        self.timer_flutuacao += dt * 0.003
        self.em_movimento = not congelado

        # Congelado (power-up freeze): não se move nem muda de direção
        if congelado:
            return

        # Decrementa timers de movimentação aleatória
        self.tempo_desde_mudanca += dt
        if self.cooldown_colisao > 0:
            self.cooldown_colisao -= dt

        # Mudança espontânea de direção a cada ~800ms (35% de chance)
        if self.tempo_desde_mudanca >= INTERVALO_MUDANCA_DIRECAO:
            self.tempo_desde_mudanca = 0
            if random.random() < 0.35:
                self._escolher_direcao_livre(labirinto)

        # Tenta mover na direção atual
        distancia_percorrida = self._tentar_mover(labirinto)

        # Se ficou preso (colisão ou canto), escolhe uma nova direção livre
        quase_travado = distancia_percorrida < self.vel * 0.25
        if quase_travado and self.cooldown_colisao <= 0:
            self._escolher_direcao_livre(labirinto)
            self.cooldown_colisao = COOLDOWN_COLISAO

        # Verifica morte pela zona vermelha
        if self._esta_na_zona(margem_zona):
            self.vivo = False

        # Avança a animação de sprite
        self.timer_frame += dt
        frames_ativos = self.frames_walk if self.em_movimento else self.frames_idle
        frame_duracao = self.frame_duracao_walk if self.em_movimento else self.frame_duracao_idle
        if frames_ativos and self.timer_frame >= frame_duracao:
            self.timer_frame = 0
            self.frame_atual = (self.frame_atual + 1) % len(frames_ativos)

    def _tentar_mover(self, labirinto):
        """
        Tenta mover na direção atual com técnica de deslize.

        Igual ao jogador: tenta X+Y juntos, depois só X, depois só Y.
        Retorna a distância real percorrida no frame.

        Returns:
            float: distância percorrida no frame (0 se travou completamente)
        """
        mov_x = self.dir_x * self.vel
        mov_y = self.dir_y * self.vel

        # Tentativa combinada (X e Y juntos)
        novo_x, novo_y = self.x + mov_x, self.y + mov_y
        if not labirinto.circulo_colide_parede(novo_x, novo_y, self.tamanho):
            self.x, self.y = novo_x, novo_y
            return self.vel

        # Deslize horizontal (só X)
        x_antes, y_antes = self.x, self.y
        novo_x = self.x + mov_x
        if not labirinto.circulo_colide_parede(novo_x, self.y, self.tamanho):
            self.x  = novo_x

        # Deslize vertical (só Y)
        novo_y = self.y + mov_y
        if not labirinto.circulo_colide_parede(self.x, novo_y, self.tamanho):
            self.y  = novo_y

        return math.hypot(self.x - x_antes, self.y - y_antes)

    def _escolher_direcao_livre(self, labirinto):
        """
        Escolhe uma nova direção de movimento livre de colisão.

        Testa 8 direções espaçadas em 360° e escolhe aleatoriamente
        entre as que não colidem. Se nenhuma estiver livre (canto
        fechado), recua em direção ao centro do tile atual.
        """
        # 8 direções candidatas, espaçadas a cada 45° com um pouco de ruído
        direcoes_candidatas = []
        for i in range(8):
            angulo = (2 * math.pi / 8) * i + random.uniform(-0.2, 0.2)
            direcoes_candidatas.append((math.cos(angulo), math.sin(angulo)))

        # Embaralha para não ter preferência por nenhuma direção específica
        random.shuffle(direcoes_candidatas)

        # Filtra candidatas que têm caminho livre à frente
        direcoes_livres = []
        passo_teste = self.vel * 3   # Testa alguns pixels à frente
        for dx, dy in direcoes_candidatas:
            teste_x = self.x + dx * passo_teste
            teste_y = self.y + dy * passo_teste
            if not labirinto.circulo_colide_parede(teste_x, teste_y, self.tamanho):
                direcoes_livres.append((dx, dy))

        if direcoes_livres:
            self.dir_x, self.dir_y = random.choice(direcoes_livres)
        else:
            # Preso em todos os lados: recua em direção ao centro do tile
            col, lin = Labirinto.pixel_para_tile(self.x, self.y)
            centro_x, centro_y = Labirinto.tile_para_pixel_centro(col, lin)
            dx = centro_x - self.x
            dy = centro_y - self.y
            dist = math.hypot(dx, dy)
            if dist > 0:
                self.dir_x = dx / dist
                self.dir_y = dy / dist
            else:
                # Último recurso: direção completamente aleatória
                angulo = random.uniform(0, 2 * math.pi)
                self.dir_x = math.cos(angulo)
                self.dir_y = math.sin(angulo)

        self.tempo_desde_mudanca = 0

    def _esta_na_zona(self, margem_zona):
        """
        Verifica se o inimigo entrou na zona vermelha (deve morrer).

        A área segura é o retângulo central do mapa.
        Tudo fora desse retângulo é zona perigosa.

        Returns:
            bool: True se o inimigo está na zona → morre
        """
        if margem_zona <= 0:
            return False
        return (
            self.x < margem_zona + self.tamanho or
            self.x > LARGURA_MAPA - margem_zona - self.tamanho or
            self.y < margem_zona + self.tamanho or
            self.y > ALTURA_MAPA  - margem_zona - self.tamanho
        )

    def colide_com_jogador(self, jog_x, jog_y, jog_tamanho):
        """
        Verifica colisão circular com o jogador.

        COLISÃO CIRCULAR:
        Dois círculos colidem quando a distância entre seus centros
        é menor que a soma de seus raios.
        Usamos dist² para evitar calcular raiz quadrada (mais eficiente).

        Returns:
            bool: True se o inimigo tocou o jogador
        """
        dx = self.x - jog_x
        dy = self.y - jog_y
        dist_minima = self.tamanho + jog_tamanho
        return dx * dx + dy * dy < dist_minima * dist_minima

    def colide_com_projetil(self, px, py):
        """
        Verifica se um projétil acertou este inimigo.

        Args:
            px, py (float): posição do projétil em pixels

        Returns:
            bool: True se o projétil acertou
        """
        dx = self.x - px
        dy = self.y - py
        return dx * dx + dy * dy < (self.tamanho + 3) ** 2   # +3 = raio do projétil

    def acertar(self):
        """Marca o inimigo como morto (atingido por projétil)."""
        self.vivo = False


    # RENDERIZAÇÃO
    def desenhar(self, tela):
        """
        Desenha o sprite do inimigo (se houver) ou, como fallback, uma
        estrela de 8 pontas com brilho neon. Flutua suavemente com
        uma animação senoidal.
        """
        if not self.vivo:
            return

        flutuacao_y = math.sin(self.timer_flutuacao + self.offset_flutuacao) * 2.0
        cx = int(self.x)
        cy = int(self.y + flutuacao_y)

        frames_ativos = self.frames_walk if self.em_movimento else self.frames_idle
        if frames_ativos:
            frame_idx = self.frame_atual % len(frames_ativos)
            frame     = frames_ativos[frame_idx]
            rect      = frame.get_rect(center=(cx, cy))
            tela.blit(frame, rect)
        else:
            # Sem sprite: desenha a estrela neon
            raio_ext       = self.tamanho
            raio_int       = int(self.tamanho * 0.5)
            num_pontas     = 8
            pontos_estrela = []
            for i in range(num_pontas * 2):
                angulo = (i * math.pi / num_pontas) - math.pi / 2
                raio   = raio_ext if i % 2 == 0 else raio_int
                pontos_estrela.append((
                    cx + math.cos(angulo) * raio,
                    cy + math.sin(angulo) * raio
                ))

            raio_glow = self.tamanho + 6
            surf_glow = pygame.Surface((raio_glow * 2, raio_glow * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf_glow, (*COR_BRILHO_INIMIGO, 50),
                               (raio_glow, raio_glow), raio_glow)
            tela.blit(surf_glow, (cx - raio_glow, cy - raio_glow))

            pygame.draw.polygon(tela, self.cor, pontos_estrela)
            pygame.draw.polygon(tela, COR_BRILHO_INIMIGO, pontos_estrela, 1)

            pygame.draw.circle(tela, COR_NUCLEO_INIMIGO, (cx, cy), 3)
            pygame.draw.circle(
                tela, (80, 0, 0),
                (cx + int(self.dir_x * 2), cy + int(self.dir_y * 2)),
                1
            )