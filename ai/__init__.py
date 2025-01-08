# ai/__init__.py
from .mccfr_agent import MCCFRAgent
from .game_rules import PineappleRules
from .evaluator import HandEvaluator

__all__ = ['MCCFRAgent', 'PineappleRules', 'HandEvaluator']

# ai/evaluator.py
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
