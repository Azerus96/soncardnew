from flask import Flask, render_template, jsonify, session, request
import random 
import os
from ai.mccfr_agent import MCCFRAgent
from ai.game_rules import PineappleRules
from storage.github_storage import GitHubStorage
import json
from typing import Dict, List

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Инициализация компонентов
rules = PineappleRules()
standard_agent = MCCFRAgent(progressive=False)
progressive_agent = MCCFRAgent(progressive=True)
storage = GitHubStorage()

# Загрузка сохраненного состояния ИИ
try:
    saved_state = storage.load_progress()
    if saved_state:
        state_data = json.loads(saved_state)
        if 'standard' in state_data:
            standard_agent.load_state(state_data['standard'])
        if 'progressive' in state_data:
            progressive_agent.load_state(state_data['progressive'])
except Exception as e:
    print(f"Error loading AI state: {e}")

class Deck:
    def __init__(self):
        self.suits = ['♥', '♦', '♣', '♠']
        self.ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        self.cards = [{'suit': suit, 'rank': rank} for suit in self.suits for rank in self.ranks]
        self.used_cards = []
        random.shuffle(self.cards)
    
    def draw(self, count: int) -> List[Dict]:
        if len(self.cards) < count:
            return []
        drawn_cards = [self.cards.pop() for _ in range(count)]
        self.used_cards.extend(drawn_cards)
        return drawn_cards

def save_ai_progress():
    """Сохраняет прогресс обоих агентов"""
    state_data = {
        'standard': standard_agent.save_state(),
        'progressive': progressive_agent.save_state()
    }
    storage.save_progress(json.dumps(state_data))

@app.route('/')
def home():
    if 'game_state' not in session:
        session['game_state'] = {
            'hand': [],
            'table': {
                'top': [''] * 3,
                'middle': [''] * 5,
                'bottom': [''] * 5
            },
            'used_cards': [],
            'draw_count': 0,
            'initial_cards_placed': False,
            'fantasy_mode': False,
            'progressive': False
        }
    return render_template('index.html', game_state=session['game_state'])

@app.route('/training')
def training():
    return render_template('training.html')

@app.route('/start')
def start_game():
    deck = Deck()
    initial_cards = deck.cards[:5]
    
    game_state = {
        'hand': initial_cards,
        'table': {
            'top': [''] * 3,
            'middle': [''] * 5,
            'bottom': [''] * 5
        },
        'used_cards': [f"{card['rank']}{card['suit']}" for card in initial_cards],
        'draw_count': 0,
        'initial_cards_placed': False,
        'fantasy_mode': False,
        'progressive': request.args.get('progressive', 'false').lower() == 'true'
    }
    
    session['game_state'] = game_state
    return jsonify({'cards': initial_cards})

@app.route('/draw')
def draw_cards():
    game_state = session.get('game_state', {})
    
    if not game_state.get('initial_cards_placed'):
        return jsonify({'cards': [], 'error': 'Сначала распределите начальные карты!'})
    
    if game_state.get('draw_count', 0) >= 4:
        return jsonify({'cards': [], 'error': 'Больше карт взять нельзя!'})
    
    deck = Deck()
    used_cards = game_state.get('used_cards', [])
    available_cards = [card for card in deck.cards 
                      if f"{card['rank']}{card['suit']}" not in used_cards]
    
    cards_to_draw = 3
    if game_state.get('fantasy_mode'):
        if game_state.get('progressive'):
            fantasy_type = rules.check_fantasy(game_state['table']['top'])
            cards_to_draw = fantasy_type['extra_cards'] - len(game_state['hand'])
        else:
            cards_to_draw = 14 - len(game_state['hand'])
    
    next_cards = available_cards[:cards_to_draw]
    
    game_state['hand'].extend(next_cards)
    game_state['used_cards'].extend([f"{card['rank']}{card['suit']}" for card in next_cards])
    game_state['draw_count'] = game_state.get('draw_count', 0) + 1
    
    session['game_state'] = game_state
    return jsonify({'cards': next_cards})

@app.route('/update_state', methods=['POST'])
def update_state():
    if not request.is_json:
        return jsonify({'error': 'Content type must be application/json'}), 400
    
    game_state = request.get_json()
    
    if not isinstance(game_state, dict):
        return jsonify({'error': 'Invalid game state format'}), 400
    
    required_keys = ['hand', 'table', 'used_cards', 'draw_count', 'initial_cards_placed']
    if not all(key in game_state for key in required_keys):
        return jsonify({'error': 'Missing required game state fields'}), 400
    
    # Проверяем возможность фантазии
    if game_state['initial_cards_placed'] and not game_state.get('fantasy_mode'):
        fantasy_check = rules.check_fantasy(game_state['table']['top'])
        if fantasy_check['fantasy']:
            game_state['fantasy_mode'] = True
    
    session['game_state'] = game_state
    return jsonify({'status': 'success'})

@app.route('/ai_move', methods=['POST'])
def ai_move():
    """Получает ход от ИИ"""
    game_state = request.json
    agent = progressive_agent if game_state.get('progressive') else standard_agent
    
    # Обновляем знания ИИ о картах
    agent.update_cards_knowledge(game_state.get('visible_cards', []))
    
    # Получаем ход от ИИ
    action = agent.get_action(game_state)
    
    # Сохраняем прогресс
    save_ai_progress()
    
    return jsonify({'action': action})

@app.route('/train_ai', methods=['POST'])
def train_ai():
    """Тренировка ИИ"""
    data = request.json
    iterations = data.get('iterations', 1000)
    progressive = data.get('progressive', False)
    
    agent = progressive_agent if progressive else standard_agent
    agent.train(iterations)
    
    # Сохраняем прогресс
    save_ai_progress()
    
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True)
