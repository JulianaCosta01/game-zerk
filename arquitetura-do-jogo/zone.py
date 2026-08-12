# =============================================================================
# zone.py: Zona Vermelha, Partículas e Itens Especiais
# =============================================================================


import pygame
import math
import random
from config import (
    LARGURA_MAPA, ALTURA_MAPA,
    VELOCIDADE_ZONA, ESPESSURA_ZONA,
    TEMPO_ATIVAR_ZONA, INIMIGOS_ATIVAR_ZONA,
    COR_ZONA_FILL, COR_ZONA_BORDA
)
from tilemap import Labirinto

class ZonaVermelha:
    """
    Gerencia a zona de fechamento que avança pelo mapa.

    Quanto maior a 'margem', menor a área segura.
    O jogador e inimigos morrem ao entrar na zona.

    Atributos:
        margem (float): espessura atual da zona em pixels
        ativa  (bool) : True quando a zona começa a avançar
        pulso  (float): fase da animação de pulsação visual
    """

    def __init__(self):
        self.margem = 0.0    # Começa sem zona
        self.ativa  = False  # Ainda não iniciou o fechamento
        self.pulso  = 0.0    # Controla a pulsação visual

    def atualizar(self, dt, segundos_decorridos, inimigos_vivos, congelada):
        """
        Atualiza o estado da zona a cada frame.

        CONDIÇÕES DE ATIVAÇÃO (qualquer uma):
          1. segundos_decorridos >= TEMPO_ATIVAR_ZONA (tempo limite)
          2. inimigos_vivos > 0 e <= INIMIGOS_ATIVAR_ZONA (poucos inimigos)

        Args:
            dt                  (float): delta time em ms
            segundos_decorridos (float): tempo de partida em segundos
            inimigos_vivos      (int)  : quantidade de inimigos ainda vivos
            congelada           (bool) : True se power-up freeze está ativo
        """
        # Verifica se deve ativar a zona
        if not self.ativa:
            cond_tempo    = segundos_decorridos >= TEMPO_ATIVAR_ZONA
            cond_inimigos = inimigos_vivos > 0 and inimigos_vivos <= INIMIGOS_ATIVAR_ZONA
            if cond_tempo or cond_inimigos:
                self.ativa = True

        # Avança a zona se ativa e não congelada pelo power-up
        if self.ativa and not congelada:
            # Normaliza para 60fps: velocidade constante em qualquer computador
            self.margem += VELOCIDADE_ZONA * (dt / 16.67)

        # Impede que a zona ultrapasse o centro do mapa
        margem_maxima = min(LARGURA_MAPA, ALTURA_MAPA) / 2 - 20
        self.margem   = min(self.margem, margem_maxima)

        # Atualiza fase da animação de pulsação
        self.pulso += dt * 0.004

    def desenhar(self, tela):
        """
        Renderiza a zona como 4 faixas semi-transparentes nas bordas do mapa.
        A borda interna pulsa em vermelho brilhante — é a "parede da morte".
        """
        if self.margem < 1:
            return   # Zona ainda não existe

        m = int(self.margem)

        # Opacidade pulsante — a zona "respira" visualmente
        alpha_pulso = int(180 + 60 * math.sin(self.pulso))

        # Surface transparente para as faixas vermelhas
        surf_zona = pygame.Surface((LARGURA_MAPA, ALTURA_MAPA), pygame.SRCALPHA)

        # Faixas em cada borda (superior, inferior, esquerda, direita)
        pygame.draw.rect(surf_zona, (*COR_ZONA_FILL, alpha_pulso),
                         (0, 0, LARGURA_MAPA, m + 8))                        # Topo
        pygame.draw.rect(surf_zona, (*COR_ZONA_FILL, alpha_pulso),
                         (0, ALTURA_MAPA - m - 8, LARGURA_MAPA, m + 8))      # Base
        pygame.draw.rect(surf_zona, (*COR_ZONA_FILL, alpha_pulso),
                         (0, m, m + 8, ALTURA_MAPA - m * 2))                 # Esquerda
        pygame.draw.rect(surf_zona, (*COR_ZONA_FILL, alpha_pulso),
                         (LARGURA_MAPA - m - 8, m, m + 8, ALTURA_MAPA - m * 2))  # Direita

        tela.blit(surf_zona, (0, 0))

        # Linha brilhante na borda interna: indica exatamente onde é perigoso
        brilho       = int(200 + 55 * math.sin(self.pulso * 1.5))
        cor_borda    = (255, brilho // 4, brilho // 4)
        espessura_ln = max(2, int(3 + 2 * math.sin(self.pulso)))
        pygame.draw.rect(
            tela, cor_borda,
            (m, m, LARGURA_MAPA - m * 2, ALTURA_MAPA - m * 2),
            espessura_ln
        )

    def jogador_na_zona(self, jog_x, jog_y, jog_tamanho):
        """
        Verifica se o jogador tocou a zona vermelha → game over.

        Args:
            jog_x, jog_y (float): posição do jogador
            jog_tamanho  (int)  : raio do jogador

        Returns:
            bool: True se o jogador está na zona
        """
        if self.margem <= 0:
            return False
        r = jog_tamanho
        return (
            jog_x - r < self.margem or
            jog_x + r > LARGURA_MAPA - self.margem or
            jog_y - r < self.margem or
            jog_y + r > ALTURA_MAPA  - self.margem
        )

    @property
    def area_segura(self):
        """Retorna pygame.Rect da área segura atual (usada pelo radar do HUD)."""
        m = int(self.margem)
        return pygame.Rect(m, m, LARGURA_MAPA - m * 2, ALTURA_MAPA - m * 2)

# PARTÍCULAS: Efeitos visuais temporário
class Particula:
    """
    Uma partícula de efeito visual temporário.

    FÍSICA SIMPLES:
    - posição += velocidade × dt (movimento)
    - velocidade *= atrito (desaceleração gradual)
    - vida diminui a cada frame (fade out — some suavemente)
    """

    def __init__(self, x, y, cor, velocidade=None, tamanho=None, vida=None):
        """
        Args:
            x, y       (float): posição inicial em pixels
            cor        (tuple): cor RGB da partícula
            velocidade (float): rapidez inicial (aleatória se None)
            tamanho    (float): raio inicial (aleatório se None)
            vida       (float): duração (1.0 = padrão, valores maiores duram mais)
        """
        self.x   = x
        self.y   = y
        self.cor = cor

        # Direção aleatória — a partícula voa em ângulo aleatório
        angulo   = random.uniform(0, 2 * math.pi)
        vel      = velocidade or random.uniform(1.5, 4.0)
        self.vel_x = math.cos(angulo) * vel
        self.vel_y = math.sin(angulo) * vel

        self.vida      = vida or 1.0    # 1.0 = cheio, 0.0 = morta
        self.vida_max  = self.vida
        self.tamanho   = tamanho or random.uniform(1.5, 3.5)
        self.atrito    = 0.92           # Fator de desaceleração (< 1 = atrasa)

    def atualizar(self, dt):
        """Atualiza posição, velocidade e vida da partícula."""
        fator       = dt / 16.67        # Normaliza para 60fps
        self.x     += self.vel_x * fator
        self.y     += self.vel_y * fator
        self.vel_x *= self.atrito       # Desacelera gradualmente
        self.vel_y *= self.atrito
        self.vida  -= 0.025 * fator     # Vai diminuindo até 0

    def desenhar(self, tela):
        """Renderiza com opacidade proporcional à vida restante (fade out)."""
        if self.vida <= 0:
            return
        opacidade = int((self.vida / self.vida_max) * 255)
        raio      = max(1, int(self.tamanho * (self.vida / self.vida_max)))
        surf      = pygame.Surface((raio * 2 + 2, raio * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*self.cor, opacidade),
                           (raio + 1, raio + 1), raio)
        tela.blit(surf, (int(self.x) - raio - 1, int(self.y) - raio - 1))

    @property
    def morta(self):
        """Retorna True se a partícula deve ser removida."""
        return self.vida <= 0


def criar_explosao(x, y, cor_primaria, cor_secundaria):
    """
    Cria uma explosão de partículas ao eliminar um inimigo.

    Gera duas camadas:
      1. Partículas rápidas e grandes (anel externo da explosão)
      2. Partículas lentas e pequenas (brilho residual que some devagar)

    Args:
        x, y           (float): posição da explosão em pixels
        cor_primaria   (tuple): cor principal das partículas
        cor_secundaria (tuple): cor do brilho residual

    Returns:
        list[Particula]: lista com todas as partículas criadas
    """
    particulas = []

    # Burst externo: 16 partículas rápidas e grandes
    for _ in range(16):
        particulas.append(Particula(
            x, y, cor_primaria,
            velocidade=random.uniform(2, 5),
            tamanho=random.uniform(2, 4)
        ))

    # Brilho residual: 10 partículas lentas que duram mais
    for _ in range(10):
        particulas.append(Particula(
            x, y, cor_secundaria,
            velocidade=random.uniform(0.5, 2),
            tamanho=random.uniform(1, 2.5),
            vida=1.5
        ))

    return particulas


def criar_coleta_item(x, y, cor):
    """
    Cria partículas ao coletar um item especial.

    Returns:
        list[Particula]
    """
    return [
        Particula(x, y, cor,
                  velocidade=random.uniform(1, 3),
                  tamanho=random.uniform(1.5, 3))
        for _ in range(12)
    ]


# ITEM ESPECIAL: Power-ups coletáveis
class ItemEspecial:
    """
    Item especial que o jogador pode coletar ao passar por cima.

    Tipos disponíveis:
        "velocidade" → aumenta velocidade de movimento temporariamente
        "duplo"      → dispara dois projéteis ao mesmo tempo
        "escudo"     → protege contra inimigos e zona vermelha
        "congelar"   → congela o crescimento da zona vermelha
    """

    # Metadados de cada tipo: cor visual e rótulo exibido na tela
    TIPOS = {
        "velocidade": {"cor": (255, 221,  68), "rotulo": "VEL"},
        "duplo":      {"cor": (255, 107,  53), "rotulo": "DBL"},
        "escudo":     {"cor": (  0, 212, 255), "rotulo": "ESC"},
        "congelar":   {"cor": (136, 238, 255), "rotulo": "FRZ"},
    }

    def __init__(self, coluna, linha, tipo):
        """
        Args:
            coluna (int): coluna no mapa
            linha  (int): linha no mapa
            tipo   (str): tipo do power-up
        """
        self.x, self.y  = Labirinto.tile_para_pixel_centro(coluna, linha)
        self.tipo       = tipo
        self.ativo      = True    # False após ser coletado
        self.pulso      = random.uniform(0, math.pi * 2)   # Fase individual
        self.meta       = self.TIPOS.get(tipo, self.TIPOS["velocidade"])

    def atualizar(self, dt):
        """Atualiza a animação de pulsação do item."""
        self.pulso += dt * 0.004

    def verificar_coleta(self, jog_x, jog_y, jog_tamanho):
        """
        Verifica se o jogador passou perto o suficiente para coletar.

        Returns:
            bool: True se foi coletado agora
        """
        if not self.ativo:
            return False
        dx = self.x - jog_x
        dy = self.y - jog_y
        raio_coleta = jog_tamanho + 14
        if dx * dx + dy * dy < raio_coleta * raio_coleta:
            self.ativo = False
            return True
        return False

    def desenhar(self, tela):
        """
        Renderiza o item como losango pulsante com rótulo e brilho.
        """
        if not self.ativo:
            return

        cor    = self.meta["cor"]
        rotulo = self.meta["rotulo"]
        cx, cy = int(self.x), int(self.y)
        raio   = int(10 + 2 * math.sin(self.pulso))   # Raio pulsante

        # Brilho externo
        surf_glow = pygame.Surface((raio * 4, raio * 4), pygame.SRCALPHA)
        pygame.draw.circle(surf_glow, (*cor, 40), (raio * 2, raio * 2), raio * 2)
        tela.blit(surf_glow, (cx - raio * 2, cy - raio * 2))

        # Losango (quadrado rotacionado 45°): usa surface SRCALPHA para suportar alpha
        losango = [
            (cx,        cy - raio),
            (cx + raio, cy       ),
            (cx,        cy + raio),
            (cx - raio, cy       ),
        ]
        surf_losango = pygame.Surface((raio * 2 + 4, raio * 2 + 4), pygame.SRCALPHA)
        pontos_locais = [
            (raio + 2,          2         ),
            (raio * 2 + 2,      raio + 2  ),
            (raio + 2,          raio * 2 + 2),
            (2,                 raio + 2  ),
        ]
        pygame.draw.polygon(surf_losango, (*cor, 200), pontos_locais)
        pygame.draw.polygon(surf_losango, (*cor, 255), pontos_locais, 2)
        tela.blit(surf_losango, (cx - raio - 2, cy - raio - 2))

        # Rótulo centralizado no item
        fonte = pygame.font.SysFont("Courier New", 8, bold=True)
        texto = fonte.render(rotulo, True, (10, 10, 20))
        tela.blit(texto, (cx - texto.get_width() // 2,
                          cy - texto.get_height() // 2))
