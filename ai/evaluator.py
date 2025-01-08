# ai/evaluator.py (Часть 1)
from typing import List, Dict
from collections import Counter

class HandEvaluator:
    RANKS = '23456789TJQKA'
    SUITS = '♠♣♥♦'
    
    @staticmethod
    def evaluate_top(cards: List[Dict]) -> float:
        """Оценка комбинации верхней линии"""
        if not cards or len(cards) != 3:
            return 0
            
        ranks = [card['rank'] for card in cards]
        rank_counts = Counter(ranks)
        
        # Проверяем сет
        if 3 in rank_counts.values():
            rank = [r for r, c in rank_counts.items() if c == 3][0]
            return 10 + HandEvaluator.RANKS.index(rank)
            
        # Проверяем пару
        if 2 in rank_counts.values():
            pair_rank = [r for r, c in rank_counts.items() if c == 2][0]
            kicker = [r for r, c in rank_counts.items() if c == 1][0]
            return 5 + HandEvaluator.RANKS.index(pair_rank) * 0.1
            
        # Старшая карта
        highest_rank = max(ranks, key=lambda x: HandEvaluator.RANKS.index(x))
        return HandEvaluator.RANKS.index(highest_rank) * 0.1

    @staticmethod
    def evaluate_middle(cards: List[Dict]) -> float:
        """Оценка комбинации средней линии"""
        return HandEvaluator._evaluate_five_cards(cards, is_middle=True)
        
    @staticmethod
    def evaluate_bottom(cards: List[Dict]) -> float:
        """Оценка комбинации нижней линии"""
        return HandEvaluator._evaluate_five_cards(cards, is_middle=False)
        
    @staticmethod
    def _evaluate_five_cards(cards: List[Dict], is_middle: bool) -> float:
        if not cards or len(cards) != 5:
            return 0
            
        ranks = [card['rank'] for card in cards]
        suits = [card['suit'] for card in cards]
        
        rank_counts = Counter(ranks)
        suit_counts = Counter(suits)
        
        # Проверяем комбинации от старшей к младшей
        # Роял-флеш
        if (len(set(suits)) == 1 and 
            set(ranks) == set('TJQKA')):
            return 9000 + (1.5 if is_middle else 1)
            
        # Стрит-флеш
        if len(set(suits)) == 1:
            rank_values = sorted([HandEvaluator.RANKS.index(r) for r in ranks])
            if rank_values[-1] - rank_values[0] == 4:
                return 8000 + rank_values[-1] + (1.5 if is_middle else 1)
                
        # Каре
        if 4 in rank_counts.values():
            quads_rank = [r for r, c in rank_counts.items() if c == 4][0]
            kicker = [r for r, c in rank_counts.items() if c == 1][0]
            return 7000 + HandEvaluator.RANKS.index(quads_rank) * 13 + HandEvaluator.RANKS.index(kicker)
            
        # Фулл-хаус
        if 3 in rank_counts.values() and 2 in rank_counts.values():
            three_rank = [r for r, c in rank_counts.items() if c == 3][0]
            pair_rank = [r for r, c in rank_counts.items() if c == 2][0]
            return 6000 + HandEvaluator.RANKS.index(three_rank) * 13 + HandEvaluator.RANKS.index(pair_rank)
            
        # Флеш
        if len(set(suits)) == 1:
            rank_values = sorted([HandEvaluator.RANKS.index(r) for r in ranks])
            return 5000 + sum(rank_values[i] * pow(13, i) for i in range(5))
            
        # Стрит
        rank_values = sorted([HandEvaluator.RANKS.index(r) for r in ranks])
        if rank_values[-1] - rank_values[0] == 4:
            return 4000 + rank_values[-1]
            
        # Сет
        if 3 in rank_counts.values():
            three_rank = [r for r, c in rank_counts.items() if c == 3][0]
            kickers = sorted([r for r, c in rank_counts.items() if c == 1],
                           key=lambda x: HandEvaluator.RANKS.index(x))
            return 3000 + HandEvaluator.RANKS.index(three_rank) * 169 + HandEvaluator.RANKS.index(kickers[1]) * 13 + HandEvaluator.RANKS.index(kickers[0])
            
        # Две пары
        if list(rank_counts.values()).count(2) == 2:
            pairs = sorted([r for r, c in rank_counts.items() if c == 2],
                         key=lambda x: HandEvaluator.RANKS.index(x))
            kicker = [r for r, c in rank_counts.items() if c == 1][0]
            return 2000 + HandEvaluator.RANKS.index(pairs[1]) * 169 + HandEvaluator.RANKS.index(pairs[0]) * 13 + HandEvaluator.RANKS.index(kicker)
            
        # Пара
        if 2 in rank_counts.values():
            pair_rank = [r for r, c in rank_counts.items() if c == 2][0]
            kickers = sorted([r for r, c in rank_counts.items() if c == 1],
                           key=lambda x: HandEvaluator.RANKS.index(x))
            return 1000 + HandEvaluator.RANKS.index(pair_rank) * 2197 + sum(HandEvaluator.RANKS.index(k) * pow(13, i) for i, k in enumerate(kickers))
            
        # Старшая карта
        rank_values = sorted([HandEvaluator.RANKS.index(r) for r in ranks])
        return sum(rank_values[i] * pow(13, i) for i in range(5))

    def _get_middle_royalty(self, cards: List[Dict]) -> int:
        """Подсчитывает бонусы за среднюю линию"""
        value = self.evaluate_middle(cards)
        # Проверяем комбинации от старшей к младшей
        if value >= 9000:  # Роял-флеш
            return 50
        if value >= 8000:  # Стрит-флеш
            return 30
        if value >= 7000:  # Каре
            return 20
        if value >= 6000:  # Фулл-хаус
            return 12
        if value >= 5000:  # Флеш
            return 8
        if value >= 4000:  # Стрит
            return 4
        if value >= 3000:  # Сет
            return 2
            
        return 0

    def _get_bottom_royalty(self, cards: List[Dict]) -> int:
    """Подсчитывает бонусы за нижнюю линию"""
        value = self.evaluate_bottom(cards)
        
        # Проверяем комбинации от старшей к младшей
        if value >= 9000:  # Роял-флеш
            return 25
        if value >= 8000:  # Стрит-флеш
            return 15
            if value >= 7000:  # Каре
            return 10
        if value >= 6000:  # Фулл-хаус
            return 6
        if value >= 5000:  # Флеш
            return 4
        if value >= 4000:  # Стрит
            return 2
            
        return 0

    def evaluate_fantasy_potential(self, hand: Dict) -> float:
        """Оценивает потенциал для фантазии"""
        if not hand or 'top' not in hand:
            return 0.0
            
        top_cards = hand['top']
        if not top_cards or len(top_cards) != 3:
            return 0.0
            
        ranks = [card['rank'] for card in top_cards]
        rank_counts = {}
        for rank in ranks:
            rank_counts[rank] = rank_counts.get(rank, 0) + 1
        
        # Оцениваем потенциал от высшего к низшему
        if any(rank_counts.get(r, 0) >= 3 for r in self.RANKS):  # Сет
            return 1.0
        if rank_counts.get('A', 0) >= 2:  # AA
            return 0.9
        if rank_counts.get('K', 0) >= 2:  # KK
            return 0.8
        if rank_counts.get('Q', 0) >= 2:  # QQ
            return 0.7
            
        # Оцениваем близость к фантазии
        high_pairs = sum(1 for r in 'QKA' if rank_counts.get(r, 0) >= 2)
        if high_pairs > 0:
            return 0.3 * high_pairs
            
        # Оцениваем потенциал для сета
        for rank in self.RANKS:
            if rank_counts.get(rank, 0) == 2:
                return 0.2  # Есть пара, возможен сет
                
        return 0.0

    def _rank_to_value(self, rank: str) -> int:
        """Преобразует ранг карты в числовое значение"""
        return self.RANKS.index(rank)

    def _is_straight(self, ranks: List[str]) -> bool:
        """Проверяет является ли комбинация стритом"""
        values = sorted([self._rank_to_value(r) for r in ranks])
        if values[-1] - values[0] == 4:  # Обычный стрит
            return True
        # Проверяем колесо (A-5)
        if set(ranks) == {'A', '2', '3', '4', '5'}:
            return True
        return False

    def _get_kickers(self, ranks: List[str], exclude_ranks: List[str]) -> List[str]:
        """Получает список кикеров, исключая определенные ранги"""
        kickers = [r for r in ranks if r not in exclude_ranks]
        return sorted(kickers, key=lambda x: self._rank_to_value(x), reverse=True)

    def calculate_hand_strength(self, hand: Dict) -> float:
        """Вычисляет общую силу руки"""
        if not all(key in hand for key in ['top', 'middle', 'bottom']):
            return 0.0
            
        top_value = self.evaluate_top(hand['top'])
        middle_value = self.evaluate_middle(hand['middle'])
        bottom_value = self.evaluate_bottom(hand['bottom'])
        
        # Проверяем правило возрастания силы
        if not (top_value <= middle_value <= bottom_value):
            return 0.0  # Мертвая рука
            
        # Нормализуем значения
        max_top = 22  # Максимальное значение для верхней линии (AAA)
        max_middle = 9100  # Примерное максимальное значение для средней линии
        max_bottom = 9100  # Примерное максимальное значение для нижней линии
        
        normalized_top = top_value / max_top
        normalized_middle = middle_value / max_middle
        normalized_bottom = bottom_value / max_bottom
        
        # Взвешенная сумма с учетом важности линий
        weighted_sum = (normalized_top * 0.2 +  # Верхняя линия менее важна
                       normalized_middle * 0.35 +
                       normalized_bottom * 0.45)
                       
        return weighted_sum

    def _get_middle_royalty(self, cards: List[Dict]) -> int:
        """Подсчитывает бонусы за среднюю линию"""
        value = self.evaluate_middle(cards)
        
        # Проверяем комбинации от сильнейшей к слабейшей
        if value >= 9000:  # Роял-флеш
            return 50
        if value >= 8000:  # Стрит-флеш
            return 30
        if value >= 7000:  # Каре
            return 20
        if value >= 6000:  # Фулл-хаус
            return 12
        if value >= 5000:  # Флеш
            return 8
        if value >= 4000:  # Стрит
            return 4
        if value >= 3000:  # Сет
            return 2
            
        return 0

    def _get_bottom_royalty(self, cards: List[Dict]) -> int:
        """Подсчитывает бонусы за нижнюю линию"""
        value = self.evaluate_bottom(cards)
        
        # Проверяем комбинации от сильнейшей к слабейшей
        if value >= 9000:  # Роял-флеш
            return 25
        if value >= 8000:  # Стрит-флеш
            return 15
        if value >= 7000:  # Каре
            return 10
        if value >= 6000:  # Фулл-хаус
            return 6
        if value >= 5000:  # Флеш
            return 4
        if value >= 4000:  # Стрит
            return 2
            
        return 0
