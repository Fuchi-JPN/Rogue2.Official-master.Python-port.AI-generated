"""
policies.py - Policy抽象＋ScriptedPolicy（設計書 §5）

ScriptedPolicyは strategy.decide()（§5.4正本）を直接実行する。
"""
try:
    from . import strategy
    from .schemas import AIAction, AIObservation, IdentifyMemo
except ImportError:
    import strategy
    from schemas import AIAction, AIObservation, IdentifyMemo


class Policy:
    name = "base"

    def decide(self, obs: AIObservation, history: list):
        """(AIAction, thought) を返す"""
        raise NotImplementedError


class ScriptedPolicy(Policy):
    name = "scripted"

    def __init__(self, memo=None):
        self.memo = memo if memo is not None else IdentifyMemo()
        self.pos_history: list = []
        self.heading = None  # 前手の移動方向（通路追従用）
        self.memory = strategy.ExplorationMemory()

    def decide(self, obs: AIObservation, history: list):
        self.memory.update(obs)
        obs.unopened_doors = self.memory.unopened_visible(obs)
        risk = strategy.assess(obs)
        action, reason = strategy.decide(obs, risk, self.memo, self.pos_history,
                                         heading=self.heading, memory=self.memory)
        if action.type == "move" and action.direction:
            self.heading = action.direction
        self.pos_history.append(tuple(obs.player_pos))
        # 履歴は直近64手のみ保持
        if len(self.pos_history) > 64:
            self.pos_history = self.pos_history[-64:]
        return action, reason
