"""
Time-Aware Transformer for sepsis early warning.

Two clinically-motivated architectural choices drive this design:

1. Time2Vec instead of fixed positional encoding: ICU vitals are
   sampled irregularly (a nurse may chart every 30 min or skip 3
   hours). Standard sinusoidal positional encoding assumes evenly
   spaced steps; Time2Vec instead embeds the actual elapsed-time value
   (ICULOS), learning both a linear trend component and periodic
   components directly from real timestamps.

2. Causal self-attention: at hour T, the model must only see hours
   <= T. Predicting sepsis risk using future vitals would be a lookahead
   leak that can never happen in real deployment (the AI Gateway calls
   this model with only the vitals recorded so far).
"""

import torch
import torch.nn as nn


def get_device() -> torch.device:
    """MPS (Apple Silicon) -> CUDA -> CPU, in that priority order."""
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


class Time2Vec(nn.Module):
    """Learns a vector representation of time (Kazemi et al. 2019).

    Input:  (batch, seq_len) raw timestamps (ICULOS hours)
    Output: (batch, seq_len, d_time) — one linear (trend) component
            concatenated with (d_time - 1) learned periodic components.
    """

    def __init__(self, d_time: int = 16):
        super().__init__()
        self.d_time = d_time
        self.w0 = nn.Parameter(torch.randn(1))
        self.b0 = nn.Parameter(torch.randn(1))
        self.w = nn.Parameter(torch.randn(d_time - 1))
        self.b = nn.Parameter(torch.randn(d_time - 1))

    def forward(self, t: torch.Tensor) -> torch.Tensor:
        t = t.unsqueeze(-1)  # (batch, seq_len, 1)
        linear = t * self.w0 + self.b0  # (batch, seq_len, 1)
        periodic = torch.sin(t * self.w + self.b)  # (batch, seq_len, d_time - 1)
        return torch.cat([linear, periodic], dim=-1)  # (batch, seq_len, d_time)


class SepsisTransformer(nn.Module):
    """Time-aware causal Transformer producing sepsis risk + SOFA.

    Risk head returns a RAW LOGIT (no sigmoid applied inside the
    module): training uses BCEWithLogitsLoss directly on this logit
    for numerical stability, and inference.py applies torch.sigmoid()
    explicitly to turn it into a 0-1 probability. Keeping the sigmoid
    out of the module (rather than toggling it by train/eval mode)
    avoids `forward()`'s output semantics silently depending on
    whatever mode the caller happens to be in.
    """

    def __init__(
        self,
        n_vitals: int = 7,
        d_time: int = 16,
        d_model: int = 128,
        n_heads: int = 4,
        n_layers: int = 4,
        d_ff: int = 256,
        dropout: float = 0.1,
        window_size: int = 24,
    ):
        super().__init__()
        self.window_size = window_size

        self.time2vec = Time2Vec(d_time)
        self.feature_proj = nn.Linear(n_vitals, 64)
        self.input_proj = nn.Linear(d_time + 64, d_model)

        self.layers = nn.ModuleList(
            [
                nn.TransformerEncoderLayer(
                    d_model=d_model,
                    nhead=n_heads,
                    dim_feedforward=d_ff,
                    dropout=dropout,
                    batch_first=True,
                )
                for _ in range(n_layers)
            ]
        )

        self.risk_head = nn.Sequential(
            nn.Linear(d_model, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 1),
        )
        self.sofa_head = nn.Sequential(
            nn.Linear(d_model, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.ReLU(),
        )

        # Boolean mask (True = disallowed) rather than an additive
        # float -inf mask: nn.MultiheadAttention treats mismatched
        # attn_mask/key_padding_mask dtypes as deprecated, so both
        # masks here are boolean for consistency.
        causal_mask = torch.triu(torch.ones(window_size, window_size, dtype=torch.bool), diagonal=1)
        self.register_buffer("causal_mask", causal_mask)

    def forward(self, vitals: torch.Tensor, timestamps: torch.Tensor, mask: torch.Tensor, return_attention: bool = True):
        """
        vitals:     (batch, window_size, n_vitals)
        timestamps: (batch, window_size)
        mask:       (batch, window_size) bool, True = real, False = padded
        return_attention: extracting per-timestep attention needs an
            extra, non-fused self-attention call (`need_weights=True`
            disables PyTorch's fused attention kernel). Training never
            uses this output (the loss only touches risk_logit and
            sofa_score), so train.py passes False to use the fast fused
            path on every layer; inference.py needs the explanation and
            passes True (the default, matching the model's output
            contract of always returning three values).

        Returns: risk_logit (batch,), sofa_score (batch,), attention_weights (batch, window_size) or None
        """
        time_emb = self.time2vec(timestamps)  # (batch, L, d_time)
        feat_emb = self.feature_proj(vitals)  # (batch, L, 64)
        x = torch.cat([time_emb, feat_emb], dim=-1)  # (batch, L, d_time + 64)
        x = self.input_proj(x)  # (batch, L, d_model)

        key_padding_mask = ~mask  # True = ignore, per nn.MultiheadAttention convention

        # Left-padded sequences combined with causal masking mean a
        # padded QUERY position can have every key masked (causal limits
        # it to <= its own index, which for a padded position is itself
        # all padding) -> softmax over all -inf -> NaN. A zero attention
        # weight times a NaN value is still NaN (0 * NaN = NaN in IEEE
        # float), so without cleanup this would silently poison later
        # layers' outputs for REAL positions too. nan_to_num after every
        # layer keeps padded positions at a clean zero and stops that
        # propagation; real positions always have at least one valid
        # causally-visible, non-padded key (themselves), so they never
        # produce NaN in the first place.
        importance = None

        if return_attention:
            for layer in self.layers[:-1]:
                x = layer(x, src_mask=self.causal_mask, src_key_padding_mask=key_padding_mask)
                x = torch.nan_to_num(x, nan=0.0)

            last_layer = self.layers[-1]
            _, attn_weights = last_layer.self_attn(
                x, x, x,
                attn_mask=self.causal_mask,
                key_padding_mask=key_padding_mask,
                need_weights=True,
                average_attn_weights=True,
            )  # attn_weights: (batch, L, L) averaged across heads
            attn_weights = torch.nan_to_num(attn_weights, nan=0.0).detach()

            x = last_layer(x, src_mask=self.causal_mask, src_key_padding_mask=key_padding_mask)
            x = torch.nan_to_num(x, nan=0.0)

            # Per-timestep importance: which hours the model attended to
            # when producing THIS prediction. Deliberately the LAST
            # (current, always-real since padding is left-aligned)
            # query position's attention row, not a mean over all query
            # positions: causal masking means key 0 is visible to all L
            # queries while key L-1 is visible to only 1, so averaging
            # over the query dimension structurally inflates early
            # hours' apparent importance regardless of what the model
            # actually learned (verified: this produced attention peaks
            # on hour 1 for every input, an artifact, not a signal).
            importance = attn_weights[:, -1, :]  # (batch, L)
        else:
            for layer in self.layers:
                x = layer(x, src_mask=self.causal_mask, src_key_padding_mask=key_padding_mask)
                x = torch.nan_to_num(x, nan=0.0)

        mask_f = mask.unsqueeze(-1).float()
        pooled = (x * mask_f).sum(dim=1) / mask_f.sum(dim=1).clamp(min=1e-8)  # (batch, d_model)

        risk_logit = self.risk_head(pooled).squeeze(-1)  # (batch,)
        sofa_score = self.sofa_head(pooled).squeeze(-1).clamp(max=24.0)  # (batch,)

        return risk_logit, sofa_score, importance
