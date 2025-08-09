# data/agent.py
import numpy as np
import pandas as pd
import os

class QLearningAgent:
    def __init__(self, actions, learning_rate=0.1, reward_decay=0.9, e_greedy=0.9):
        self.actions = actions  # [0, 1, 2] for easy, normal, hard
        self.lr = learning_rate
        self.gamma = reward_decay
        self.epsilon = e_greedy
        self.q_table_path = 'q_table_game3.csv' # 서버 내에 저장될 파일명
        self.q_table = self._load_q_table()

    def _load_q_table(self):
        """ CSV 파일에서 Q-테이블을 로드합니다. 없으면 새로 생성합니다. """
        if os.path.exists(self.q_table_path):
            return pd.read_csv(self.q_table_path, index_col=0)
        else:
            states = ['low_power', 'mid_power', 'high_power']
            return pd.DataFrame(
                np.zeros((len(states), len(self.actions))),
                index=states,
                columns=[str(a) for a in self.actions]
            )

    def _discretize_state(self, avg_power):
        """ 연속적인 평균 파워 값을 'low', 'mid', 'high' 이산 상태로 변환합니다. """
        if avg_power < 50:
            return 'low_power'
        elif 50 <= avg_power < 90:
            return 'mid_power'
        else:
            return 'high_power'

    def save_q_table(self):
        """ Q-테이블을 CSV 파일로 저장합니다. """
        self.q_table.to_csv(self.q_table_path)

    def choose_action(self, state_observation):
        """ Epsilon-Greedy 전략에 따라 행동(난이도)을 선택합니다. """
        state = self._discretize_state(state_observation)
        
        if state not in self.q_table.index:
            new_row = pd.Series([0]*len(self.actions), index=self.q_table.columns, name=state)
            self.q_table = pd.concat([self.q_table, pd.DataFrame([new_row])])

        if np.random.uniform() > self.epsilon:
            action = np.random.choice(self.actions) # 탐험: 무작위 선택
        else:
            state_action_values = self.q_table.loc[state, :]
            action = np.random.choice(
                state_action_values[state_action_values == np.max(state_action_values)].index
            ) # 활용: 가장 Q값이 높은 행동 선택
        
        return int(action)

    def update_q_table(self, state, action, reward, next_state):
        """ Q-러닝 공식에 따라 Q-테이블을 업데이트하고 저장합니다. """
        s = self._discretize_state(state)
        s_ = self._discretize_state(next_state)
        a = str(action)

        if s_ not in self.q_table.index:
            new_row = pd.Series([0]*len(self.actions), index=self.q_table.columns, name=s_)
            self.q_table = pd.concat([self.q_table, pd.DataFrame([new_row])])

        q_predict = self.q_table.loc[s, a]
        q_target = reward + self.gamma * self.q_table.loc[s_, :].max()
        
        # Q-러닝 업데이트
        self.q_table.loc[s, a] += self.lr * (q_target - q_predict)
        self.save_q_table()