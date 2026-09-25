"""
Neural memory module used by the Mnemosyne brain service.

In this repository, "Titans" means this memory architecture only:
an embedding, an LSTM short-term context, and an MLP, with a
next-character surprise score and one gradient update step.
It does not name an agent.
"""

import torch
import torch.nn as nn
import torch.optim as optim
from typing import Dict, Tuple


class NeuralMemory(nn.Module):
    """
    Memory module: embedding, LSTM, and a two-layer MLP.
    This is the Titans memory architecture in this repository.
    """
    
    def __init__(self, embed_dim: int = 16, hidden_dim: int = 32, vocab_size: int = 100):
        super(NeuralMemory, self).__init__()
        self.embed_dim = embed_dim
        self.vocab_size = vocab_size
        
        # Embedding layer
        self.embedding = nn.Embedding(vocab_size, embed_dim)
        
        # Short-Term Context (Controller)
        self.lstm = nn.LSTM(
            input_size=embed_dim,
            hidden_size=hidden_dim,
            batch_first=True
        )
        
        # MLP. It reads the LSTM hidden size only; the embedding is not concatenated.
        self.fc1 = nn.Linear(hidden_dim, hidden_dim)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_dim, vocab_size)
        
    def forward(self, x: torch.Tensor, hidden: Tuple[torch.Tensor, torch.Tensor] = None) -> Tuple[torch.Tensor, Tuple[torch.Tensor, torch.Tensor]]:
        """
        Forward pass with memory interaction.
        """
        # Embed input
        embedded = self.embedding(x)  # [batch, seq, embed]
        
        # Pass through LSTM Controller
        lstm_out, new_hidden = self.lstm(embedded, hidden)  # lstm_out: [batch, seq, hidden_dim]
        
        # MLP over the LSTM output
        mem_out = self.fc1(lstm_out)
        mem_out = self.relu(mem_out)
        logits = self.fc2(mem_out)  # [batch, seq, vocab]
        
        return logits, new_hidden


class SecurityAgent:
    """
    Optimizer, loss, and LSTM state for one NeuralMemory instance.

    The class name is historical. This is not a Titans agent.
    Titans refers only to the memory module above.
    """
    
    def __init__(self, embed_dim: int = 16, hidden_dim: int = 32, vocab_size: int = 100, learning_rate: float = 0.01):
        self.embed_dim = embed_dim
        self.vocab_size = vocab_size
        self.learning_rate = learning_rate
        
        self.model = NeuralMemory(embed_dim, hidden_dim, vocab_size)
        self.optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        self.criterion = nn.CrossEntropyLoss()
        
        # Persistent Short-Term Context (LSTM state)
        self.hidden_state = None
        
    def _tokenize(self, text: str) -> torch.Tensor:
        tokens = [ord(c) % self.vocab_size for c in text]
        return torch.tensor(tokens, dtype=torch.long).unsqueeze(0)
    
    def calculate_surprise(self, text: str) -> float:
        if not text or len(text) < 2:
            return 0.0
        
        tokens = self._tokenize(text)
        input_tokens = tokens[:, :-1]
        target_tokens = tokens[:, 1:]
        
        self.model.eval()
        with torch.no_grad():
            # Pass persistent hidden state
            logits, new_hidden = self.model(input_tokens, self.hidden_state)
            
            logits_flat = logits.reshape(-1, self.vocab_size)
            target_flat = target_tokens.reshape(-1)
            loss = self.criterion(logits_flat, target_flat)
            surprise_score = loss.item()
            
            # Update persistent state (detach to prevent graph retention)
            self.hidden_state = (new_hidden[0].detach(), new_hidden[1].detach())
        
        return surprise_score
    
    def update_memory(self, text: str) -> None:
        if not text or len(text) < 2:
            return
        
        tokens = self._tokenize(text)
        input_tokens = tokens[:, :-1]
        target_tokens = tokens[:, 1:]
        
        self.model.train()
        
        # For learning, we temporarily use the valid hidden state 
        # but don't persist the result to avoid double-counting context
        # detaching is crucial
        ctx = self.hidden_state
        if ctx:
             ctx = (ctx[0].detach(), ctx[1].detach())

        logits, _ = self.model(input_tokens, ctx)
        
        logits_flat = logits.reshape(-1, self.vocab_size)
        target_flat = target_tokens.reshape(-1)
        loss = self.criterion(logits_flat, target_flat)
        
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
    
    def is_anomalous(self, surprise_score: float, threshold: float = 4.2) -> bool:
        """
        Determine if a surprise score indicates an anomaly.
        
        
        Args:
            surprise_score: Calculated surprise score
            threshold: Anomaly threshold (default: 4.2)
            
        Returns:
            True if anomalous, False otherwise
        """
        return surprise_score > threshold


class SessionManager:
    """
    Manages session-specific SecurityAgent instances.
    """
    
    def __init__(self):
        self.sessions: Dict[str, SecurityAgent] = {}
    
    def get_or_create_agent(self, session_id: str) -> SecurityAgent:
        """
        Retrieve existing agent for session or create a new one.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            SecurityAgent instance for the session
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = SecurityAgent()
        return self.sessions[session_id]
    
    def get_session_count(self) -> int:
        """Get the number of active sessions."""
        return len(self.sessions)
